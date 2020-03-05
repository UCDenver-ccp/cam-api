"""REST portal for CAM-KP RDF database."""
import json
import logging

from fastapi import FastAPI, Body
import httpx
from starlette.responses import Response

from api.models import Query, Message
from core.transpile import build_query, parse_response, get_details, parse_kgraph

LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.DEBUG)

app = FastAPI(
    title='CAM-KP API',
    description='REST portal for CAM-KP RDF database',
    version='1.0.0',
)

with open('examples/has_participant.json') as f:
    example = json.load(f)


@app.post('/transpile', response_model=str, tags=['query'])
async def transpile_query(
        query: Query = Body(..., example=example),
        strict: bool = True,
) -> str:
    """Transpile Reasoner Standard query to SPARQL."""
    message = query.message.dict()
    qgraph = message['query_graph']
    sparql_query = build_query(qgraph, strict)
    # return raw text response
    return Response(sparql_query, status_code=200, media_type='text/plain')


@app.post('/query', response_model=Message, tags=['query'])
async def answer_query(
        query: Query = Body(..., example=example),
        strict: bool = True,
) -> Message:
    """Answer biomedical question."""
    message = query.message.dict()
    sparql_query = build_query(message['query_graph'], strict)
    LOGGER.debug(sparql_query)
    headers = {
        'content-type': 'application/sparql-query',
        'Accept': 'application/json'
    }
    async with httpx.AsyncClient(timeout=None) as client:
        response = await client.post(
            'https://stars-blazegraph.renci.org/cam/sparql',
            headers=headers,
            data=sparql_query,
        )
    assert response.status_code < 300
    message['knowledge_graph'], message['results'] = parse_response(
        response=response.json()['results']['bindings'],
        qgraph=message['query_graph']
    )

    detail_query, node_map, edge_map = get_details(message['knowledge_graph'])
    LOGGER.debug(detail_query)
    async with httpx.AsyncClient(timeout=None) as client:
        response = await client.post(
            'https://stars-blazegraph.renci.org/cam/sparql',
            headers=headers,
            data=detail_query,
        )
    assert response.status_code < 300
    message['knowledge_graph'] = parse_kgraph(
        response=response.json()['results']['bindings'],
        node_map=node_map,
        edge_map=edge_map,
        kgraph=message['knowledge_graph']
    )
    return message
