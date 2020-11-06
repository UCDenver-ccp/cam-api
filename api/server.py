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
    title="Text Mining Provider -- Targeted text-mined association API",
    description="""This REST portal serves Biolink associations that have been mined from the scientific literature. <br> 
                   Current content include the following associations: 
                   <ul>
                    <li> <a href="https://biolink.github.io/biolink-model/docs/ChemicalToGeneAssociation.html">biolink:ChemicalToGeneAssociation</a>
                        <ul>
                            <li> Chemicals are represented using the <a href="https://www.ebi.ac.uk/chebi/">CHEBI ontology</a>.
                            <li> Genes are represented as gene products using the <a href="https://proconsortium.org/">Protein Ontology</a>. 
                            <ul>
                                <li>Note that the species non-specific classes from the Protein Ontology have been preferred in the annotation process, <br>so you may need to make use of the subsumption hierarchy in the Protein Ontology to link to species-specific entities.
                            </ul>
                            <li> Relations between chemicals and genes include:
                        <ul>
                            <li> <a href="https://biolink.github.io/biolink-model/docs/positively_regulates_entity_to_entity.html">biolink:positively_regulates_entity_to_entity</a>
                            <li> <a href="https://biolink.github.io/biolink-model/docs/negatively_regulates_entity_to_entity.html">biolink:negatively_regulates_entity_to_entity</a>
                        </ul>
                        <li> Example:
                        <pre>{
  &nbsp;&nbsp;"message": {
    &nbsp;&nbsp;&nbsp;&nbsp;"query_graph": {
      &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;"nodes": [
        &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;{
          &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;"id": "n0",
          &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;"type": "chemical_substance",
          &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;"curie": "CHEBI:3215"
        &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;},
        &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;{
          &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;"id": "n1",
          &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;"type": "gene_product",
          &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;"curie": "PR:000031567"
        &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;}
      &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;],
      &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;"edges": [
        &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;{
          &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;"id": "e0",
          &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;"source_id": "n0",
          &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;"target_id": "n1",
          &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;"type": "negatively_regulates_entity_to_entity"
        &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;}
      &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;]
    &nbsp;&nbsp;&nbsp;&nbsp;}
  &nbsp;&nbsp;}
}
                        </pre>
                    </ul>
                   """,
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
