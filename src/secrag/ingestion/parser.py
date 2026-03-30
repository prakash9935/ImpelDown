"""
PDF Parsing Module (US-101)

Uses pdfplumber to extract text from PDF documents,
splitting into chunks for embedding and storage in Qdrant.
"""

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import List

import pdfplumber

logger = logging.getLogger(__name__)


@dataclass
class Chunk:
    """Represents a chunk of parsed PDF content."""

    text: str
    source_file: str
    page_num: int
    chunk_index: int
    metadata: dict = field(default_factory=dict)


def parse_pdf(file_path: str, chunk_size: int = 512) -> List[Chunk]:
    """
    Parse a PDF file and return list of text chunks (US-101).

    Uses pdfplumber for fast text extraction from PDF files,
    then splits into chunks on token boundaries.

    Args:
        file_path: Path to PDF file
        chunk_size: Token boundary for chunking (default 512)

    Returns:
        List of Chunk objects with page_num, chunk_index, text

    Raises:
        FileNotFoundError: If PDF file doesn't exist
        ValueError: If PDF parsing fails
    """
    file_path = Path(file_path)

    if not file_path.exists():
        raise FileNotFoundError(f"PDF file not found: {file_path}")

    if not file_path.suffix.lower() == ".pdf":
        raise ValueError(f"File must be PDF: {file_path}")

    logger.info(f"Parsing PDF: {file_path}")

    try:
        chunks = []
        chunk_index = 0

        # Use pdfplumber to extract text from each page
        with pdfplumber.open(file_path) as pdf:
            for page_num, page in enumerate(pdf.pages, start=1):
                # Extract text from page
                page_text = page.extract_text()

                if not page_text or not page_text.strip():
                    logger.debug(f"No text on page {page_num}")
                    continue

                # Split page text into chunks
                # Simple token-based chunking (rough estimation: ~4 chars per token)
                tokens_per_chunk = chunk_size

                lines = page_text.split("\n")
                current_chunk_text = ""
                current_chunk_tokens = 0

                for line in lines:
                    line_tokens = len(line.split()) + 1  # Approximate token count

                    if (
                        current_chunk_tokens + line_tokens > tokens_per_chunk
                        and current_chunk_text.strip()
                    ):
                        # Save current chunk
                        chunks.append(
                            Chunk(
                                text=current_chunk_text.strip(),
                                source_file=file_path.name,
                                page_num=page_num,
                                chunk_index=chunk_index,
                            )
                        )
                        chunk_index += 1
                        current_chunk_text = ""
                        current_chunk_tokens = 0

                    current_chunk_text += line + "\n"
                    current_chunk_tokens += line_tokens

                # Add final chunk from page if non-empty
                if current_chunk_text.strip():
                    chunks.append(
                        Chunk(
                            text=current_chunk_text.strip(),
                            source_file=file_path.name,
                            page_num=page_num,
                            chunk_index=chunk_index,
                        )
                    )
                    chunk_index += 1

        if not chunks:
            logger.warning(f"No text extracted from {file_path.name}")
            return []

        logger.info(f"Parsed {len(chunks)} chunks from {file_path.name}")
        return chunks

    except Exception as e:
        logger.error(f"Failed to parse PDF {file_path}: {str(e)}")
        raise ValueError(f"PDF parsing failed: {str(e)}")
