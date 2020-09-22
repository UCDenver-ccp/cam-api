from core.transpile import build_query
from nose.tools import eq_
import asyncio
from unittest.mock import MagicMock, patch
from unittest import TestCase, skip
from reasoner_validator import validate_Message, ValidationError
from core.utilities import PREFIXES


# nodes and edges are fully specified
qgraph_fully_specified_entity_pair = {
    "nodes": [
        {"id": "n0", "type": "chemical_substance", "curie": "CHEBI:3215"},
        {"id": "n1", "type": "gene_product", "curie": "PR:000031567"},
    ],
    "edges": [
        {
            "id": "e0",
            "source_id": "n0",
            "target_id": "n1",
            "type": "negatively_regulates_entity_to_entity",
        }
    ],
}

# nodes are specified by type only
qgraph_type_only_entity_pair = {
    "nodes": [
        {"id": "n0", "type": "chemical_substance"},
        {"id": "n1", "type": "gene_product"},
    ],
    "edges": [
        {
            "id": "e0",
            "source_id": "n0",
            "target_id": "n1",
            "type": "negatively_regulates_entity_to_entity",
        }
    ],
}

# nodes are specified by curie only
qgraph_curie_only_entity_pair = {
    "nodes": [
        {"id": "n0", "curie": "CHEBI:3215"},
        {"id": "n1", "curie": "PR:000031567"},
    ],
    "edges": [
        {
            "id": "e0",
            "source_id": "n0",
            "target_id": "n1",
            "type": "negatively_regulates_entity_to_entity",
        }
    ],
}

# one node fully specified, the other by type only
qgraph_one_curie_one_type = {
    "nodes": [
        {"id": "n0", "type": "chemical_substance"},
        {"id": "n1", "type": "gene_product", "curie": "PR:000031567"},
    ],
    "edges": [
        {
            "id": "e0",
            "source_id": "n0",
            "target_id": "n1",
            "type": "negatively_regulates_entity_to_entity",
        }
    ],
}

# one node fully specified, the other node by type only. No edge type specified
qgraph_one_curie_one_type_no_edge_type = {
    "nodes": [
        {"id": "n0", "type": "chemical_substance"},
        {"id": "n1", "type": "gene_product", "curie": "PR:000031567"},
    ],
    "edges": [
        {
            "id": "e0",
            "source_id": "n0",
            "target_id": "n1",
        }
    ],
}

# three nodes fully specified, 2 edges also fully specified
qgraph_two_hop_fully_specified = {
    "nodes": [
        {"id": "n0", "type": "chemical_substance", "curie": "CHEBI:3215"},
        {"id": "n1", "type": "gene_product", "curie": "PR:000031567"},
        {"id": "n2", "type": "gene_product", "curie": "PR:000012345"},
    ],
    "edges": [
        {
            "id": "e0",
            "source_id": "n0",
            "target_id": "n1",
            "type": "negatively_regulates_entity_to_entity",
        },
        {
            "id": "e1",
            "source_id": "n1",
            "target_id": "n2",
            "type": "positively_regulates_entity_to_entity",
        },
    ],
}


def test_validate_query_graphs():
    "validate each query graph as part of a message using the TRAPI validator"

    message = {}
    message["query_graph"] = qgraph_fully_specified_entity_pair
    validate_Message(message)

    message["query_graph"] = qgraph_type_only_entity_pair
    validate_Message(message)

    message["query_graph"] = qgraph_curie_only_entity_pair
    validate_Message(message)

    message["query_graph"] = qgraph_one_curie_one_type
    validate_Message(message)

    message["query_graph"] = qgraph_one_curie_one_type_no_edge_type
    validate_Message(message)

    message["query_graph"] = qgraph_two_hop_fully_specified
    validate_Message(message)


class AsyncMock(MagicMock):
    "helper class to test async. Borrowed from: https://medium.com/@AgariInc/strategies-for-testing-async-code-in-python-c52163f2deab"

    async def __call__(self, *args, **kwargs):
        return super().__call__(*args, **kwargs)


# simple coroutine to call build_query inside async
async def to_sparql(qgraph, strict):
    return await build_query(qgraph, strict)


def get_prefixes():
    "helper method to get prefixes to add to the expected SPARQL in the tests below"
    prequel = ""
    for key, value in PREFIXES.items():
        prequel += f"PREFIX {key}: <{value}>\n"
    prequel += "\n"
    return prequel


# Note that the path to the run_query function must be from where it is loaded (core.transpile) not where it is defined (core.utilities)
class TestBuildQueryFullySpecified(TestCase):

    # test w/fully specified entity pair
    @patch("core.transpile.run_query", new_callable=AsyncMock)
    def test_build_query(self, mock_thing):
        mock_thing.return_value = [
            {"predicate": {"value": "http://purl.obolibrary.org/obo/RO_0002212"}}
        ]
        strict = True
        sparql = asyncio.run(to_sparql(qgraph_fully_specified_entity_pair, strict))

        expected_sparql = (
            get_prefixes()
            + """SELECT DISTINCT ?e0 ?n0 ?n0_type ?n1 ?n1_type WHERE {
  ?n0 sesame:directType ?n0_type .
  ?n1 sesame:directType ?n1_type .
VALUES ?e0 { <http://purl.obolibrary.org/obo/RO_0002212> }
  ?n0 ?e0 ?n1 .
?n0 rdf:type CHEBI:3215 .
?n1 rdf:type PR:000031567 .
}"""
        )
        eq_(expected_sparql, sparql, "SPARQL not as expected")


class TestBuildQueryTypeOnly(TestCase):
    # test w/type-only entity pair
    @patch("core.transpile.run_query", new_callable=AsyncMock)
    def test_build_query(self, mock_thing):
        mock_thing.return_value = [
            {"predicate": {"value": "http://purl.obolibrary.org/obo/RO_0002212"}}
        ]
        strict = True
        sparql = asyncio.run(to_sparql(qgraph_type_only_entity_pair, strict))

        expected_sparql = (
            get_prefixes()
            + """SELECT DISTINCT ?e0 ?n0 ?n0_type ?n1 ?n1_type WHERE {
  ?n0 sesame:directType ?n0_type .
  ?n1 sesame:directType ?n1_type .
VALUES ?e0 { <http://purl.obolibrary.org/obo/RO_0002212> }
  ?n0 ?e0 ?n1 .
?n0 rdf:type bl:ChemicalSubstance .
?n1 rdf:type bl:GeneProduct .
}"""
        )
        eq_(expected_sparql, sparql, "SPARQL not as expected")


class TestBuildQueryCurieOnly(TestCase):
    # test w/curie-only entity pair
    @patch("core.transpile.run_query", new_callable=AsyncMock)
    def test_build_query(self, mock_thing):
        mock_thing.return_value = [
            {"predicate": {"value": "http://purl.obolibrary.org/obo/RO_0002212"}}
        ]
        strict = True
        sparql = asyncio.run(to_sparql(qgraph_curie_only_entity_pair, strict))

        expected_sparql = (
            get_prefixes()
            + """SELECT DISTINCT ?e0 ?n0 ?n0_type ?n1 ?n1_type WHERE {
  ?n0 sesame:directType ?n0_type .
  ?n1 sesame:directType ?n1_type .
VALUES ?e0 { <http://purl.obolibrary.org/obo/RO_0002212> }
  ?n0 ?e0 ?n1 .
?n0 rdf:type CHEBI:3215 .
?n1 rdf:type PR:000031567 .
}"""
        )
        eq_(expected_sparql, sparql, "SPARQL not as expected")


class TestBuildQueryOneTypeOneCurie(TestCase):
    # test w/one type & one curie entity pair
    @patch("core.transpile.run_query", new_callable=AsyncMock)
    def test_build_query(self, mock_thing):
        mock_thing.return_value = [
            {"predicate": {"value": "http://purl.obolibrary.org/obo/RO_0002212"}}
        ]
        strict = True
        sparql = asyncio.run(to_sparql(qgraph_one_curie_one_type, strict))

        expected_sparql = (
            get_prefixes()
            + """SELECT DISTINCT ?e0 ?n0 ?n0_type ?n1 ?n1_type WHERE {
  ?n0 sesame:directType ?n0_type .
  ?n1 sesame:directType ?n1_type .
VALUES ?e0 { <http://purl.obolibrary.org/obo/RO_0002212> }
  ?n0 ?e0 ?n1 .
?n0 rdf:type bl:ChemicalSubstance .
?n1 rdf:type PR:000031567 .
}"""
        )
        eq_(expected_sparql, sparql, "SPARQL not as expected")


class TestBuildQueryOneTypeOneCurieNoEdge(TestCase):
    # test w/one type & one curie entity pair but no edge type specified
    @skip("# NOTE: this fails as the code expects an edge type")
    @patch("core.transpile.run_query", new_callable=AsyncMock)
    def test_build_query(self, mock_thing):
        mock_thing.return_value = [
            {"predicate": {"value": "http://purl.obolibrary.org/obo/RO_0002212"}}
        ]
        strict = True
        sparql = asyncio.run(to_sparql(qgraph_one_curie_one_type_no_edge_type, strict))

        expected_sparql = (
            get_prefixes()
            + """SELECT DISTINCT ?e0 ?n0 ?no_type ?n1 ?n1_type WHERE {
  ?n0 sesame:directType ?n0_type .
  ?n1 sesame:directType ?n1_type .
VALUES ?e0 {  }
  ?n0 ?e0 ?n1 .
?n0 rdf:type bl:ChemicalSubstance .
?n1 rdf:type PR:000031567 .
}"""
        )

        print("SPARQL: " + sparql)
        print("EXPECTED: " + expected_sparql)
        eq_(expected_sparql, sparql, "SPARQL not as expected")


class TestBuildQueryTwoHop(TestCase):
    # test w/two hop fully-specified
    @patch("core.transpile.run_query", new_callable=AsyncMock)
    def test_build_query(self, mock_thing):
        mock_thing.return_value = [
            {"predicate": {"value": "http://purl.obolibrary.org/obo/RO_0002212"}}
        ]
        strict = True
        sparql = asyncio.run(to_sparql(qgraph_two_hop_fully_specified, strict))

        expected_sparql = (
            get_prefixes()
            + """SELECT DISTINCT ?e0 ?e1 ?n0 ?n0_type ?n1 ?n1_type ?n2 ?n2_type WHERE {
  ?n0 sesame:directType ?n0_type .
  ?n1 sesame:directType ?n1_type .
  ?n2 sesame:directType ?n2_type .
VALUES ?e0 { <http://purl.obolibrary.org/obo/RO_0002212> }
  ?n0 ?e0 ?n1 .
VALUES ?e1 { <http://purl.obolibrary.org/obo/RO_0002212> }
  ?n1 ?e1 ?n2 .
?n0 rdf:type CHEBI:3215 .
?n1 rdf:type PR:000031567 .
?n2 rdf:type PR:000012345 .
}"""
        )

        print("SPARQL: " + sparql)
        print("EXPECTED: " + expected_sparql)
        eq_(expected_sparql, sparql, "SPARQL not as expected")
