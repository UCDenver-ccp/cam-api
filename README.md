# REST API for the Text Mining Provider text-mined Biolink association KG

This TRAPI is available in the [SmartAPI registry](https://smart-api.info/ui/4ea6d865ffb6de29023e0f294347526e).

## Installation

### Docker Installation

```bash
> docker-compose build
```

## Deployment

### Docker Deployment

```bash
> docker-compose up
```
__Access Swagger UI at `http://HOST/docs`.__

## Usage

This REST portal serves Biolink associations that have been mined from the scientific literature. <br> 
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
                        <li> Example input:
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
<h3>Provenance</h3>
  <p>Provenance for each edge is included as part of the <i>edge_bindings</i> in the <i>results</i> payload. The provenance includes the publication identifier, the sentence from which the association was mined, character offsets for the subject and object, and a score provided by the classifier that identified the association. An example is shown below:</p>
    <pre>
    [
    &nbsp;&nbsp;{
    &nbsp;&nbsp;&nbsp;&nbsp;'publication': 'PMID:29085514', 
    &nbsp;&nbsp;&nbsp;&nbsp;'score': '0.99956816', 
    &nbsp;&nbsp;&nbsp;&nbsp;'sentence': 'The administration of 50 ?g/ml bupivacaine promoted maximum breast cancer cell invasion, and suppressed LRRC3B mRNA expression in cells.', 
    &nbsp;&nbsp;&nbsp;&nbsp;'subject_spans': 'start: 31, end: 42', 
    &nbsp;&nbsp;&nbsp;&nbsp;'object_spans': 'start: 104, end: 110', 
    &nbsp;&nbsp;&nbsp;&nbsp;'provided_by': 'TMProvider'
    &nbsp;&nbsp;}
    ]
    </pre>
