"""Extracts plain text from uploaded patient report files."""

from __future__ import annotations

import io

from pypdf import PdfReader


def extract_text(uploaded_file) -> str:
    """Extracts text from a Streamlit UploadedFile (.pdf, .txt, or .md)."""
    name = uploaded_file.name.lower()

    if name.endswith(".pdf"):
        return _extract_pdf(uploaded_file)
    if name.endswith(".txt") or name.endswith(".md"):
        return uploaded_file.read().decode("utf-8", errors="ignore")

    raise ValueError(
        f"Unsupported file type: {uploaded_file.name}. "
        "Please upload a .pdf or .txt file, or paste the text instead."
    )


def _extract_pdf(uploaded_file) -> str:
    reader = PdfReader(io.BytesIO(uploaded_file.read()))
    pages = [page.extract_text() or "" for page in reader.pages]
    full_text = "\n".join(pages).strip()

    if not full_text:
        raise ValueError(
            "Couldn't extract any text from this PDF - it may be a scanned "
            "image without a text layer. Try pasting the report text "
            "manually in the 'Paste text' tab instead."
        )
    return full_text
