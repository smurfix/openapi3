import random
import uuid

import pytest
import anyio

import httpx

from hypercorn.config import Config

import openapi3

from api.main import app


@pytest.fixture #(scope="session")
def config(unused_tcp_port_factory):
    c = Config()
    c.bind = [f"localhost:{unused_tcp_port_factory()}"]
    return c


@pytest.fixture #(scope="session")
async def server(config, anyio_backend):
    if anyio_backend=="trio":
        from hypercorn.trio import serve
    else:
        from hypercorn.asyncio import serve
    async with anyio.create_task_group() as tg:
        tg.start_soon(serve, app, config)
        yield config
        tg.cancel_scope.cancel()


@pytest.fixture #(scope="session")
async def client(server):
    async with httpx.AsyncClient() as client:
        data = await client.get(f"http://{server.bind[0]}/openapi.json")
    data = data.json()
    data["servers"][0]["url"] = f"http://{server.bind[0]}"
    api = openapi3.OpenAPI(data)
    return api


def randomPet(name=None):
    return {"data":{"pet":{"name":str(name) if name else random.choice(["dog","cat","mouse","eagle"])}}}


@pytest.mark.anyio
async def test_createPet(server, client):
    async with client:
        r = await client.call_createPet(**randomPet())
        assert type(r) == client.components.schemas["Pet"].get_type()

        r = await client.call_createPet(data={"pet":{"name":r.name}})
        assert type(r) == client.components.schemas["Error"].get_type()


@pytest.mark.anyio
async def test_listPet(server, client):
    async with client:
        r = await client.call_createPet(**randomPet(uuid.uuid4()))
        l = await client.call_listPet()
    assert len(l) > 0


@pytest.mark.anyio
async def test_getPet(server, client):
    async with client:
        pet = await client.call_createPet(**randomPet(uuid.uuid4()))
        r = await client.call_getPet(parameters={"pet_id":pet.id})
        assert type(r) == type(pet)
        assert r.id == pet.id

        r = await client.call_getPet(parameters={"pet_id":-1})
        assert type(r) == client.components.schemas["Error"].get_type()


@pytest.mark.anyio
async def test_deletePet(server, client):
    async with client:
        r = await client.call_deletePet(parameters={"pet_id":-1})
        assert type(r) == client.components.schemas["Error"].get_type()

        await client.call_createPet(**randomPet(uuid.uuid4()))
        zoo = await client.call_listPet()
        for pet in zoo:
            await client.call_deletePet(parameters={"pet_id":pet.id})


@pytest.mark.anyio
async def test_getPetUnexpectedResponse(server, client):
    """
    Tests that undeclared response codes raise the correct UnexpectedResponseError
    with the relevant information included.
    """
    async with client:
        with pytest.raises(
                openapi3.UnexpectedResponseError,
                match=r"Unexpected response 204 from getPet \(expected one of 200, 404, 422, no default is defined\)",
            ) as exc_info:
            r = await client.call_getPet(parameters={"pet_id": -2})

    assert exc_info.value.status_code == 204
