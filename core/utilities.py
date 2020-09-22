"""Utilities."""
from collections import defaultdict
import copy
import hashlib
import json
import re

import httpx

# "backend" matches the Docker container name for the container with the Blazegraph instance
# "assoc" is the namespace/repository name where the triples have loaded
BLAZEGRAPH_URL = "http://backend:9999/blazegraph/namespace/assoc/sparql"
BLAZEGRAPH_HEADERS = {
    "content-type": "application/sparql-query",
    "Accept": "application/json",
}
PREFIXES = {
    "BFO": "http://purl.obolibrary.org/obo/BFO_",
    "BIOGRID": "http://thebiogrid.org/",
    "BioSample": "http://example.org/UNKNOWN/BioSample/",
    "CAID": "http://example.org/UNKNOWN/CAID/",
    "CHEBI": "http://purl.obolibrary.org/obo/CHEBI_",
    "CHEMBL.COMPOUND": "http://identifiers.org/chembl.compound/",
    "CHEMBL.TARGET": "http://identifiers.org/chembl.target/",
    "CIO": "http://purl.obolibrary.org/obo/CIO_",
    "CIViC": "http://example.org/UNKNOWN/CIViC/",
    "CL": "http://purl.obolibrary.org/obo/CL_",
    "CLO": "http://purl.obolibrary.org/obo/CLO_",
    "ClinVar": "http://www.ncbi.nlm.nih.gov/clinvar/",
    "DBSNP": "http://identifiers.org/dbsnp/",
    "DOID": "http://purl.obolibrary.org/obo/DOID_",
    "DRUGBANK": "http://identifiers.org/drugbank/",
    "ECO": "http://purl.obolibrary.org/obo/ECO_",
    "ECTO": "http://example.org/UNKNOWN/ECTO/",
    "EFO": "http://purl.obolibrary.org/obo/EFO_",
    "ENSEMBL": "http://ensembl.org/id/",
    "ExO": "http://example.org/UNKNOWN/ExO/",
    "FAO": "http://purl.obolibrary.org/obo/FAO_",
    "GENO": "http://purl.obolibrary.org/obo/GENO_",
    "GO": "http://purl.obolibrary.org/obo/GO_",
    "GOLD.META": "http://identifiers.org/gold.meta/",
    "GTOPDB": "http://example.org/UNKNOWN/GTOPDB/",
    "HANCESTRO": "http://example.org/UNKNOWN/HANCESTRO/",
    "HGNC": "http://www.genenames.org/cgi-bin/gene_symbol_report?hgnc_id=",
    "HGVS": "http://example.org/UNKNOWN/HGVS/",
    "HMDB": "http://www.hmdb.ca/metabolites/",
    "HP": "http://purl.obolibrary.org/obo/HP_",
    "IAO": "http://purl.obolibrary.org/obo/IAO_",
    "INCHI": "http://identifiers.org/inchi/",
    "INCHIKEY": "http://identifiers.org/inchikey/",
    "IUPHAR": "http://example.org/UNKNOWN/IUPHAR/",
    "IntAct": "http://example.org/UNKNOWN/IntAct/",
    "KEGG": "http://identifiers.org/kegg/",
    "MEDDRA": "http://purl.bioontology.org/ontology/MEDDRA/",
    "MGI": "http://www.informatics.jax.org/accession/MGI:",
    "MIR": "http://identifiers.org/mir/",
    "MONDO": "http://purl.obolibrary.org/obo/MONDO_",
    "MYVARIANT_HG19": "http://example.org/UNKNOWN/MYVARIANT_HG19/",
    "MYVARIANT_HG38": "http://example.org/UNKNOWN/MYVARIANT_HG38/",
    "NCBIGene": "http://www.ncbi.nlm.nih.gov/gene/",
    "NCIT": "http://purl.obolibrary.org/obo/NCIT_",
    "OBAN": "http://purl.org/oban/",
    "OBI": "http://purl.obolibrary.org/obo/OBI_",
    "OGMS": "http://purl.obolibrary.org/obo/OGMS_",
    "OIO": "http://www.geneontology.org/formats/oboInOwl#",
    "OMIM": "http://purl.obolibrary.org/obo/OMIM_",
    "ORPHANET": "http://identifiers.org/orphanet/",
    "PANTHER": "http://www.pantherdb.org/panther/family.do?clsAccession=",
    "PMID": "http://www.ncbi.nlm.nih.gov/pubmed/",
    "PO": "http://purl.obolibrary.org/obo/PO_",
    "PR": "http://purl.obolibrary.org/obo/PR_",
    "PW": "http://purl.obolibrary.org/obo/PW_",
    "PomBase": "https://www.pombase.org/spombe/result/",
    "RHEA": "http://identifiers.org/rhea/",
    "RO": "http://purl.obolibrary.org/obo/RO_",
    "SGD": "https://www.yeastgenome.org/locus/",
    "SIO": "http://semanticscience.org/resource/SIO_",
    "SMPDB": "http://smpdb.ca/view/",
    "SO": "http://purl.obolibrary.org/obo/SO_",
    "UBERON": "http://purl.obolibrary.org/obo/UBERON_",
    "UMLS": "http://linkedlifedata.com/resource/umls/id/",
    "UMLSSC": "https://uts-ws.nlm.nih.gov/rest/semantic-network/semantic-network/current/TUI/",
    "UMLSSG": "https://uts-ws.nlm.nih.gov/rest/semantic-network/semantic-network/current/GROUP/",
    "UMLSST": "https://uts-ws.nlm.nih.gov/rest/semantic-network/semantic-network/current/STY/",
    "UNII": "http://fdasis.nlm.nih.gov/srs/unii/",
    "UPHENO": "http://purl.obolibrary.org/obo/UPHENO_",
    "UniProtKB": "http://identifiers.org/uniprot/",
    "VMC": "http://example.org/UNKNOWN/VMC/",
    "WB": "http://identifiers.org/wb/",
    "WD": "http://example.org/UNKNOWN/WD/",
    "WIKIPATHWAYS": "http://identifiers.org/wikipathways/",
    "ZFIN": "http://zfin.org/",
    "biolinkml": "https://w3id.org/biolink/biolinkml/",
    "dct": "http://example.org/UNKNOWN/dct/",
    "dcterms": "http://purl.org/dc/terms/",
    "dictyBase": "http://dictybase.org/gene/",
    "faldo": "http://biohackathon.org/resource/faldo#",
    "metatype": "https://w3id.org/biolink/biolinkml/type/",
    "owl": "http://www.w3.org/2002/07/owl#",
    "pav": "http://purl.org/pav/",
    "qud": "http://qudt.org/1.1/schema/qudt#",
    "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
    "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
    "shex": "http://www.w3.org/ns/shex#",
    "skos": "https://www.w3.org/TR/skos-reference/#",
    "void": "http://rdfs.org/ns/void#",
    "wgs": "http://www.w3.org/2003/01/geo/wgs84_pos",
    "xsd": "http://www.w3.org/2001/XMLSchema#",
    "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
    "go": "http://www.geneontology.org/formats/oboInOwl#",
    "blml": "https://w3id.org/biolink/biolinkml/meta/",
    "bl": "https://w3id.org/biolink/vocab/",
    "MONDO": "http://purl.obolibrary.org/obo/MONDO_",
    "EMAPA": "http://purl.obolibrary.org/obo/EMAPA_",
    "SO": "http://purl.obolibrary.org/obo/SO_",
    "RO": "http://purl.obolibrary.org/obo/RO_",
    "GO": "http://purl.obolibrary.org/obo/GO_",
    "CHEBI": "http://purl.obolibrary.org/obo/CHEBI_",
    "BFO": "http://purl.obolibrary.org/obo/BFO_",
    "obo": "http://purl.obolibrary.org/obo/",
    "NCBIGENE": "http://identifiers.org/ncbigene:",
    "sesame": "http://www.openrdf.org/schema/sesame#",
    "owl": "http://www.w3.org/2002/07/owl#",
    "prov": "http://www.w3.org/ns/prov#",
    "MESH": "http://id.nlm.nih.gov/mesh/",
}


def hash_dict(_dict):
    """Compute a hash string for a dict."""
    return hashlib.sha256(json.dumps(_dict).encode("utf-8")).hexdigest()


def snake_to_pascal(string):
    """Convert snake-case string to pascal-case."""
    return string[0].upper() + re.sub(
        "_([a-z])", lambda match: match.group(1).upper(), string[1:]
    )


def pascal_to_snake(string):
    """Convert pascal-case string to snake-case."""
    return string[0].lower() + re.sub(
        "[A-Z]", lambda match: "_" + match.group(0).lower(), string[1:]
    )


def apply_prefix(string):
    """Apply the last matching prefix."""
    for short, long in PREFIXES.items():
        if string.startswith(long):
            return short + ":" + string[len(long) :]
    return string


def unprefix(curie):
    """Expand a CURIE to a full URI."""
    parts = curie.split(":", 1)
    if len(parts) > 1 and parts[0] in PREFIXES:
        return PREFIXES.get(parts[0]) + parts[1]
    else:
        return curie


BIG_NUMBER = 99999


def trim_qgraph(qgraph):
    """Return a generator of sub-qgraphs with one edge removed.

    The chosen edge will be one of the ones with the lowest combined endpoint degree.
    No edge connected to a node with prescribed curie will be removed.
    After removing the edge, nodes with degree zero will be removed.
    """
    node_degree = defaultdict(int)
    for edge in qgraph["edges"]:
        node_degree[edge["source_id"]] += 1
        node_degree[edge["target_id"]] += 1
    for node in qgraph["nodes"]:
        if node.get("curie", None):
            node_degree[node["id"]] = BIG_NUMBER
    edge_importance = {
        edge["id"]: node_degree[edge["source_id"]] + node_degree[edge["target_id"]]
        for edge in qgraph["edges"]
    }
    min_importance = min(edge_importance.values())
    if min_importance >= BIG_NUMBER:
        return
    for edge in qgraph["edges"]:
        if edge_importance[edge["id"]] == min_importance:
            yield {
                "nodes": qgraph["nodes"],
                "edges": [e for e in qgraph["edges"] if e["id"] != edge["id"]],
            }
    # TODO: remove orphaned nodes


async def run_query(query):
    """Run SPARQL query on Blazegraph database."""
    async with httpx.AsyncClient(timeout=None) as client:
        response = await client.post(
            BLAZEGRAPH_URL,
            headers=BLAZEGRAPH_HEADERS,
            data=query,
        )
    assert response.status_code < 300
    return response.json()["results"]["bindings"]
