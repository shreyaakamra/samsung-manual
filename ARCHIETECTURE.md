# Architecture & Design Decisions

This document explains what this project does, why each technical choice
was made, and the reasoning behind the pivots that shaped it. Written to
be a reference for explaining the project — to an interviewer, or to
future-me revisiting this code.

## The problem

A customer asks a support question about a product ("how do I replace my
phone's battery?"). An LLM answering purely from its training data can
hallucinate or give generic advice that doesn't match the actual device.
**Retrieval-Augmented Generation (RAG)** fixes this: retrieve the actual
relevant text from a real knowledge base first, then give that text to the
LLM as grounding context before it answers.

This project builds the **retrieval** half of that pipeline: ingest repair
manuals into a searchable, filterable vector database.

## Project history — the decisions that shaped this

This wasn't built in a straight line, and the pivots are part of the story:

1. **Started with FAISS + PDFs** (`pdf_q-a` project) — general "upload any
   PDF, ask about it" tool. Worked, but two limitations: no metadata
   filtering (FAISS only stores vectors, not structured attributes), and
   PDF text extraction was fragile — scanned pages, broken tables.
2. **Tried scraping Samsung's own product manuals** for a more realistic
   "one company's catalog" use case. Hit real-world constraints: manual
   URLs had to be sourced one by one, PDF extraction issues persisted,
   and licensing/ToS questions matter at scale for scraped content.
3. **Pivoted to the MyFixit dataset** — a structured, pre-segmented,
   properly licensed collection of repair guides. This resolved both
   problems and gave a genuine reason to introduce Qdrant's metadata
   filtering as a real improvement, not just a swap for its own sake.

## Why Qdrant instead of FAISS

This is the most defensible technical decision in the project, worth
being able to explain precisely:

**FAISS** is a library, not a database — it stores vectors and does
similarity search, full stop. It has no concept of "this vector belongs to
category Phone." Filtering by an attribute means building and maintaining
a separate lookup system yourself.

**Qdrant** is a vector database — vectors are stored *with* arbitrary
metadata (payload) attached, and a single query can combine similarity
search *and* metadata filtering (e.g. "find the closest matches, but only
among Phone-category chunks"). Since this project's core requirement is
scoping retrieval to a specific device/category, that combined
filter+search capability is the actual reason for the choice — not
novelty for its own sake.

## Why the MyFixit dataset instead of chunking raw PDFs

In the PDF-based version, chunk boundaries had to be invented
(`chunk_size=600, chunk_overlap=80`) because raw extracted PDF text has no
natural structure — chunking is a guess at where one unit of meaning ends
and another begins. Overlap exists specifically to avoid cutting a
sentence in half at a chunk boundary.

MyFixit's data is pre-segmented: each repair guide is broken into `Steps`,
and each step's `Text_raw` is already a complete, coherent instruction.
Using one step = one chunk avoids two failure modes: chunks too small to
contain a full instruction, and chunks large enough to dilute the
embedding with irrelevant surrounding text. This is a data-quality choice,
not a shortcut — recognizing that the source data already had the
boundaries a chunking algorithm would otherwise have to approximate.

## Why metadata lives alongside every chunk

Each indexed point carries `category`, `subject`, `guide_title`, and
`step_order` alongside its vector. This is what makes scoped queries
possible: "how do I replace the battery" filtered to `category="Phone"`
returns different, more relevant results than the same query searched
across every device category at once. Without this metadata, retrieval
quality degrades as the dataset grows — more categories means more
irrelevant near-matches competing for the same top-k results.

## What an embedding actually is

A sentence-transformer model (`all-MiniLM-L6-v2`) converts text into a
384-number vector such that texts with similar *meaning* — not just
matching keywords — end up numerically close in that 384-dimensional
space. This is what enables semantic search: a query for "phone won't
turn on" can match a chunk saying "device is unresponsive" even though
they share almost no words.

**Important consistency requirement:** the same embedding model must be
used for both indexing (documents) and querying (the user's question).
Mismatched models produce vectors in different spaces — similarity scores
between them are meaningless.

## Why downloading and indexing are separate steps

`download_myfixit.py` and `ingest_myfixit_to_qdrant.py` are deliberately
separate, run-once/offline steps. This mirrors a general RAG architecture
principle: **indexing is a batch process, retrieval is a real-time
process.** Users querying the system need fast responses; building the
index can take as long as it needs to, since it happens ahead of time and
only needs to be redone when the underlying data changes.

## Why batching during embedding

```python
batch_size = 256
for i in range(0, len(chunks), batch_size):
    ...
```

Embedding tens of thousands of chunks in a single call risks memory
pressure and gives no visibility into partial progress if something fails
midway. Batching keeps memory bounded and makes failures recoverable —
you know exactly which batch succeeded last.

## Known limitations / honest gaps

Worth naming these proactively rather than waiting to be asked:

- **No LLM generation step yet.** Retrieval works and returns relevant
  chunks, but nothing yet turns those chunks + the question into a
  natural-language answer. Next planned step: wire in Groq, same as the
  `pdf_q-a` project.
- **No formal retrieval evaluation.** Results look reasonable on manual
  spot-checks, but there's no metric (e.g. retrieval@k against a labeled
  test set) confirming retrieval quality systematically.
- **Pure vector search, no hybrid search.** Semantic embeddings handle
  synonyms well but can miss exact-term matches that keyword search would
  catch (e.g. a specific model number). A production system might combine
  vector search with keyword/BM25 search.
- **Not yet tested at scale.** Validated against a few hundred to a few
  thousand chunks; behavior with the full ~30K-manual dataset across all
  15 categories hasn't been measured.


