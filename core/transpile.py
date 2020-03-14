"""Build a SPARQL Query."""
from collections import defaultdict

import httpx

from core.utilities import PREFIXES, snake_to_pascal, pascal_to_snake, apply_prefix, hash_dict

BLAZEGRAPH_URL = 'https://stars-blazegraph.renci.org/cam/sparql'
BLAZEGRAPH_HEADERS = {
    'content-type': 'application/sparql-query',
    'Accept': 'application/json'
}

def build_query(qgraph, strict=True, limit=-1):
    """Build a SPARQL Query string."""
    query = ''
    for key, value in PREFIXES.items():
        query += f'PREFIX {key}: <{value}>\n'
    ids = [f"?{node['id']}" for node in qgraph['nodes']]
    ids += [f"?{node['id']}_type" for node in qgraph['nodes'] if not node.get('curie', None)]
    ids += list({f"?{edge['type'] or edge['id']}" for edge in qgraph['edges']})
    var_string = ' '.join(ids)
    query += f'\nSELECT DISTINCT {var_string} WHERE {{\n'
    curies = dict()
    for node in qgraph["nodes"]:

        if node['curie']:
            # enforce node curie
            curies[node['id']] = node['curie']
        elif node['type']:
            # enforce node type
            curies[node['id']] = f"?{node['id']}_type"
            pascal_node_type = snake_to_pascal(node['type'])
            query += f"  {curies[node['id']]} rdfs:subClassOf bl:{pascal_node_type} .\n"
        if strict:
            query += f"  ?{node['id']} sesame:directType {curies[node['id']]} .\n"

    predicates = set()
    for idx, edge in enumerate(qgraph['edges']):
        var = edge['type'] or edge['id']
        if edge['type'] and edge['type'] not in predicates:
            # enforce edge type
            query += f"  bl:{edge['type']} <http://reasoner.renci.org/vocab/slot_mapping> ?{var} .\n"
            predicates.add(var)

        # enforce connectivity
        if strict:
            query += f"  ?{edge['source_id']} ?{var} ?{edge['target_id']} .\n"
        else:
            query += f"  ?{edge['source_id']}_{idx} sesame:directType {curies[edge['source_id']]} .\n"
            query += f"  ?{edge['target_id']}_{idx} sesame:directType {curies[edge['target_id']]} .\n"
            query += f"  ?{edge['source_id']}_{idx} ?{var} ?{edge['target_id']}_{idx} .\n"

    query += "}"
    if limit >= 0:
        query += f" LIMIT {limit}"
    return query


def get_details(kgraph):
    """Get node and edge details."""
    node_map = {
        f'n{idx:04d}': node['id']
        for idx, node in enumerate(kgraph['nodes'].values())
    }
    edge_map = defaultdict(list)
    for edge in kgraph['edges'].values():
        edge_map[edge['type']].append(edge['id'])
    edge_map2 = {f'e{idx:04d}': key for idx, key in enumerate(edge_map)}
    query = ''
    for key, value in PREFIXES.items():
        query += f'PREFIX {key}: <{value}>\n'
    var_strings = [f"?{qid}_blclass" for qid in node_map]
    var_strings += [f"?{qid}_label" for qid in node_map]
    var_strings += [f"?{qid}_blslot" for qid in edge_map2]
    var_string = ' '.join(var_strings)
    query += f'\nSELECT DISTINCT {var_string} WHERE {{\n'
    for qid, kid in node_map.items():
        if kid.startswith('http'):
            kid = f'<{kid}>'
        # get node label and biolink class
        query += f"  OPTIONAL {{\n"
        query += f"    {kid} rdfs:subClassOf ?{qid}_class .\n"
        query += f"    ?{qid}_class ^blml:class_uri/blml:isa* ?{qid}_blclass .\n"
        query += f"    OPTIONAL {{{kid} rdfs:label ?{qid}_label .}} .\n"
        query += f"  }} .\n"
    for qid, kid in edge_map2.items():
        if kid.startswith('http'):
            kid = f'<{kid}>'
        # get edge biolink slot
        query += f"  OPTIONAL {{?{qid}_blslot blml:slot_uri {kid} .}} .\n"

    query += "}"
    return query, node_map, {key: edge_map[value] for key, value in edge_map2.items()}


async def parse_response(response, qgraph):
    """Parse the query response."""
    results = []
    kgraph = {
        "nodes": dict(),
        "edges": dict(),
    }
    edge_idx = 0
    for row in response:
        result = {
            "node_bindings": [],
            "edge_bindings": []
        }
        # handle nodes
        node_ids = dict()
        for qnode in qgraph['nodes']:
            if not qnode.get('curie', None):
                node_id = apply_prefix(row[f"{qnode['id']}_type"]['value'])
            else:
                node_id = qnode['curie']
            node_ids[qnode['id']] = node_id
            kgraph['nodes'][node_id] = {
                'id': node_id,
            }
            result['node_bindings'].append({
                'qg_id': qnode['id'],
                'kg_id': node_id,
            })
        # handle edges
        for qedge in qgraph['edges']:
            var = qedge['type'] or qedge['id']
            edge_type = apply_prefix(row[f"{var}"]['value'])
            source_id = node_ids[qedge['source_id']]
            target_id = node_ids[qedge['target_id']]
            edge = {
                'type': edge_type,
                'source_id': source_id,
                'target_id': target_id,
            }
            edge_id = hash_dict(edge)
            kgraph['edges'][edge_id] = {
                'id': edge_id,
                **edge,
            }

            src = row[qedge['source_id']]['value']
            pred = row[qedge['type'] or qedge['id']]['value']
            obj = row[qedge['target_id']]['value']
            query = get_CAM_query(src, pred, obj)
            async with httpx.AsyncClient(timeout=None) as client:
                response = await client.post(
                    BLAZEGRAPH_URL,
                    headers=BLAZEGRAPH_HEADERS,
                    data=query,
                )
            assert response.status_code < 300
            bindings = response.json()['results']['bindings']
            assert len(bindings) == 1
            graph = (bindings[0].get('other', None) or bindings[0]['g'])['value']

            result['edge_bindings'].append({
                'qg_id': qedge['id'],
                'kg_id': edge_id,
                'provenance': graph,
            })
            edge_idx += 1
        results.append(result)

    return kgraph, results


def parse_kgraph(response, node_map, edge_map, kgraph):
    """Parse the query response."""
    nodes = kgraph['nodes']
    for qid, kid in node_map.items():
        nodes[kid]['type'] = set()
        for row in response:
            if f"{qid}_label" in row:
                nodes[kid]['name'] = row[f"{qid}_label"]['value']
            if f"{qid}_blclass" in row:
                node_type = pascal_to_snake(apply_prefix(row[f"{qid}_blclass"]['value']).split(':', 1)[1])
                nodes[kid]['type'].add(node_type)
        nodes[kid]['type'] = list(nodes[kid]['type'])
    kgraph['nodes'] = list(nodes.values())

    edges = kgraph['edges']
    for qid, kids in edge_map.items():
        for row in response:
            if f"{qid}_blslot" not in row:
                continue
            edge_type = node_type = apply_prefix(row[f"{qid}_blslot"]['value']).split(':', 1)[1]
            for kid in kids:
                edges[kid]['type'] = edge_type
    kgraph['edges'] = list(edges.values())

    return kgraph


def get_CAM_query(src, pred, obj):
    """Generate query to get asserted CAM including triple."""
    query = ''
    for key, value in PREFIXES.items():
        query += f'PREFIX {key}: <{value}>\n'
    return query + 'SELECT ?g ?other WHERE {\n' \
        '  GRAPH ?g {\n' \
        f'   <{src}> <{pred}> <{obj}>\n' \
        '  }\n' \
        '  OPTIONAL {\n' \
        '    ?g prov:wasDerivedFrom ?other .\n' \
        '  }\n' \
        '}'


def get_CAM_stuff_query(graph):
    """Generate query to get CAM triples."""
    query = ''
    for key, value in PREFIXES.items():
        query += f'PREFIX {key}: <{value}>\n'
    return query + 'SELECT ?s_type ?p ?o_type WHERE {\n' \
        f'  GRAPH <{graph}> {{\n' \
        '    ?s ?p ?o .\n' \
        '    ?s rdf:type owl:NamedIndividual .\n' \
        '    ?o rdf:type owl:NamedIndividual .\n' \
        '  }\n' \
        '  ?o sesame:directType ?o_type .\n' \
        '  ?s sesame:directType ?s_type .\n' \
        '}'
