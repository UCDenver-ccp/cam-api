"""Utilities."""
import re

PREFIXES = {
    'rdf': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#',
    'rdfs': 'http://www.w3.org/2000/01/rdf-schema#',
    'go': 'http://www.geneontology.org/formats/oboInOwl#',
    'blml': 'https://w3id.org/biolink/biolinkml/meta/',
    'bl': 'https://w3id.org/biolink/vocab/',
    'MONDO': 'http://purl.obolibrary.org/obo/MONDO_',
    'SO': 'http://purl.obolibrary.org/obo/SO_',
    'RO': 'http://purl.obolibrary.org/obo/RO_',
    'GO': 'http://purl.obolibrary.org/obo/GO_',
    'obo': 'http://purl.obolibrary.org/obo/',
    'NCBIGENE': 'http://identifiers.org/ncbigene:',
    'sesame': 'http://www.openrdf.org/schema/sesame#',
}


def snake_to_pascal(string):
    """Convert snake-case string to pascal-case."""
    return string[0].upper() + re.sub('_([a-z])', lambda match: match.group(1).upper(), string[1:])


def pascal_to_snake(string):
    """Convert pascal-case string to snake-case."""
    return string[0].lower() + re.sub('[A-Z]', lambda match: '_' + match.group(0).lower(), string[1:])


def apply_prefix(string):
    """Apply the last matching prefix."""
    for short, long in PREFIXES.items():
        if string.startswith(long):
            return short + ':' + string[len(long):]