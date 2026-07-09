"""
Shared config. Same chunking values you used in the pdf_q-a project
(chunk_size=600, chunk_overlap=80) — carried over since they worked well.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()  # reads variables from a local .env file (never commit that file)

# Paths
PROJECT_ROOT = Path(__file__).parent.parent
MANUALS_DIR = PROJECT_ROOT / "manuals"
MANIFEST_PATH = MANUALS_DIR / "manifest.json"

# Chunking
CHUNK_SIZE = 600
CHUNK_OVERLAP = 80

# Embeddings
EMBEDDING_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
EMBEDDING_DIM = 384  # matches all-MiniLM-L6-v2 output size

# Qdrant
# Local dev default is http://localhost:6333 with no API key.
# For Qdrant Cloud, set QDRANT_URL and QDRANT_API_KEY in a local .env file:
#   QDRANT_URL=https://your-cluster-url.qdrant.io
#   QDRANT_API_KEY=your-api-key-here
QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")  # None for local dev, fine as-is
QDRANT_COLLECTION = "samsung_manuals"

# Retrieval
RETRIEVAL_K = 5
