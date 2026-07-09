"""
search.py

Example filtered search against the Qdrant collection. This is the payoff
for tagging metadata during ingestion — you can scope retrieval to a
specific product or category instead of searching everything.
"""

from qdrant_client.models import Filter, FieldCondition, MatchValue
from sentence_transformers import SentenceTransformer

from config import EMBEDDING_MODEL_NAME, QDRANT_COLLECTION, RETRIEVAL_K
from ingest_to_qdrant import get_qdrant_client


def search(query: str, product_name: str | None = None, category: str | None = None, k: int = RETRIEVAL_K):
    embedder = SentenceTransformer(EMBEDDING_MODEL_NAME)
    client = get_qdrant_client()

    query_vector = embedder.encode(query).tolist()

    conditions = []
    if product_name:
        conditions.append(FieldCondition(key="product_name", match=MatchValue(value=product_name)))
    if category:
        conditions.append(FieldCondition(key="category", match=MatchValue(value=category)))

    query_filter = Filter(must=conditions) if conditions else None

    response = client.query_points(
        collection_name=QDRANT_COLLECTION,
        query=query_vector,
        query_filter=query_filter,
        limit=k,
    )
    results = response.points

    for r in results:
        print(f"\n[score={r.score:.3f}] {r.payload['product_name']} "
              f"(p.{r.payload['page_number']}, {r.payload['source_file']})")
        print(f"  {r.payload['text'][:200]}...")

    return results


if __name__ == "__main__":
    # Example: only search Galaxy S24 manual chunks
    search("how do I reset my phone to factory settings", product_name="Galaxy S24")
