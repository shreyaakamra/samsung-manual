"""
search.py

Filtered semantic search over the MyFixit-indexed Qdrant collection.
Filter by category (e.g. "Phone") and/or subject (e.g. "Battery") to scope
retrieval, same pattern as the Samsung manuals project.
"""

from qdrant_client.models import Filter, FieldCondition, MatchValue
from sentence_transformers import SentenceTransformer

from config import EMBEDDING_MODEL_NAME, QDRANT_COLLECTION, RETRIEVAL_K
from ingest_myfixit_to_qdrant import get_qdrant_client


def search(query: str, category: str | None = None, subject: str | None = None, k: int = RETRIEVAL_K):
    embedder = SentenceTransformer(EMBEDDING_MODEL_NAME)
    client = get_qdrant_client()

    query_vector = embedder.encode(query).tolist()

    conditions = []
    if category:
        conditions.append(FieldCondition(key="category", match=MatchValue(value=category)))
    if subject:
        conditions.append(FieldCondition(key="subject", match=MatchValue(value=subject)))

    query_filter = Filter(must=conditions) if conditions else None

    response = client.query_points(
        collection_name=QDRANT_COLLECTION,
        query=query_vector,
        query_filter=query_filter,
        limit=k,
    )
    results = response.points

    for r in results:
        print(f"\n[score={r.score:.3f}] {r.payload['guide_title']} "
              f"(step {r.payload['step_order']}, category: {r.payload['category']})")
        print(f"  {r.payload['text'][:200]}...")
        print(f"  source: {r.payload['url']}")

    return results


if __name__ == "__main__":
    search("how do I replace the battery", category="Phone")