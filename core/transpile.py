"""Build a SPARQL Query."""
from collections import defaultdict

import httpx

from core.utilities import (
    PREFIXES,
    snake_to_pascal,
    pascal_to_snake,
    apply_prefix,
    hash_dict,
    unprefix,
    run_query,
)


async def build_query(qgraph, strict=True, limit=-1):
    """Build a SPARQL Query string."""
    query = ""
    node_types = {}
    for node in qgraph["nodes"]:

        if node.get("curie", False):
            # enforce node curie
            node_types[node["id"]] = node["curie"]
        elif node["type"]:
            # enforce node type
            pascal_node_type = snake_to_pascal(node["type"])
            node_types[node["id"]] = f"bl:{pascal_node_type}"
        if strict:
            query += f"  ?{node['id']} sesame:directType ?{node['id']}_type .\n"

    instance_vars = set()
    instance_vars_to_types = {}
    for idx, edge in enumerate(qgraph["edges"]):
        var = edge["id"]
        if edge["type"]:
            # enforce edge type
            predicate_query = f"""
            PREFIX bl: <https://w3id.org/biolink/vocab/>
            SELECT DISTINCT ?predicate
            WHERE {{
                bl:{edge['type']} <http://translator/text_mining_provider/slot_mapping> ?predicate .
            }}
            """
            bindings = await run_query(predicate_query)
            predicates = " ".join(
                [f"<{binding['predicate']['value']}>" for binding in bindings]
            )

            # predicates = edge["type"]
            query += f"VALUES ?{var} {{ {predicates} }}\n"

        # enforce connectivity
        if strict:
            query += f"  ?{edge['source_id']} ?{var} ?{edge['target_id']} .\n"
            instance_vars.add(edge["source_id"])
            instance_vars_to_types[edge["source_id"]] = edge["source_id"]
            instance_vars.add(edge["target_id"])
            instance_vars_to_types[edge["target_id"]] = edge["target_id"]
        else:
            exclude_list = "<http://purl.obolibrary.org/obo/GO_0003674>, <http://purl.obolibrary.org/obo/GO_0008150>, <http://purl.obolibrary.org/obo/GO_0005575>"
            query += f"  ?{edge['source_id']}_{idx} sesame:directType ?{edge['source_id']}_type .\n"
            query += f"FILTER(?{edge['source_id']}_type NOT IN ({exclude_list}))\n"
            query += f"FILTER NOT EXISTS {{ ?{edge['source_id']}_type rdfs:isDefinedBy <http://purl.obolibrary.org/obo/bfo.owl> }}\n"
            query += f"  ?{edge['target_id']}_{idx} sesame:directType ?{edge['target_id']}_type .\n"
            query += f"FILTER(?{edge['target_id']}_type NOT IN ({exclude_list}))\n"
            query += f"FILTER NOT EXISTS {{ ?{edge['target_id']}_type rdfs:isDefinedBy <http://purl.obolibrary.org/obo/bfo.owl> }}\n"
            query += (
                f"  ?{edge['source_id']}_{idx} ?{var} ?{edge['target_id']}_{idx} .\n"
            )
            instance_vars.add(f"{edge['source_id']}_{idx}")
            instance_vars_to_types[f"{edge['source_id']}_{idx}"] = edge["source_id"]
            instance_vars.add(f"{edge['target_id']}_{idx}")
            instance_vars_to_types[f"{edge['target_id']}_{idx}"] = edge["target_id"]
    for var, var_to_type in instance_vars_to_types.items():
        var_type = node_types[var_to_type]
        query += f"?{var} rdf:type {var_type} .\n"

    query += "}"
    if limit >= 0:
        query += f" LIMIT {limit}"

    prequel = ""
    for key, value in PREFIXES.items():
        prequel += f"PREFIX {key}: <{value}>\n"
    ids = [f"?{var}" for var in instance_vars]
    ids += [f"?{node['id']}_type" for node in qgraph["nodes"]]
    ids += list({f"?{edge['id']}" for edge in qgraph["edges"]})
    ids.sort()  # sorting to ensure reproducible order in unit tests
    var_string = " ".join(ids)
    prequel += f"\nSELECT DISTINCT {var_string} WHERE {{\n"
    return prequel + query


def get_details(kgraph):
    """Get node and edge details."""
    node_map = {
        f"n{idx:04d}": node["id"] for idx, node in enumerate(kgraph["nodes"].values())
    }
    edge_map = defaultdict(list)
    for edge in kgraph["edges"].values():
        edge_map[edge["type"]].append(edge["id"])
    edge_map2 = {f"e{idx:04d}": key for idx, key in enumerate(edge_map)}
    query = ""
    for key, value in PREFIXES.items():
        query += f"PREFIX {key}: <{value}>\n"
    query += f"\nSELECT DISTINCT ?kid ?blclass ?label WHERE {{\n"
    values = " ".join([f"<{unprefix(kid)}>" for qid, kid in node_map.items()])
    query += f"VALUES ?kid {{ {values} }}\n"
    query += "?kid rdfs:subClassOf ?blclass .\n"
    # query += "?blclass blml:is_a* bl:NamedThing .\n"
    query += "OPTIONAL { ?kid rdfs:label ?label . }"
    query += "}"

    slot_query = ""
    for key, value in PREFIXES.items():
        slot_query += f"PREFIX {key}: <{value}>\n"
    slot_query += f"\nSELECT DISTINCT ?qid ?kid ?blslot ?label WHERE {{\n"
    values = " ".join(
        [f'( <{unprefix(kid)}> "{qid}" )' for qid, kid in edge_map2.items()]
    )
    slot_query += f"VALUES (?kid ?qid) {{ {values} }}\n"
    slot_query += (
        "?blslot <http://translator/text_mining_provider/slot_mapping> ?kid .\n"
    )
    # slot_query += """FILTER NOT EXISTS {
    #     ?other <http://translator/text_mining_provider/slot_mapping> ?kid .
    #     ?other blml:is_a+/blml:mixins* ?blslot .
    # }"""
    slot_query += "OPTIONAL { ?kid rdfs:label ?label . }\n"
    slot_query += "}"

    return (
        query,
        slot_query,
        node_map,
        {key: edge_map[value] for key, value in edge_map2.items()},
    )


async def parse_response(response, qgraph, strict=True):
    """Parse the query response."""
    results = []
    kgraph = {
        "nodes": dict(),
        "edges": dict(),
    }
    edge_idx = 0
    for row in response:
        result = {"node_bindings": [], "edge_bindings": []}
        # handle nodes
        node_ids = dict()
        for qnode in qgraph["nodes"]:
            node_id = apply_prefix(row[f"{qnode['id']}_type"]["value"])
            node_ids[qnode["id"]] = node_id
            kgraph["nodes"][node_id] = {
                "id": node_id,
            }
            result["node_bindings"].append(
                {
                    "qg_id": qnode["id"],
                    "kg_id": node_id,
                }
            )
        # handle edges
        for idx, qedge in enumerate(qgraph["edges"]):
            var = qedge["id"]
            edge_type = apply_prefix(row[f"{var}"]["value"])
            source_id = node_ids[qedge["source_id"]]
            target_id = node_ids[qedge["target_id"]]
            edge = {
                "type": edge_type,
                "source_id": source_id,
                "target_id": target_id,
            }
            edge_id = hash_dict(edge)
            kgraph["edges"][edge_id] = {
                "id": edge_id,
                **edge,
            }

            if strict:
                src = row[qedge["source_id"]]["value"]
                obj = row[qedge["target_id"]]["value"]
            else:
                src = row[f"{qedge['source_id']}_{idx}"]["value"]
                obj = row[f"{qedge['target_id']}_{idx}"]["value"]
            pred = row[qedge["id"]]["value"]
            query = get_evidence_query(src, pred, obj)
            bindings = await run_query(query)

            result["edge_bindings"].append(
                {
                    "qg_id": qedge["id"],
                    "kg_id": edge_id,
                }
            )

            # for each evidence add score, sentence, etc.
            for idx, binding in enumerate(bindings):
                result["edge_bindings"][0][f"publication_{idx}"] = binding[
                    "publications"
                ]["value"]
                result["edge_bindings"][0][f"score_{idx}"] = binding["score"]["value"]
                result["edge_bindings"][0][f"sentence_{idx}"] = binding["sentence"][
                    "value"
                ]
                result["edge_bindings"][0][f"subject_spans_{idx}"] = binding[
                    "subject_spans"
                ]["value"]
                result["edge_bindings"][0][f"object_spans_{idx}"] = binding[
                    "object_spans"
                ]["value"]
                result["edge_bindings"][0][f"provided_by_{idx}"] = binding[
                    "provided_by"
                ]["value"]

            edge_idx += 1
        results.append(result)

    return kgraph, results


def parse_kgraph(response, slot_response, node_map, edge_map, kgraph):
    """Parse the query response."""
    nodes = kgraph["nodes"]
    for qid, kid in node_map.items():
        nodes[kid]["type"] = set()
        for row in response:
            fullkid = unprefix(kid)
            if row["kid"]["value"] == fullkid:
                if "label" in row:
                    nodes[kid]["name"] = row["label"]["value"]
                node_type = pascal_to_snake(
                    apply_prefix(row["blclass"]["value"]).split(":", 1)[1]
                )
                nodes[kid]["type"].add(node_type)
        # reasoner validator seems to want a list instead of set for the node type
        # sorted to ensure reproducibility for unit tests
        nodes[kid]["type"] = list(nodes[kid]["type"])
        nodes[kid]["type"].sort()
    kgraph["nodes"] = list(nodes.values())

    edges = kgraph["edges"]
    for qid, kids in edge_map.items():
        for row in slot_response:
            if row["qid"]["value"] == qid:
                edge_type = apply_prefix(row["blslot"]["value"]).split(":", 1)[1]
                for kid in kids:
                    edges[kid]["type"] = edge_type
    kgraph["edges"] = list(edges.values())

    return kgraph


def get_evidence_query(src, pred, obj):
    """Generate query to get text-mined evidence that asserts the edge."""
    query = ""
    for key, value in PREFIXES.items():
        query += f"PREFIX {key}: <{value}>\n"
    return (
        query
        + "select ?assoc ?publications ?score ?sentence ?subject_spans ?object_spans ?provided_by {\n"
        f"  ?subj <http://www.openrdf.org/schema/sesame#directType> <{src}> .\n"
        "  ?assoc <https://w3id.org/biolink/vocab/subject> ?subj .\n"
        "  ?assoc <https://w3id.org/biolink/vocab/object> ?obj .\n"
        f"  ?obj <http://www.openrdf.org/schema/sesame#directType> <{obj}> .\n"
        f"  ?assoc <https://w3id.org/biolink/vocab/relation> <{pred}> .\n"
        "  ?assoc <https://w3id.org/biolink/vocab/evidence> ?evidence .\n"
        "  ?evidence <https://w3id.org/biolink/vocab/publications> ?publications .\n"
        "  ?evidence <https://w3id.org/biolink/vocab/sentence> ?sentence .\n"
        "  ?evidence <https://w3id.org/biolink/vocab/subject_spans> ?subject_spans .\n"
        "  ?evidence <https://w3id.org/biolink/vocab/object_spans> ?object_spans .\n"
        "  ?evidence <https://w3id.org/biolink/vocab/provided_by> ?provided_by .\n"
        "  ?evidence <https://w3id.org/biolink/vocab/score> ?score .\n"
        "}"
    )


# def get_CAM_query(src, pred, obj):
#     """Generate query to get asserted CAM including triple."""
#     query = ""
#     for key, value in PREFIXES.items():
#         query += f"PREFIX {key}: <{value}>\n"
#     return (
#         query + "SELECT ?g ?other WHERE {\n"
#         "  GRAPH ?g {\n"
#         f"   <{src}> <{pred}> <{obj}>\n"
#         "  }\n"
#         "  OPTIONAL {\n"
#         "    ?g prov:wasDerivedFrom ?other .\n"
#         "  }\n"
#         "}"
#     )


# def get_CAM_stuff_query(graph):
#     """Generate query to get CAM triples."""
#     query = ""
#     for key, value in PREFIXES.items():
#         query += f"PREFIX {key}: <{value}>\n"
#     return (
#         query + "SELECT ?s_type ?p ?o_type WHERE {\n"
#         f"  GRAPH <{graph}> {{\n"
#         "    ?s ?p ?o .\n"
#         "    ?s rdf:type owl:NamedIndividual .\n"
#         "    ?o rdf:type owl:NamedIndividual .\n"
#         "  }\n"
#         "  ?o sesame:directType ?o_type .\n"
#         "  ?s sesame:directType ?s_type .\n"
#         "}"
#     )
