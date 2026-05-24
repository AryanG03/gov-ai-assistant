"""Chunker: splits large text into overlapping chunks."""
from config import CHUNK_SIZE, CHUNK_OVERLAP


def smart_chunk_text(text: str, chunk_size: int = CHUNK_SIZE) -> list[str]:
    paragraphs = text.split("\n\n")
    chunks, current = [], ""
    for para in paragraphs:
        if len(current) + len(para) + 2 <= chunk_size:
            current += para + "\n\n"
        else:
            if current.strip():
                chunks.append(current.strip())
            if len(para) > chunk_size:
                for i in range(0, len(para), chunk_size - CHUNK_OVERLAP):
                    chunks.append(para[i:i + chunk_size])
                current = ""
            else:
                current = para + "\n\n"
    if current.strip():
        chunks.append(current.strip())
    return chunks or [text]