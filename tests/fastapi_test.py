import asyncio
import random
import uuid

import pytest

import httpx

import uvloop
from hypercorn.asyncio import serve
from hypercorn.config import Config

import openapi3

from api.main import app


@pytest.fixture(scope="session")
def config(unused_tcp_port_factory):
    c = Config()
    c.bind = [f"localhost:{unused_tcp_port_factory()}"]
    return c


@pytest.fixture(scope="session")
def event_loop(request):
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def server(event_loop, config):
    uvloop.install()
    try:
        sd = asyncio.Event()
        task = event_loop.create_task(serve(app, config, shutdown_trigger=sd.wait))
        yield config
    finally:
        sd.set()
        await task


@pytest.fixture(scope="session")
async def client(event_loop, server):
    async with httpx.AsyncClient() as client:
        data = await client.get(f"http://{server.bind[0]}/openapi.json")
    data = data.json()
    data["servers"][0]["url"] = f"http://{server.bind[0]}"
    api = openapi3.OpenAPI(data)
    return api


def randomPet(name=None):
    return {"data":{"pet":{"name":str(name) if name else random.choice(["dog","cat","mouse","eagle"])}}}


@pytest.mark.asyncio
async def test_createPet(event_loop, server, client):
    async with client:
        r = await client.call_createPet(**randomPet())
        assert type(r) == client.components.schemas["Pet"].get_type()

        r = await client.call_createPet(data={"pet":{"name":r.name}})
        assert type(r) == client.components.schemas["Error"].get_type()


@pytest.mark.asyncio
async def test_listPet(event_loop, server, client):
    async with client:
        r = await client.call_createPet(**randomPet(uuid.uuid4()))
        l = await client.call_listPet()
    assert len(l) > 0


@pytest.mark.asyncio
async def test_getPet(event_loop, server, client):
    async with client:
        pet = await client.call_createPet(**randomPet(uuid.uuid4()))
        r = await client.call_getPet(parameters={"pet_id":pet.id})
        assert type(r) == type(pet)
        assert r.id == pet.id

        r = await client.call_getPet(parameters={"pet_id":-1})
        assert type(r) == client.components.schemas["Error"].get_type()


@pytest.mark.asyncio
async def test_deletePet(event_loop, server, client):
    async with client:
        r = await client.call_deletePet(parameters={"pet_id":-1})
        assert type(r) == client.components.schemas["Error"].get_type()

        await client.call_createPet(**randomPet(uuid.uuid4()))
        zoo = await client.call_listPet()
        for pet in zoo:
            await client.call_deletePet(parameters={"pet_id":pet.id})


@pytest.mark.asyncio
async def test_getPetUnexpectedResponse(event_loop, server, client):
    """
    Tests that undeclared response codes raise the correct UnexpectedResponseError
    with the relevant inforamtion included.
    """
    with pytest.raises(
            openapi3.UnexpectedResponseError,
            match=r"Unexpected response 204 from getPet \(expected one of 200, 404, 422, no default is defined\)",
        ) as exc_info:
        r = await asyncio.to_thread(client.call_getPet, parameters={"pet_id": -2})

    assert exc_info.value.status_code == 204
