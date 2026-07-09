"""
ingest_to_qdrant.py

Reads manifest.json (built by download_manuals.py), extracts + chunks each
PDF, embeds the chunks, and upserts them into a Qdrant collection with
metadata payload (product_name, category, manual_type, page_number).

This is the same shape as your FAISS pipeline from the pdf_q-a project —
main difference is Qdrant stores metadata alongside each vector, so you can
filter searches later (e.g. only search "Galaxy S24" chunks).
"""

import json
import uuid

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from sentence_transformers import SentenceTransformer

from config import (
    MANIFEST_PATH,
    EMBEDDING_MODEL_NAME,
    EMBEDDING_DIM,
    QDRANT_URL,
    QDRANT_API_KEY,
    QDRANT_COLLECTION,
)
from pdf_processing import process_pdf


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


def load_manifest() -> list[dict]:
    if not MANIFEST_PATH.exists():
        raise FileNotFoundError(
            f"No manifest found at {MANIFEST_PATH}. Run download_manuals.py first."
        )
    return json.loads(MANIFEST_PATH.read_text())


def main():
    manifest = load_manifest()
    print(f"Loaded manifest with {len(manifest)} manuals")

    print(f"Loading embedding model '{EMBEDDING_MODEL_NAME}'...")
    embedder = SentenceTransformer(EMBEDDING_MODEL_NAME)

    client = get_qdrant_client()
    ensure_collection(client)

    total_chunks = 0
    for entry in manifest:
        print(f"\nProcessing: {entry['product_name']} ({entry['file_name']})")
        chunks = process_pdf(entry["local_path"])
        print(f"  extracted {len(chunks)} chunks")

        if not chunks:
            continue

        texts = [c.text for c in chunks]
        vectors = embedder.encode(texts, show_progress_bar=False)

        points = []
        for chunk, vector in zip(chunks, vectors):
            points.append(
                PointStruct(
                    id=str(uuid.uuid4()),
                    vector=vector.tolist(),
                    payload={
                        "text": chunk.text,
                        "product_name": entry["product_name"],
                        "category": entry["category"],
                        "manual_type": entry["manual_type"],
                        "source_file": entry["file_name"],
                        "page_number": chunk.page_number,
                    },
                )
            )

        client.upsert(collection_name=QDRANT_COLLECTION, points=points)
        total_chunks += len(points)
        print(f"  upserted {len(points)} chunks into Qdrant")

    print(f"\nDone. {total_chunks} total chunks indexed in '{QDRANT_COLLECTION}'.")


if __name__ == "__main__":
    main()
