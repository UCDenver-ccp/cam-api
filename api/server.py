"""REST portal for CAM-KP RDF database."""
import logging

from fastapi import FastAPI
import httpx
from starlette.responses import Response

from api.models import Query, Message
from core.transpile import build_query, parse_response

LOGGER = logging.getLogger(__name__)

app = FastAPI(
    title='CAM-KP API',
    description='REST portal for CAM-KP RDF database',
    version='1.0.0',
)


@app.post('/transpile', response_model=str, tags=['query'])
async def transpile_query(query: Query) -> str:
    """Transpile Reasoner Standard query to SPARQL."""
    message = query.message.dict()
    qgraph = message['query_graph']
    sparql_query = build_query(qgraph)
    # return raw text response
    return Response(sparql_query, status_code=200, media_type='text/plain')


@app.post('/query', response_model=Message, tags=['query'])
async def answer_query(query: Query) -> Message:
    """Answer biomedical question."""
    message = query.message.dict()
    sparql_query = build_query(message['query_graph'])
    LOGGER.info(sparql_query)
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
    return message
