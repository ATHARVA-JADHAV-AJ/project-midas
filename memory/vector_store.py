# Project Midas â€” Qdrant Vector Store Interface
# Author: Atharva Kishor Jadhav (AJ)
# ---------------------------------------------------------------
"""
Thin wrapper around the Qdrant Python client for Project Midas.

All operations run against a local Qdrant instance (no cloud API).
The collection name and vector size are configured via environment variables.
"""

import os
import logging
import uuid
from typing import List, Optional
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue
)

logger = logging.getLogger(__name__)

QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
COLLECTION = os.getenv("QDRANT_COLLECTION", "midas_docs")
# nomic-embed-text produces 768-dimension vectors
VECTOR_SIZE = int(os.getenv("VECTOR_SIZE", "768"))


def get_client() -> QdrantClient:
    return QdrantClient(url=QDRANT_URL)


def ensure_collection(client: Optional[QdrantClient] = None) -> None:
    """
    Create the collection if it doesn't exist.
    Safe to call multiple times â€” checks first.
    """
    c = client or get_client()
    existing = [col.name for col in c.get_collections().collections]
    if COLLECTION not in existing:
        c.create_collection(
            collection_name=COLLECTION,
            vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE),
        )
        logger.info(f"Created Qdrant collection '{COLLECTION}' ({VECTOR_SIZE}d, cosine)")


def upsert_chunks(chunks: List[str], vectors: List[List[float]], metadata: Optional[List[dict]] = None) -> int:
    """
    Upsert a batch of text chunks and their pre-computed vectors into the collection.
    Returns the number of points upserted.
    """
    c = get_client()
    ensure_collection(c)

    points = [
        PointStruct(
            id=str(uuid.uuid4()),
            vector=vec,
            payload={"text": chunk, **(metadata[i] if metadata else {})},
        )
        for i, (chunk, vec) in enumerate(zip(chunks, vectors))
    ]
    c.upsert(collection_name=COLLECTION, points=points)
    logger.info(f"Upserted {len(points)} chunks into '{COLLECTION}'")
    return len(points)


def search_similar(query_vector: List[float], top_k: int = 5) -> List[str]:
    """
    Retrieve the top-k most similar text chunks for a given query vector.
    Returns a list of text strings (the chunk content), not full point objects.
    """
    c = get_client()
    results = c.query_points(
        collection_name=COLLECTION,
        query=query_vector,
        limit=top_k,
        with_payload=True,
    )
    return [hit.payload.get("text", "") for hit in results.points]



