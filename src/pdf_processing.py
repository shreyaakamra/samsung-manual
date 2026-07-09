"""
pdf_processing.py

Extracts text from PDFs page-by-page (so we can keep page_number metadata)
and splits it into overlapping chunks for embedding.
"""

from dataclasses import dataclass
from pypdf import PdfReader

from config import CHUNK_SIZE, CHUNK_OVERLAP


@dataclass
class Chunk:
    text: str
    page_number: int


def extract_pages(pdf_path: str) -> list[tuple[int, str]]:
    """Returns list of (page_number, page_text) tuples. Flags scanned/empty pages."""
    reader = PdfReader(pdf_path)
    pages = []
    for i, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        if not text.strip():
            print(f"    [warn] page {i} of {pdf_path} has no extractable text "
                  f"(likely scanned/image-based — consider OCR)")
        pages.append((i, text))
    return pages


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """Simple sliding-window character chunking with overlap."""
    if not text.strip():
        return []

    chunks = []
    start = 0
    text_len = len(text)
    while start < text_len:
        end = min(start + chunk_size, text_len)
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end == text_len:
            break
        start = end - overlap
    return chunks


def process_pdf(pdf_path: str) -> list[Chunk]:
    """Extracts and chunks a PDF, preserving page number per chunk."""
    pages = extract_pages(pdf_path)
    all_chunks = []
    for page_number, page_text in pages:
        for chunk in chunk_text(page_text):
            all_chunks.append(Chunk(text=chunk, page_number=page_number))
    return all_chunks
