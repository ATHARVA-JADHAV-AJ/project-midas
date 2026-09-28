# Project Midas — Document Ingestor (Docling + Qdrant)
# Author: Atharva Kishor Jadhav (AJ)
# ---------------------------------------------------------------
"""
Ingests PDF documents into the Qdrant knowledge base.

Pipeline:
  1. Docling parses the PDF with layout awareness (preserves table structure,
     headings, and reading order across multi-column layouts)
  2. The extracted text is split into overlapping chunks
  3. Each chunk is embedded using nomic-embed-text (CPU-only)
  4. Chunks + vectors are upserted into the Qdrant collection

Usage (CLI):
    python -m memory.ingestor --file path/to/document.pdf
"""

import os
import logging
import argparse
from pathlib import Path
from typing import List

from memory.embedder import embed_batch
from memory.vector_store import ensure_collection, upsert_chunks
from memory.sanitizer import sanitize_text

logger = logging.getLogger(__name__)

CHUNK_SIZE = int(os.getenv("INGEST_CHUNK_SIZE", "512"))   # characters per chunk
CHUNK_OVERLAP = int(os.getenv("INGEST_CHUNK_OVERLAP", "64"))  # character overlap between chunks


def _chunk_text(text: str, size: int, overlap: int) -> List[str]:
    """
    Split text into overlapping windows of `size` characters.
    Overlap ensures context at chunk boundaries isn't lost.
    """
    chunks = []
    start = 0
    while start < len(text):
        end = min(start + size, len(text))
        chunks.append(text[start:end].strip())
        start += size - overlap
    return [c for c in chunks if c]  # Drop any empty chunks


def ingest_pdf(pdf_path: str) -> int:
    """
    Parse a PDF with Docling, chunk the text, embed it, and store in Qdrant.
    Returns the number of chunks indexed.
    """
    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    logger.info(f"Ingesting: {pdf_path.name}")

    # Docling import is deferred so the server starts cleanly even if Docling
    # is not yet installed (ingestor is a CLI tool, not a hot path)
    try:
        from docling.document_converter import DocumentConverter
    except ImportError:
        raise RuntimeError(
            "Docling not installed. Run: pip install docling"
        )

    converter = DocumentConverter()
    result = converter.convert(str(pdf_path))
    # Export to plain text — Docling preserves reading order across columns/tables
    full_text = result.document.export_to_text()

    if not full_text.strip():
        logger.warning(f"Docling returned empty text for {pdf_path.name}")
        return 0

    # Sanitize for prompt injection patterns before chunking
    full_text, flagged = sanitize_text(full_text, source_name=pdf_path.name)
    if flagged:
        logger.warning(f"Sanitized {len(flagged)} potential injection(s) from {pdf_path.name}")

    chunks = _chunk_text(full_text, CHUNK_SIZE, CHUNK_OVERLAP)
    logger.info(f"Split into {len(chunks)} chunks (size={CHUNK_SIZE}, overlap={CHUNK_OVERLAP})")

    vectors = embed_batch(chunks)
    doc_metadata = [{"source": pdf_path.name, "chunk_index": i} for i in range(len(chunks))]

    ensure_collection()
    count = upsert_chunks(chunks, vectors, metadata=doc_metadata)
    logger.info(f"Indexed {count} chunks from {pdf_path.name}")
    return count


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
    parser = argparse.ArgumentParser(description="Ingest a PDF into the Midas knowledge base")
    parser.add_argument("--file", required=True, help="Path to the PDF file")
    args = parser.parse_args()
    total = ingest_pdf(args.file)
    print(f"Done. {total} chunks indexed.")
