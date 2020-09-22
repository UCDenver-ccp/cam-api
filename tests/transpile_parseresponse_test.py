from core.transpile import parse_response
from nose.tools import eq_
import asyncio
from unittest.mock import MagicMock, patch
from unittest import TestCase, skip
from reasoner_validator import validate_Message, ValidationError


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

response = [
    {
        "e0": {"type": "uri", "value": "http://purl.obolibrary.org/obo/RO_0002212"},
        "n0": {"type": "uri", "value": "_:IjbFtUdgNQk-HHlsBju-I_jpSnA_subj"},
        "n0_type": {
            "type": "uri",
            "value": "http://purl.obolibrary.org/obo/CHEBI_3215",
        },
        "n1": {"type": "uri", "value": "_:IjbFtUdgNQk-HHlsBju-I_jpSnA_obj"},
        "n1_type": {
            "type": "uri",
            "value": "http://purl.obolibrary.org/obo/PR_0000317567",
        },
    }
]


class AsyncMock(MagicMock):
    "helper class to test async. Borrowed from: https://medium.com/@AgariInc/strategies-for-testing-async-code-in-python-c52163f2deab"

    async def __call__(self, *args, **kwargs):
        return super().__call__(*args, **kwargs)


# simple coroutine to call parse_response inside async
async def to_resp(response, qgraph, strict):
    return await parse_response(response, qgraph, strict)


# Note that the path to the run_query function must be from where it is loaded (core.transpile) not where it is defined (core.utilities)
class TestParseResponseFromFullySpecified(TestCase):

    # test w/fully specified entity pair
    @patch("core.transpile.run_query", new_callable=AsyncMock)
    def test_build_query(self, mock_thing):
        mock_thing.return_value = [
            {
                "publications": {"value": "PMID:29085514"},
                "score": {"value": "0.99956816"},
                "sentence": {
                    "value": "The administration of 50 ?g/ml bupivacaine promoted maximum breast cancer cell invasion, and suppressed LRRC3B mRNA expression in cells."
                },
                "subject_spans": {"value": "start: 31, end: 42"},
                "object_spans": {"value": "start: 104, end: 110"},
                "provided_by": {"value": "TMProvider"},
            }
        ]
        strict = True
        kgraph, results = asyncio.run(
            to_resp(response, qgraph_fully_specified_entity_pair, strict)
        )

        expected_results = [
            {
                "node_bindings": [
                    {"qg_id": "n0", "kg_id": "CHEBI:3215"},
                    {"qg_id": "n1", "kg_id": "PR:0000317567"},
                ],
                "edge_bindings": [
                    {
                        "qg_id": "e0",
                        "kg_id": "7d682dcbe995d90c08b24f382cea523dc4f9e82208a42d98180b911a34102914",
                        "provenance": str(
                            [
                                {
                                    "publication": "PMID:29085514",
                                    "score": "0.99956816",
                                    "sentence": "The administration of 50 ?g/ml bupivacaine promoted maximum breast cancer cell invasion, and suppressed LRRC3B mRNA expression in cells.",
                                    "subject_spans": "start: 31, end: 42",
                                    "object_spans": "start: 104, end: 110",
                                    "provided_by": "TMProvider",
                                }
                            ]
                        ),
                    }
                ],
            }
        ]

        expected_kgraph = {
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
        print("RESULTS:" + str(results))
        print("EXPECTED RESULTS:" + str(expected_results))
        print("KGRAPH:" + str(kgraph))
        print("EXPECTED KGRAPH:" + str(expected_kgraph))

        eq_(expected_results, results, "Results not as expected")
        eq_(expected_kgraph, kgraph, "Results not as expected")