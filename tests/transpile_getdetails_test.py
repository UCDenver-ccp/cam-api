from core.transpile import get_details
from nose.tools import eq_
import asyncio
from unittest.mock import MagicMock, patch
from unittest import TestCase, skip
from reasoner_validator import validate_Message, ValidationError
from core.utilities import PREFIXES


def get_prefixes():
    "helper method to get prefixes to add to the expected SPARQL in the tests below"
    prequel = ""
    for key, value in PREFIXES.items():
        prequel += f"PREFIX {key}: <{value}>\n"
    prequel += "\n"
    return prequel


kgraph = {
    "nodes": {
        "CHEBI:3215": {"id": "CHEBI:3215"},
        "PR:000031567": {"id": "PR:000031567"},
    },
    "edges": {
        "7d682dcbe995d90c08b24f382cea523dc4f9e82208a42d98180b911a34102914": {
            "id": "7d682dcbe995d90c08b24f382cea523dc4f9e82208a42d98180b911a34102914",
            "type": "RO:0002212",
            "source_id": "CHEBI:3215",
            "target_id": "PR:000031567",
        }
    },
}


def test_get_details():
    detail_query, slot_query, node_map, edge_map = get_details(kgraph)

    expected_detail_query = (
        get_prefixes()
        + """SELECT DISTINCT ?kid ?blclass ?label WHERE {
VALUES ?kid { <http://purl.obolibrary.org/obo/CHEBI_3215> <http://purl.obolibrary.org/obo/PR_000031567> }
?kid rdfs:subClassOf ?blclass .
OPTIONAL { ?kid rdfs:label ?label . }}"""
    )

    # SELECT DISTINCT ?kid ?blclass ?label WHERE {
    # VALUES ?kid { <http://purl.obolibrary.org/obo/CHEBI_3215> <http://purl.obolibrary.org/obo/PR_000031567> }
    # ?kid rdfs:subClassOf ?blclass .
    # ?blclass blml:is_a* bl:NamedThing .
    # OPTIONAL { ?kid rdfs:label ?label . }}
    expected_slot_query = (
        get_prefixes()
        + """SELECT DISTINCT ?qid ?kid ?blslot ?label WHERE {
VALUES (?kid ?qid) { ( <http://purl.obolibrary.org/obo/RO_0002212> "e0000" ) }
?blslot <http://translator/text_mining_provider/slot_mapping> ?kid .
OPTIONAL { ?kid rdfs:label ?label . }
}"""
    )

    # SELECT DISTINCT ?qid ?kid ?blslot ?label WHERE {
    # VALUES (?kid ?qid) { ( <http://purl.obolibrary.org/obo/RO_0002212> "e0000" ) }
    # ?blslot <http://reasoner.renci.org/vocab/slot_mapping> ?kid .
    # FILTER NOT EXISTS {
    #         ?other <http://reasoner.renci.org/vocab/slot_mapping> ?kid .
    #         ?other blml:is_a+/blml:mixins* ?blslot .
    #     }OPTIONAL { ?kid rdfs:label ?label . }
    # }

    expected_node_map = {"n0000": "CHEBI:3215", "n0001": "PR:000031567"}
    expected_edge_map = {
        "e0000": ["7d682dcbe995d90c08b24f382cea523dc4f9e82208a42d98180b911a34102914"]
    }

    print("DETAIL QUERY: " + str(detail_query) + "\n\n")
    print("EXPECTED DETAIL QUERY: " + str(expected_detail_query) + "\n\n")
    print("SLOT QUERY: " + str(slot_query) + "\n\n")
    print("EXPECTED SLOT QUERY: " + str(expected_slot_query) + "\n\n")

    print("NODE MAP: " + str(node_map) + "\n\n")

    print("EDGE MAP: " + str(edge_map) + "\n\n")

    eq_(expected_detail_query, detail_query, "Detail query not as expected")
    eq_(expected_slot_query, slot_query, "Slot query not as expected")
    eq_(expected_node_map, node_map, "Node map not as expected")
    eq_(expected_edge_map, edge_map, "Edge map not as expected")
