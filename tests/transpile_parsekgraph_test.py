from core.transpile import parse_kgraph
from nose.tools import eq_
import asyncio
from unittest.mock import MagicMock, patch
from unittest import TestCase, skip
from reasoner_validator import validate_Message, ValidationError


kgraph = {
    "nodes": {
        "CHEBI:3215": {"id": "CHEBI:3215"},
        "PR:0000317567": {"id": "PR:0000317567"},
    },
    "edges": {
        "7d682dcbe995d90c08b24f382cea523dc4f9e82208a42d98180b911a34102914": {
            "id": "7d682dcbe995d90c08b24f382cea523dc4f9e82208a42d98180b911a34102914",
            "type": "RO:0002212",
            "source_id": "CHEBI:3215",
            "target_id": "PR:0000317567",
        }
    },
}


detail_query_response = [
    {
        "kid": {"value": "http://purl.obolibrary.org/obo/CHEBI_3215"},
        "blclass": {"value": "https://w3id.org/biolink/vocab/ChemicalSubstance"},
        "label": {"value": "bupivacaine"},
    },
    {
        "kid": {"value": "http://purl.obolibrary.org/obo/PR_0000317567"},
        "blclass": {"value": "https://w3id.org/biolink/vocab/GeneProduct"},
        "label": {"value": "leucine-rich repeat-containing protein 3B"},
    },
    {
        "kid": {"value": "http://purl.obolibrary.org/obo/PR_0000317567"},
        "blclass": {"value": "https://w3id.org/biolink/vocab/GeneOrGeneProduct"},
        "label": {"value": "leucine-rich repeat-containing protein 3B"},
    },
]
slot_query_response = [
    {
        "qid": {"value": "e0000"},
        "kid": {"value": "http://purl.obolibrary.org/obo/RO_0002212"},
        "blslot": {
            "value": "https://w3id.org/biolink/vocab/negatively_regulates_entity_to_entity"
        },
        "label": {"value": "negatively regulates entity-to-entity"},
    }
]

node_map = {"n0000": "CHEBI:3215", "n0001": "PR:0000317567"}
edge_map = {
    "e0000": ["7d682dcbe995d90c08b24f382cea523dc4f9e82208a42d98180b911a34102914"]
}


expected_kgraph = {
    "nodes": [
        {"id": "CHEBI:3215", "type": ["chemical_substance"], "name": "bupivacaine"},
        {
            "id": "PR:0000317567",
            "type": ["gene_or_gene_product", "gene_product"],
            "name": "leucine-rich repeat-containing protein 3B",
        },
    ],
    "edges": [
        {
            "id": "7d682dcbe995d90c08b24f382cea523dc4f9e82208a42d98180b911a34102914",
            "type": "negatively_regulates_entity_to_entity",
            "source_id": "CHEBI:3215",
            "target_id": "PR:0000317567",
        }
    ],
}


def test_parse_kgraph():
    updated_kgraph = parse_kgraph(
        response=detail_query_response,
        slot_response=slot_query_response,
        node_map=node_map,
        edge_map=edge_map,
        kgraph=kgraph,
    )

    print("UPDATED KGRAPH: " + str(updated_kgraph))
    print("EXPECTED KGRAPH: " + str(expected_kgraph))
    eq_(expected_kgraph, updated_kgraph, "Updated knowledge graph not as expected")


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


results = [
    {
        "node_bindings": [
            {"qg_id": "n0", "kg_id": "CHEBI:3215"},
            {"qg_id": "n1", "kg_id": "PR:0000317567"},
        ],
        "edge_bindings": [
            {
                "qg_id": "e0",
                "kg_id": "7d682dcbe995d90c08b24f382cea523dc4f9e82208a42d98180b911a34102914",
                "publication_0": "PMID:29085514",
                "score_0": 0.99956816,
                "sentence_0": "The administration of 50 ?g/ml bupivacaine promoted maximum breast cancer cell invasion, and suppressed LRRC3B mRNA expression in cells.",
                "subject_spans_0": "start: 31, end: 42",
                "object_spans_0": "start: 104, end: 110",
                "provided_by_0": "TMProvider",
            }
        ],
    }
]


# validate the message produced
def test_validate_message():
    message = {}
    message["query_graph"] = qgraph_fully_specified_entity_pair
    message["results"] = results
    message["knowledge_graph"] = expected_kgraph
    validate_Message(message)
