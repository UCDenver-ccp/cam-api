"""ReasonerStdAPI models."""
from typing import Union, List, Dict
from pydantic import BaseModel, AnyUrl

# https://github.com/swagger-api/swagger-ui/issues/5804


class BiolinkEntity(str):
    """Biolink entity."""


class BiolinkRelation(str):
    """Biolink relation."""


class QNode(BaseModel):
    """Query node."""

    id: str
    curie: Union[str, List[str]] = None
    type: Union[str, List[str]] = None


class QEdge(BaseModel):
    """Query edge."""

    id: str
    type: Union[str, List[str]] = None
    source_id: str
    target_id: str


class Node(BaseModel):
    """Knowledge graph node."""

    id: str
    name: str = None
    type: Union[BiolinkEntity, List[BiolinkEntity]] = None


class Edge(BaseModel):
    """Knowledge graph edge."""

    id: str
    type: Union[BiolinkRelation, List[BiolinkRelation]] = None
    source_id: str
    target_id: str


class QueryGraph(BaseModel):
    """Query graph."""

    nodes: List[QNode]
    edges: List[QEdge]


class Credentials(BaseModel):
    """Credentials."""

    username: str
    password: str


class RemoteKnowledgeGraph(BaseModel):
    """Remote knowledge graph."""

    url: AnyUrl
    credentials: Credentials = None
    protocol: str = None


class KnowledgeGraph(BaseModel):
    """Knowledge graph."""

    nodes: List[Node]
    edges: List[Edge]


class EdgeBinding(BaseModel):
    """Edge binding."""

    qg_id: str
    kg_id: Union[str, List[str]]
    provenance: str = None


class NodeBinding(BaseModel):
    """Node binding."""

    qg_id: str
    kg_id: Union[str, List[str]]


class Result(BaseModel):
    """Result."""

    node_bindings: List[NodeBinding]
    edge_bindings: List[EdgeBinding]
    extra_nodes: List[Dict] = None
    extra_edges: List[Dict] = None


class Message(BaseModel):
    """Message."""

    query_graph: QueryGraph = None
    knowledge_graph: Union[KnowledgeGraph, RemoteKnowledgeGraph] = None
    results: List[Result] = None


class Query(BaseModel):
    """Query."""

    message: Message
