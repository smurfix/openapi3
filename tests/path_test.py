"""
This file tests that paths are parsed and populated correctly
"""
import pytest

from openapi3 import OpenAPI
from openapi3.schemas import Schema


def test_paths_exist(petstore_expanded_spec):
    """
    Tests that paths are parsed correctly
    """
    assert '/pets' in petstore_expanded_spec.paths
    assert '/pets/{id}' in petstore_expanded_spec.paths
    assert len(petstore_expanded_spec.paths) == 2

def test_operations_exist(petstore_expanded_spec):
    """
    Tests that methods are populated as expected in paths
    """
    pets_path = petstore_expanded_spec.paths['/pets']
    assert pets_path.get is not None
    assert pets_path.post is not None
    assert pets_path.put is None
    assert pets_path.delete is None

    pets_id_path = petstore_expanded_spec.paths['/pets/{id}']
    assert pets_id_path.get is not None
    assert pets_id_path.post is None
    assert pets_id_path.put is None
    assert pets_id_path.delete is not None


def test_operation_populated(petstore_expanded_spec):
    """
    Tests that operations are populated as expected
    """
    op = petstore_expanded_spec.paths['/pets'].get

    # check description and metadata populated correctly
    assert op.operationId == "findPets"
    assert op.description.startswith("Returns all pets from the system")
    assert op.summary is None

    # check parameters populated correctly
    assert len(op.parameters) == 2

    param1 = op.parameters[0]
    assert param1.name == "tags"
    assert param1.in_ == "query"
    assert param1.description == "tags to filter by"
    assert param1.required == False
    assert param1.style == "form"
    assert param1.schema is not None
    assert param1.schema.type == "array"
    assert param1.schema.items.type == "string"

    param2 = op.parameters[1]
    assert param2.name == "limit"
    assert param2.in_ == "query"
    assert param2.description == "maximum number of results to return"
    assert param2.required == False
    assert param2.schema is not None
    assert param2.schema.type == "integer"
    assert param2.schema.format == "int32"

    # check that responses populated correctly
    assert '200' in op.responses
    assert 'default' in op.responses
    assert len(op.responses) == 2

    resp1 = op.responses['200']
    assert resp1.description == "pet response"
    assert len(resp1.content) == 1
    assert 'application/json' in resp1.content
    con1 = resp1.content['application/json']
    assert con1.schema is not None
    assert con1.schema.type == "array"
    # we're not going to test that the ref resolved correctly here - that's a separate test
    assert type(con1.schema.items) == Schema

    resp2 = op.responses['default']
    assert resp2.description == "unexpected error"
    assert len(resp2.content) == 1
    assert 'application/json' in resp2.content
    con2 = resp2.content['application/json']
    assert con2.schema is not None
    # again, test ref resolution elsewhere
    assert type(con2.schema) == Schema
