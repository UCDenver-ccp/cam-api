"""Build a SPARQL Query."""
import re


def snake_to_pascal(string):
    """Convert snake-case string to pascal-case."""
    return string[0].upper() + re.sub('_([a-z])', lambda match: match.group(1).upper(), string[1:])


PREFIXES = {
    'rdf': '<http://www.w3.org/1999/02/22-rdf-syntax-ns#>',
    'rdfs': '<http://www.w3.org/2000/01/rdf-schema#>',
    'go': '<http://www.geneontology.org/formats/oboInOwl#>',
    'blml': '<https://w3id.org/biolink/biolinkml/meta/>',
    'bl': '<https://w3id.org/biolink/vocab/>',
    'MONDO': '<http://purl.obolibrary.org/obo/MONDO_>',
    'SO': '<http://purl.obolibrary.org/obo/SO_>',
    'RO': '<http://purl.obolibrary.org/obo/RO_>',
    'obo': '<http://purl.obolibrary.org/obo/>',
    'NCBIGENE': '<http://identifiers.org/ncbigene:>',
}


def build_query(qgraph):
    """Build a SPARQL Query string."""
    query = ''
    for key, value in PREFIXES.items():
        query += f'PREFIX {key}: {value}\n'
    query += '\nSELECT DISTINCT * WHERE {\n'
    for node in qgraph["nodes"]:
        if node['curie']:
            query += f"  ?{node['id']} rdf:type {node['curie']} .\n"

        if node['type']:
            pascal_node_type = snake_to_pascal(node['type'])
            query += f"  bl:{pascal_node_type} blml:class_uri ?{node['type']} .\n"
            query += f"  ?{node['id']} rdf:type ?{node['type']} .\n"

        # query += f"{node_id_to_uri[node_id]} rdfs:label ?{node_id}label .\n"

    for edge in qgraph['edges']:
        query += f"  bl:{edge['type']} blml:slot_uri ?{edge['id']} .\n"
        query += f"  ?{edge['source_id']} ?{edge['id']} ?{edge['target_id']} .\n"

    query += "}"
    return query


def parse_response(response, qgraph):
    """Parse the query response."""
    results = []
    kgraph = {
        "nodes": dict(),
        "edges": []
    }
    edge_id = 0
    for row in response:
        result = {
            "node_bindings": [],
            "edge_bindings": []
        }
        for qg_node in qgraph['nodes']:
            node_id = row[qg_node['id']]['value']
            kgraph['nodes'][node_id] = {
                'id': node_id,
                'type': row[qg_node['type']]['value'],
            }
            result['node_bindings'].append({
                'qg_id': qg_node['id'],
                'kg_id': node_id,
            })
        for qedge in qgraph['edges']:
            kgraph['edges'].append({
                'id': edge_id,
                'type': row[qedge['id']]['value'],
                'source_id': row[qedge['source_id']]['value'],
                'target_id': row[qedge['target_id']]['value'],
            })
            result['edge_bindings'].append({
                'qg_id': qedge['id'],
                'kg_id': edge_id,
            })
            edge_id += 1
        results.append(result)

    kgraph['nodes'] = list(kgraph['nodes'].values())

    return kgraph, results
