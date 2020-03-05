"""Build a SPARQL Query."""
from collections import defaultdict

from core.utilities import PREFIXES, snake_to_pascal, pascal_to_snake, apply_prefix


def build_query(qgraph):
    """Build a SPARQL Query string."""
    query = ''
    for key, value in PREFIXES.items():
        query += f'PREFIX {key}: <{value}>\n'
    ids = [f"?{node['id']}_type" for node in qgraph['nodes']]
    ids += [f"?{edge['id']}" for edge in qgraph['edges']]
    var_string = ' '.join(ids)
    query += f'\nSELECT DISTINCT {var_string} WHERE {{\n'
    for node in qgraph["nodes"]:
        # enforce node curie
        if node['curie']:
            query += f"  ?{node['id']} rdf:type {node['curie']} .\n"

        # enforce node type
        if node['type']:
            pascal_node_type = snake_to_pascal(node['type'])
            query += f"  bl:{pascal_node_type} ^blml:is_a*/blml:class_uri ?{node['type']} .\n"
            query += f"  ?{node['id']} rdf:type ?{node['type']} .\n"

        # get node "direct type" (curie)
        query += f"  ?{node['id']} sesame:directType ?{node['id']}_type .\n"

    for edge in qgraph['edges']:
        # enforce edge type
        query += f"  bl:{edge['type']} blml:slot_uri ?{edge['id']} .\n"

        # enforce connectivity
        query += f"  ?{edge['source_id']} ?{edge['id']} ?{edge['target_id']} .\n"

    query += "}"
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
        query += f"  ?{qid}_blslot blml:slot_uri {kid} .\n"

    query += "}"
    return query, node_map, {key: edge_map[value] for key, value in edge_map2.items()}


def parse_response(response, qgraph):
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
        for qnode in qgraph['nodes']:
            node_id = apply_prefix(row[f"{qnode['id']}_type"]['value'])
            kgraph['nodes'][node_id] = {
                'id': node_id,
            }
            result['node_bindings'].append({
                'qg_id': qnode['id'],
                'kg_id': node_id,
            })
        # handle edges
        for qedge in qgraph['edges']:
            edge_id = f'e{edge_idx:04d}'
            edge_type = apply_prefix(row[f"{qedge['id']}"]['value'])
            source_id = apply_prefix(row[f"{qedge['source_id']}_type"]['value'])
            target_id = apply_prefix(row[f"{qedge['target_id']}_type"]['value'])
            kgraph['edges'][edge_id] = {
                'id': edge_id,
                'type': edge_type,
                'source_id': source_id,
                'target_id': target_id,
            }
            result['edge_bindings'].append({
                'qg_id': qedge['id'],
                'kg_id': edge_id,
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
            edge_type = node_type = apply_prefix(row[f"{qid}_blslot"]['value']).split(':', 1)[1]
            for kid in kids:
                edges[kid]['type'] = edge_type
    kgraph['edges'] = list(edges.values())

    return kgraph
