"""ChromaDB client for RAG retrieval.

Manages two collections:
  - sao_progressive_novels: Novel text chunks (populated by ingest_novels.py)
  - sao_world_entities: Monster/NPC/quest descriptions (populated by vectorize_entities.py)
"""

import logging
import time
from pathlib import Path

import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction

logger = logging.getLogger(__name__)

EMBEDDING_MODEL = "BAAI/bge-small-zh-v1.5"
COLLECTION_NOVELS = "sao_progressive_novels"
COLLECTION_ENTITIES = "sao_world_entities"

_client: chromadb.ClientAPI | None = None
_embedding_fn: SentenceTransformerEmbeddingFunction | None = None


def init_chromadb(chromadb_path: str | None = None) -> chromadb.ClientAPI:
    """Initialize the ChromaDB persistent client."""
    global _client, _embedding_fn
    if _client is not None:
        return _client

    if chromadb_path is None:
        chromadb_path = str(
            Path(__file__).resolve().parent.parent.parent.parent / "data" / "chromadb"
        )

    logger.info("Connecting to ChromaDB at %s", chromadb_path)
    _client = chromadb.PersistentClient(path=chromadb_path)
    _embedding_fn = SentenceTransformerEmbeddingFunction(model_name=EMBEDDING_MODEL)
    logger.info("ChromaDB initialized")
    return _client


def get_chromadb() -> chromadb.ClientAPI:
    """Get the active ChromaDB client. Raises if not initialized."""
    if _client is None:
        raise RuntimeError("ChromaDB not initialized. Call init_chromadb() first.")
    return _client


def get_embedding_fn() -> SentenceTransformerEmbeddingFunction:
    """Get the shared embedding function."""
    if _embedding_fn is None:
        raise RuntimeError("ChromaDB not initialized. Call init_chromadb() first.")
    return _embedding_fn


def _get_collection(name: str) -> chromadb.Collection:
    """Get or create a collection with the shared embedding function."""
    client = get_chromadb()
    return client.get_or_create_collection(
        name=name,
        embedding_function=get_embedding_fn(),
    )


def query_novels(
    query_text: str,
    n_results: int = 5,
    floor_filter: int | None = None,
    trace_id: str = "no-trace",
) -> list[dict]:
    """Query novel chunks by semantic similarity.

    Args:
        query_text: The search query
        n_results: Max results to return
        floor_filter: Optional filter by Aincrad floor
        trace_id: Trace ID for logging

    Returns:
        List of {text, metadata, distance} dicts, sorted by relevance
    """
    start_time = time.time()
    collection = _get_collection(COLLECTION_NOVELS)
    if collection.count() == 0:
        logger.warning("trace=%s step=rag_retrieve collection=novels status=empty", trace_id)
        return []

    where = {"aincrad_layer": floor_filter} if floor_filter else None
    
    try:
        results = collection.query(
            query_texts=[query_text],
            n_results=n_results,
            where=where,
        )

        output = []
        for i in range(len(results["documents"][0])):
            output.append({
                "text": results["documents"][0][i],
                "metadata": results["metadatas"][0][i],
                "distance": results["distances"][0][i],
            })
        
        latency_ms = (time.time() - start_time) * 1000
        top_score = output[0]["distance"] if output else 0.0
        logger.info(
            "trace=%s step=rag_retrieve collection=novels chunks=%d top_score=%.3f latency_ms=%.1f",
            trace_id, len(output), top_score, latency_ms
        )
        return output
    except Exception as e:
        latency_ms = (time.time() - start_time) * 1000
        logger.error(
            "trace=%s step=rag_retrieve collection=novels status=error error=%s latency_ms=%.1f",
            trace_id, e, latency_ms
        )
        raise


def query_entities(
    query_text: str,
    n_results: int = 5,
    entity_type: str | None = None,
    floor_filter: int | None = None,
    trace_id: str = "no-trace",
) -> list[dict]:
    """Query world entity descriptions by semantic similarity.

    Args:
        query_text: The search query
        n_results: Max results to return
        entity_type: Optional filter: "monster", "npc", or "quest"
        floor_filter: Optional filter by floor number
        trace_id: Trace ID for logging

    Returns:
        List of {text, metadata, distance} dicts, sorted by relevance
    """
    start_time = time.time()
    collection = _get_collection(COLLECTION_ENTITIES)
    if collection.count() == 0:
        logger.warning("trace=%s step=rag_retrieve collection=entities status=empty", trace_id)
        return []

    where_clauses = []
    if entity_type:
        where_clauses.append({"entity_type": entity_type})
    if floor_filter:
        where_clauses.append({"floor": floor_filter})

    where = None
    if len(where_clauses) == 1:
        where = where_clauses[0]
    elif len(where_clauses) > 1:
        where = {"$and": where_clauses}

    try:
        results = collection.query(
            query_texts=[query_text],
            n_results=n_results,
            where=where,
        )

        output = []
        for i in range(len(results["documents"][0])):
            output.append({
                "text": results["documents"][0][i],
                "metadata": results["metadatas"][0][i],
                "distance": results["distances"][0][i],
            })
        
        latency_ms = (time.time() - start_time) * 1000
        top_score = output[0]["distance"] if output else 0.0
        logger.info(
            "trace=%s step=rag_retrieve collection=entities entity_type=%s chunks=%d top_score=%.3f latency_ms=%.1f",
            trace_id, entity_type or "all", len(output), top_score, latency_ms
        )
        return output
    except Exception as e:
        latency_ms = (time.time() - start_time) * 1000
        logger.error(
            "trace=%s step=rag_retrieve collection=entities status=error error=%s latency_ms=%.1f",
            trace_id, e, latency_ms
        )
        raise


def query_combined(
    query_text: str,
    n_novels: int = 3,
    n_entities: int = 3,
    floor_filter: int | None = None,
) -> list[str]:
    """Query both collections and return merged text chunks for context injection.

    Returns deduplicated text strings sorted by relevance, ready for
    context_builder's rag_chunks parameter.
    """
    novel_results = query_novels(query_text, n_results=n_novels, floor_filter=floor_filter)
    entity_results = query_entities(query_text, n_results=n_entities, floor_filter=floor_filter)

    # Merge and sort by distance (lower = more relevant)
    all_results = []
    for r in novel_results:
        all_results.append((r["distance"], f"[小说参考] {r['text']}"))
    for r in entity_results:
        etype = r["metadata"].get("entity_type", "unknown")
        all_results.append((r["distance"], f"[{etype}数据] {r['text']}"))

    all_results.sort(key=lambda x: x[0])
    return [text for _, text in all_results]
