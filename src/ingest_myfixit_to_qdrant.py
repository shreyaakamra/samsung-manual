"""
ingest_myfixit_to_qdrant.py

Reads downloaded MyFixit category JSON files, turns each repair step into
a chunk, embeds it, and upserts into Qdrant with metadata (category,
subject, guide title, step order, source URL). Same shape as the Samsung
PDF pipeline's ingest_to_qdrant.py, just without the PDF extraction step.
"""

import uuid

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from sentence_transformers import SentenceTransformer

from config import (
    MYFIXIT_CATEGORIES,
    MYFIXIT_JSONS_DIR,
    EMBEDDING_MODEL_NAME,
    EMBEDDING_DIM,
    QDRANT_URL,
    QDRANT_API_KEY,
    QDRANT_COLLECTION,
)
from myfixit_processing import process_category_file


def get_qdrant_client() -> QdrantClient:
    return QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)


def ensure_collection(client: QdrantClient):
    existing = [c.name for c in client.get_collections().collections]
    if QDRANT_COLLECTION not in existing:
        client.create_collection(
            collection_name=QDRANT_COLLECTION,
            vectors_config=VectorParams(size=EMBEDDING_DIM, distance=Distance.COSINE),
        )
        print(f"Created Qdrant collection '{QDRANT_COLLECTION}'")
    else:
        print(f"Using existing Qdrant collection '{QDRANT_COLLECTION}'")


def main():
    embedder = SentenceTransformer(EMBEDDING_MODEL_NAME)
    client = get_qdrant_client()
    ensure_collection(client)

    total_chunks = 0
    for category in MYFIXIT_CATEGORIES:
        json_path = MYFIXIT_JSONS_DIR / f"{category}.json"
        if not json_path.exists():
            print(f"[skip] {json_path} not found — run download_myfixit.py first")
            continue

        print(f"\nProcessing category: {category}")
        chunks = process_category_file(json_path)
        print(f"  {len(chunks)} steps extracted")

        # Embed and upsert in batches to keep memory/requests reasonable
        batch_size = 256
        for i in range(0, len(chunks), batch_size):
            batch = chunks[i : i + batch_size]
            texts = [c.text for c in batch]
            vectors = embedder.encode(texts, show_progress_bar=False)

            points = [
                PointStruct(
                    id=str(uuid.uuid4()),
                    vector=vector.tolist(),
                    payload={
                        "text": chunk.text,
                        "guide_title": chunk.guide_title,
                        "guide_id": chunk.guide_id,
                        "category": chunk.category,
                        "subject": chunk.subject,
                        "step_order": chunk.step_order,
                        "step_id": chunk.step_id,
                        "url": chunk.url,
                    },
                )
                for chunk, vector in zip(batch, vectors)
            ]
            client.upsert(collection_name=QDRANT_COLLECTION, points=points)
            total_chunks += len(points)
            print(f"  upserted batch {i // batch_size + 1} ({len(points)} chunks)")

    print(f"\nDone. {total_chunks} total chunks indexed in '{QDRANT_COLLECTION}'.")


if __name__ == "__main__":
    main()