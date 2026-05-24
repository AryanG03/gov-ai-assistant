"""PDF Reader: extracts text from PDF files using PyMuPDF."""
import fitz
import os


def extract_text_from_pdf(pdf_path: str) -> str:
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"PDF not found: {pdf_path}")
    doc   = fitz.open(pdf_path)
    pages = []
    for i, page in enumerate(doc, 1):
        text = page.get_text("text").strip()
        if text:
            pages.append(f"[PAGE {i}]\n{text}")
    doc.close()
    if not pages:
        raise ValueError(f"No text extracted from {pdf_path}. May be a scanned PDF.")
    return "\n\n".join(pages)


def get_pdf_metadata(pdf_path: str) -> dict:
    doc  = fitz.open(pdf_path)
    meta = doc.metadata or {}
    result = {
        "title":  meta.get("title", "Unknown"),
        "author": meta.get("author", "Unknown"),
        "pages":  doc.page_count,
    }
    doc.close()
    return result