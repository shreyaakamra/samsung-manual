# Repair Manual RAG (MyFixit)

A Retrieval-Augmented Generation (RAG) pipeline over the [MyFixit dataset](https://github.com/rub-ksv/MyFixit-Dataset)
— 31,601 repair manuals across 15 device categories, collected from
[iFixit](https://www.ifixit.com). Indexed into Qdrant with per-guide
metadata (category, subject, guide title) so questions can be scoped to a
specific device category (e.g. "Phone" only) instead of searching everything.

## Why this pivot

An earlier version of this project scraped Samsung manuals directly as
PDFs. This dataset is a better fit for a few reasons:

- **Already structured** — each manual is JSON with steps pre-segmented,
  so there's no PDF text-extraction step (no scanned pages, no broken
  table extraction, no OCR needed).
- **Metadata included** — `Category`, `Subject`, and `Title` map directly
  onto the filtering fields the pipeline needs, instead of being
  hand-typed per manual.
- **Clearly licensed for this use** — released for research/dataset use;
  cite the paper below if you use it.

Framing note: this is **repair guidance** (how to disassemble/fix a
device), not general **user manual** content (how to use its features).
"How do I replace my phone's battery" is a great support-bot query for
this dataset; "how do I turn on dark mode" is not — that's the kind of
question the original PDF-manual approach was built for.

## Setup

```bash
pip install -r requirements.txt
```

Run Qdrant locally:

```bash
docker run -p 6333:6333 qdrant/qdrant
```

## Step 1 — Download category data

Edit `config.py` and set `MYFIXIT_CATEGORIES` to whichever categories you
want (options: `Mac`, `Car and Truck`, `Household`, `Computer Hardware`,
`Appliance`, `Camera`, `PC`, `Electronics`, `Phone`, `Game Console`,
`Skills`, `Vehicle`, `Media Player`, `Apparel`, `Tablet`). Start with 1-2
small categories to validate the pipeline.

```bash
python download_myfixit.py
```

Downloads the category JSON files directly from the dataset's GitHub repo
into `data/myfixit_jsons/`.

## Step 2 — Ingest into Qdrant

```bash
python ingest_myfixit_to_qdrant.py
```

Parses each manual's steps (each step's `Text_raw` is already a natural
chunk — no character-based chunking needed), embeds with
`all-MiniLM-L6-v2`, and upserts into the `myfixit_manuals` Qdrant
collection with metadata attached.

## Step 3 — Search

```bash
python search.py
```

Or from your own code:

```python
from search import search
results = search("how do I replace the battery", category="Phone")
```

## Data format note

Each category file in the dataset is **JSON-lines** (one JSON object per
line), not a single JSON array — `myfixit_processing.py` reads it that way.

## Next step

Wire retrieved chunks + the user's question into an LLM call (Groq) to
generate the final answer.

## Citation

If you use this dataset, cite the original paper:

```
Nabizadeh, N., Kolossa, D., & Heckmann, M. (2020). MyFixit: An Annotated
Dataset, Annotation Tool, and Baseline Methods for Information Extraction
from Repair Manuals. Proceedings of The 12th Language Resources and
Evaluation Conference (LREC 2020), 2120-2128.
```

## Files

- `config.py` — embedding, Qdrant, and category settings
- `download_myfixit.py` — fetches category JSON files from GitHub
- `myfixit_processing.py` — parses JSON-lines manuals into step-level chunks
- `ingest_myfixit_to_qdrant.py` — embeds chunks, upserts into Qdrant
- `search.py` — filtered semantic search