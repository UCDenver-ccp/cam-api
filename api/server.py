"""REST portal for CAM-KP RDF database."""
import json
import logging

from fastapi import FastAPI, Body
import httpx
from starlette.responses import Response

from api.models import Query, Message
from core.transpile import build_query, parse_response, get_details, parse_kgraph, get_CAM_query, get_CAM_stuff_query

LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.DEBUG)
BLAZEGRAPH_URL = 'https://stars-blazegraph.renci.org/cam/sparql'
# BLAZEGRAPH_URL = 'https://stars-app.renci.org/smallcam/sparql'

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
        limit: int = -1,
) -> Message:
    """Answer biomedical question."""
    message = query.message.dict()
    sparql_query = build_query(message['query_graph'], strict=strict, limit=limit)
    # LOGGER.debug(sparql_query)
    headers = {
        'content-type': 'application/sparql-query',
        'Accept': 'application/json'
    }
    # get results
    async with httpx.AsyncClient(timeout=None) as client:
        response = await client.post(
            BLAZEGRAPH_URL,
            headers=headers,
            data=sparql_query,
        )
    assert response.status_code < 300

    # parse results
    bindings = response.json()['results']['bindings']
    message['knowledge_graph'], message['results'] = parse_response(
        response=bindings,
        qgraph=message['query_graph']
    )

    if strict:
        # add extra CAM stuff
        qedge = message['query_graph']['edges'][0]
        result = bindings[0]
        src = result[qedge['source_id']]['value']
        pred = result[qedge['type'] or qedge['id']]['value']
        obj = result[qedge['target_id']]['value']
        query = get_CAM_query(src, pred, obj)
        async with httpx.AsyncClient(timeout=None) as client:
            response = await client.post(
                BLAZEGRAPH_URL,
                headers=headers,
                data=query,
            )
        assert response.status_code < 300
        bindings = response.json()['results']['bindings']
        assert len(bindings) == 1
        graph = (bindings[0].get('other', None) or bindings[0]['g'])['value']
        query = get_CAM_stuff_query(graph)
        async with httpx.AsyncClient(timeout=None) as client:
            response = await client.post(
                BLAZEGRAPH_URL,
                headers=headers,
                data=query,
            )
        assert response.status_code < 300
        bindings = response.json()['results']['bindings']

        for idx, triple in enumerate(bindings):
            
            source_id = triple['s_type']['value']
            message['knowledge_graph']['nodes'][source_id] = {
                'id': source_id
            }
            target_id = triple['o_type']['value']
            message['knowledge_graph']['nodes'][target_id] = {
                'id': target_id
            }
            edge_id = f'ee{idx:04d}'
            edge_type = triple['p_type']['value']
            message['knowledge_graph']['edges'][edge_id] = {
                'id': edge_id,
                'type': edge_type,
                'source_id': source_id,
                'target_id': target_id,
            }
    LOGGER.debug(message['knowledge_graph'])

    # get knowledge graph
    detail_query, node_map, edge_map = get_details(message['knowledge_graph'])
    # LOGGER.debug(detail_query)
    async with httpx.AsyncClient(timeout=None) as client:
        response = await client.post(
            BLAZEGRAPH_URL,
            headers=headers,
            data=detail_query,
        )
    assert response.status_code < 300

    # parse knowledge graph
    message['knowledge_graph'] = parse_kgraph(
        response=response.json()['results']['bindings'],
        node_map=node_map,
        edge_map=edge_map,
        kgraph=message['knowledge_graph']
    )

    return message
