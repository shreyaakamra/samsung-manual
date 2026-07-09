# Samsung Manuals RAG

A Retrieval-Augmented Generation (RAG) pipeline for Samsung product manuals.
Indexes manuals into Qdrant with per-product metadata, so questions can be
answered from a specific device's manual (e.g. "Galaxy S24 only") instead of
searching everything at once.

## Why Qdrant instead of FAISS

A related project of mine, [pdf_q-a](https://github.com/shreyaakamra/pdf_q-a),
uses FAISS for a general-purpose "upload any PDF, ask about it" tool. This
project deliberately uses Qdrant instead, because the use case is different:
a fixed catalog of manuals that benefits from **metadata filtering**
(product, category) that a plain FAISS index doesn't give you out of the box.
Qdrant runs as its own service with a query API that supports filtering
alongside vector search, which is the main reason for the swap.

## Features

- Downloads and organizes manuals from Samsung's own support pages
- Chunks and embeds manual text, indexed into Qdrant with metadata
  (`product_name`, `category`, `manual_type`, `page_number`)
- Filtered semantic search — scope a query to one product or category
- Same chunking approach (`chunk_size=600`, `chunk_overlap=80`) proven out
  in the sibling `pdf_q-a` project

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env   # fill in only if using Qdrant Cloud — leave blank for local
```

Run Qdrant locally for development:

```bash
docker run -p 6333:6333 qdrant/qdrant
```

(Or use [Qdrant Cloud](https://cloud.qdrant.io) and set `QDRANT_URL` /
`QDRANT_API_KEY` in `.env`.)

## Step 1 — Download manuals

Edit `src/download_manuals.py`: replace the placeholder URLs in the
`MANUALS` list with real links from Samsung's support/downloads pages
(samsung.com → Support → search product → Manuals & Downloads → right-click
PDF → Copy Link Address).

Start with 5–10 manuals to validate the pipeline before scaling up.

```bash
cd src
python download_manuals.py
```

Saves PDFs into `manuals/` and writes `manuals/manifest.json`, tagging each
file with `product_name`, `category`, and `manual_type`.

> **Before doing this at scale:** check Samsung's site terms for scraping
> restrictions. Downloading a handful of manuals for a personal/educational
> project is a different footprint than mass-downloading their catalog.

## Step 2 — Ingest into Qdrant

```bash
python ingest_to_qdrant.py
```

Extracts text per PDF page, chunks it, embeds each chunk with
`all-MiniLM-L6-v2`, and upserts into the `samsung_manuals` Qdrant collection.

## Step 3 — Search

```bash
python search.py
```

Or from your own code:

```python
from search import search
results = search("how do I factory reset my phone", product_name="Galaxy S24")
```

Omit `product_name`/`category` to search across all indexed manuals.

## Known limitations

- Scanned/image-based manual pages won't extract text without OCR
  (flagged with a warning during ingestion)
- Table-heavy sections (spec sheets) may extract poorly, same limitation
  noted in `pdf_q-a`

## Next step

Wire retrieved chunks + the user's question into an LLM call (e.g. Groq) to
generate the final answer, then wrap it in a small Gradio UI for a live demo
— same pattern as `pdf_q-a`.

## Files

- `src/config.py` — chunking, embedding, and Qdrant settings
- `src/download_manuals.py` — fetches manuals, builds `manifest.json`
- `src/pdf_processing.py` — text extraction + chunking
- `src/ingest_to_qdrant.py` — embeds chunks, upserts into Qdrant
- `src/search.py` — filtered semantic search
