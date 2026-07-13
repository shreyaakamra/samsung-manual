# Repair Manual RAG (MyFixit)

A Retrieval-Augmented Generation pipeline that lets users ask natural-language repair questions ("how do I replace my phone's battery?") and get back the relevant repair steps, filtered to the correct device category, sourced from real iFixit repair guides.

---

## 1. Problem Statement

Repair manuals for consumer electronics are scattered, unstructured, and hard to search. A user with a broken device typically has to:

- Search the web and land on multiple conflicting guides
- Wade through a full PDF or web page to find the two steps that matter
- Manually filter out irrelevant results (e.g. car repair steps showing up next to phone repair steps, because "battery" and "screen" are generic terms across product categories)

A first version of this project tried to solve this by scraping Samsung PDF manuals directly. That approach ran into the usual problems with unstructured source data: scanned/image-only pages with no extractable text, broken table extraction, and no consistent metadata to filter on.

**The problem this project solves:** given a natural-language repair question, retrieve the specific, correct repair steps — scoped to the right device category — without requiring the user to manually sift through an entire manual or a mix of irrelevant categories.

---

## 2. Project Description

This project pivoted away from PDF scraping to the [MyFixit Dataset](https://github.com/rub-ksv/MyFixit-Dataset): 31,601 repair guides across 15 device categories, collected from [iFixit](https://www.ifixit.com), released for research use with pre-segmented steps and structured metadata.

**Why the pivot made sense:**

| | PDF scraping (v1) | MyFixit dataset (v2, this repo) |
|---|---|---|
| Text extraction | Manual, breaks on scanned pages | Not needed — steps are already segmented JSON fields |
| Chunking | Character-based sliding window, chunk boundaries can split a step mid-sentence | Not needed — each step is already a natural chunk |
| Metadata | Hand-typed per manual | `Category`, `Subject`, `Title` ship with the dataset |
| Licensing | Scraping ToS ambiguity | Clearly licensed for research/dataset use |

**Important framing distinction:** this is a **repair guidance** system ("how do I disassemble/fix X"), not a **user manual** system ("how do I turn on dark mode"). The MyFixit dataset only covers the former — the latter is what the original PDF-manual project was aimed at, and that distinction is worth being explicit about if asked in an interview why two related-but-different projects exist.

---

## 3. Technical Architecture

```
MyFixit-Dataset (GitHub, per-category JSON-lines)
        │
        ▼
 download_myfixit.py  ──► data/myfixit_jsons/<Category>.json
        │
        ▼
 myfixit_processing.py  ──► parses each guide's steps into Chunk objects
        │                    (Category, Subject, Title, step_order, url, step text)
        ▼
 ingest_myfixit_to_qdrant.py
        │  - embeds each step's text with all-MiniLM-L6-v2 (384-dim)
        │  - batches embeddings (batch_size=256) to bound memory/request size
        ▼
   Qdrant collection (cosine similarity)
        │  payload per point: text, guide_title, guide_id, category,
        │  subject, step_order, step_id, url
        ▼
 search.py  ──► embeds the query, applies optional category/subject
                filter (Qdrant FieldCondition/MatchValue), returns top-k
        │
        ▼
   [NOT YET BUILT] Generation step — wire retrieved chunks + question
   into a Groq LLM call to produce a final natural-language answer
```

**Component choices and the reasoning behind them:**

- **Embedding model — `all-MiniLM-L6-v2`:** carried over from the earlier `pdf_q-a` project. Small (384-dim), fast on CPU, good enough recall for a portfolio-scale corpus without needing GPU inference.
- **Vector DB — Qdrant:** supports payload-based filtering natively (`category`, `subject`), which is the core UX requirement here — scoping search to one device category instead of searching everything. Chosen over FAISS (used in the earlier `pdf_q-a` project) specifically because FAISS doesn't do structured metadata filtering as a first-class feature.
- **No chunking step:** unlike the PDF pipeline (`chunk_size=600`, `chunk_overlap=80`), each MyFixit step's `Text_raw` field is already a coherent, appropriately-sized unit — so introducing a sliding-window chunker here would just re-fragment already-good data.
- **Retrieval, not yet generation:** the repo currently implements retrieval only. `search.py` returns ranked, filtered chunks with their source guide and URL. The README's own "Next step" section calls out that wiring these into a Groq call for answer synthesis hasn't been done yet.

---

## 4. Success Criteria — and how it's actually being measured today

Because generation isn't wired up yet, "success" for the current state of this repo is a **retrieval-quality question**, not an end-to-end answer-quality question. Framed honestly:

| Criterion | What it means | Current measurement status |
|---|---|---|
| **Category filtering works** | Querying with `category="Phone"` never returns `Car and Truck` results | Verified manually via `search.py`'s `__main__` example (`"how do I replace the battery", category="Phone"`) — no automated test suite yet |
| **Retrieved steps are topically relevant** | Top-k results are steps that plausibly answer the query | Eyeballed via printed `score`, `guide_title`, and step text snippet — no held-out relevance-labeled eval set yet |
| **Source traceability** | Every retrieved chunk can be traced back to its original guide | Yes by construction — `url`, `guide_id`, and `step_order` are stored in the Qdrant payload and printed with every result |
| **Ingestion completeness** | All steps in a downloaded category file make it into Qdrant | Logged via chunk counts printed per category and per batch during ingestion — not cross-checked against source file line counts |
| **End-to-end answer quality** | A generated answer is grounded in retrieved steps and actually answers the question | **Not measurable yet** — generation step doesn't exist in this repo |

**Honest summary:** success so far = "does filtered semantic search return the right guide for a manually-tried query." That's a reasonable checkpoint for a retrieval layer, but it isn't a rigorous evaluation (no labeled query set, no precision/recall numbers, no automated regression tests). If asked in an interview "how did you measure success," the accurate answer is *manual spot-checking of retrieval results*, not a formal eval harness — worth saying plainly rather than overstating it.

---

## 5. Limitations

- **No generation layer.** The pipeline stops at retrieval. There is no LLM call that turns retrieved steps into a natural-language answer yet — this is the explicit "Next step" in the original README.
- **No automated evaluation.** No labeled query/answer set, no precision@k or recall@k numbers, no regression tests for retrieval quality. Success is currently assessed by manually reading printed results.
- **Known code inconsistencies (as of the current `main` branch):**
  - `download_myfixit.py` imports `MYFIXIT_CATEGORIES`, `MYFIXIT_BASE_URL`, and `MYFIXIT_JSONS_DIR` from `config.py`, but `config.py` doesn't currently define them — running the script as-is will raise an `ImportError`.
  - `ingest_myfixit_to_qdrant.py` imports `process_category_file` from `myfixit_processing.py`, but that file still contains the old PDF-chunking functions (`extract_pages`, `chunk_text`, `process_pdf`) from the earlier Samsung-PDF version, not a `process_category_file` function. This looks like an in-progress refactor that wasn't fully pushed.
- **Legacy naming.** The Qdrant collection is still named `samsung_manuals` in `config.py`, left over from before the pivot to the MyFixit dataset — cosmetic, but worth cleaning up so the code matches the current data source.
- **No reranking.** Retrieval is single-stage cosine similarity over bi-encoder embeddings — no cross-encoder reranking pass to improve precision on ambiguous queries.
- **Partial dataset coverage by design.** Only categories explicitly listed in `MYFIXIT_CATEGORIES` get downloaded and indexed — the system doesn't index all 31,601 guides unless every category is added, which is a reasonable dev-time choice but means "coverage" is whatever's been configured, not the full dataset.
- **No deployment/serving layer.** This is a set of pipeline scripts run from the command line (`download_myfixit.py` → `ingest_myfixit_to_qdrant.py` → `search.py`), not a deployed app with a UI — unlike the `pdf_q-a` project, which was deployed to Hugging Face Spaces with a Gradio front end.
- **No API key / cost guardrails yet** for the planned Groq generation step, since that step doesn't exist in the repo yet.

---

## 6. Setup

```bash
pip install -r requirements.txt
docker run -p 6333:6333 qdrant/qdrant   # run Qdrant locally
```

1. Edit `config.py` — set `MYFIXIT_CATEGORIES` to the categories you want (`Phone`, `Appliance`, `Computer Hardware`, etc. — start with 1-2 small ones to validate the pipeline).
2. `python download_myfixit.py` — pulls category JSON files into `data/myfixit_jsons/`.
3. `python ingest_myfixit_to_qdrant.py` — embeds and upserts steps into Qdrant.
4. `python search.py` — run a filtered semantic search, or import `search()` directly.

## Citation

```
Nabizadeh, N., Kolossa, D., & Heckmann, M. (2020). MyFixit: An Annotated
Dataset, Annotation Tool, and Baseline Methods for Information Extraction
from Repair Manuals. Proceedings of The 12th Language Resources and
Evaluation Conference (LREC 2020), 2120-2128.
```
