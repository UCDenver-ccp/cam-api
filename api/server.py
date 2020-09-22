"""REST portal for CAM-KP RDF database."""
from collections import defaultdict
import json
import logging
from typing import List

from fastapi import FastAPI, Body
import httpx
from starlette.responses import Response

from api.models import Query, Message, QueryGraph
from core.transpile import (
    build_query,
    parse_response,
    get_details,
    parse_kgraph,
    # get_CAM_query,
    # get_CAM_stuff_query,
)
from core.utilities import apply_prefix, hash_dict, trim_qgraph, run_query

LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.DEBUG)

app = FastAPI(
    title="Text Mining Provider API",
    description="REST portal for Text Mining Provider targeted Biolink association database",
    version="1.0.0",
)

with open("examples/chebi-pr-regulation.json") as f:
    example = json.load(f)


# @app.post("/transpile", response_model=str, tags=["query"])
# async def transpile_query(
#     query: Query = Body(..., example=example),
#     strict: bool = True,
# ) -> str:
#     """Transpile Reasoner Standard query to SPARQL."""
#     message = query.message.dict()
#     qgraph = message["query_graph"]
#     sparql_query = await build_query(qgraph, strict)
#     # return raw text response
#     return Response(sparql_query, status_code=200, media_type="text/plain")


# subexample = example["message"]["query_graph"]


# @app.post("/subquery", response_model=List[QueryGraph], tags=["query"])
# async def generate_subqueries(
#     qgraph: QueryGraph = Body(..., example=subexample),
# ) -> List[QueryGraph]:
#     """Generate sub-queries by removing one edge at a time."""
#     return list(trim_qgraph(qgraph.dict()))


@app.post("/query", response_model=Message, tags=["query"])
async def answer_query(
    query: Query = Body(..., example=example),
    strict: bool = True,
    limit: int = -1,
) -> Message:
    """Answer biomedical question."""
    message = query.message.dict()
    sparql_query = await build_query(message["query_graph"], strict=strict, limit=limit)
    headers = {"content-type": "application/sparql-query", "Accept": "application/json"}
    # get results
    results = await run_query(sparql_query)

    # parse results
    message["knowledge_graph"], message["results"] = await parse_response(
        response=results,
        qgraph=message["query_graph"],
        strict=strict,
    )
    if not results:
        message["knowledge_graph"] = {
            "nodes": [],
            "edges": [],
        }
        return message

    # get knowledge graph
    detail_query, slot_query, node_map, edge_map = get_details(
        message["knowledge_graph"]
    )
    response = await run_query(detail_query)
    slot_response = await run_query(slot_query)

    # parse knowledge graph
    message["knowledge_graph"] = parse_kgraph(
        response=response,
        slot_response=slot_response,
        node_map=node_map,
        edge_map=edge_map,
        kgraph=message["knowledge_graph"],
    )

    return message
