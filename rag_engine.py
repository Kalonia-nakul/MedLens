"""
Core RAG logic: file parsing, chunking, embedding (via Ollama), vector
storage (via ChromaDB, persisted locally), retrieval, and answer generation
(via Ollama chat model).
"""

import re
from pathlib import Path
from typing import List, Dict

import chromadb
import requests


# ---------------------------------------------------------------------------
# File parsing
# ---------------------------------------------------------------------------
def _read_txt(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def _read_pdf(path: Path) -> str:
    from pypdf import PdfReader

    reader = PdfReader(str(path))
    text_parts = []
    for page in reader.pages:
        text_parts.append(page.extract_text() or "")
    return "\n".join(text_parts)


def _read_docx(path: Path) -> str:
    import docx

    doc = docx.Document(str(path))
    return "\n".join(p.text for p in doc.paragraphs)


def extract_text(path: Path) -> str:
    ext = path.suffix.lower()
    if ext == ".pdf":
        return _read_pdf(path)
    if ext == ".docx":
        return _read_docx(path)
    return _read_txt(path)  # .txt, .md, fallback


# ---------------------------------------------------------------------------
# Chunking
# ---------------------------------------------------------------------------
def chunk_text(text: str, chunk_size: int = 800, overlap: int = 150) -> List[str]:
    """Simple sliding-window chunker on whitespace-normalized text."""
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return []

    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start += chunk_size - overlap
    return chunks


# ---------------------------------------------------------------------------
# Ollama client helpers
# ---------------------------------------------------------------------------
class OllamaClient:
    def __init__(self, base_url: str, llm_model: str, embed_model: str):
        self.base_url = base_url.rstrip("/")
        self.llm_model = llm_model
        self.embed_model = embed_model

    def embed(self, text: str) -> List[float]:
        resp = requests.post(
            f"{self.base_url}/api/embeddings",
            json={"model": self.embed_model, "prompt": text},
            timeout=60,
        )
        resp.raise_for_status()
        return resp.json()["embedding"]

    def chat(self, system_prompt: str, user_prompt: str) -> str:
        resp = requests.post(
            f"{self.base_url}/api/chat",
            json={
                "model": self.llm_model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "stream": False,
                "options": {"temperature": 0.2},
            },
            timeout=120,
        )
        resp.raise_for_status()
        return resp.json()["message"]["content"]


# ---------------------------------------------------------------------------
# RAG Engine
# ---------------------------------------------------------------------------
SYSTEM_PROMPT = """You are a cautious clinical-information assistant helping a \
patient understand their own uploaded document (e.g. lab results, discharge \
notes, prescription details).

Rules you must follow:
1. Answer ONLY using the CONTEXT provided below. If the answer is not in the \
context, say you don't have enough information in the uploaded document, and \
suggest the patient ask their doctor or pharmacist directly.
2. You may explain what values or terms in the document generally mean, and \
suggest sensible, low-risk next steps (e.g. "consider scheduling a follow-up", \
"discuss this result with your doctor", "this is generally recommended, but \
confirm with your care team").
3. Do NOT provide a definitive diagnosis. Do NOT prescribe or adjust medication \
dosages. Do NOT tell the patient to stop or start a specific treatment on your \
own authority.
4. If anything in the context suggests a potentially urgent or severe issue, \
clearly recommend prompt medical attention (e.g. calling their doctor today, or \
emergency care if symptoms are severe).
5. Be clear, warm, and plain-spoken. Avoid unnecessary jargon; briefly explain \
any medical terms you use.
6. Always keep in mind you are a supplementary information tool, not a \
replacement for a licensed medical professional.
"""


class RAGEngine:
    def __init__(self, ollama_base_url: str, llm_model: str, embed_model: str, chroma_dir: str):
        self.client = OllamaClient(ollama_base_url, llm_model, embed_model)
        self.chroma = chromadb.PersistentClient(path=chroma_dir)

    def _collection(self, patient_id: str):
        # One collection per patient keeps documents isolated between patients.
        name = f"patient_{patient_id}"
        return self.chroma.get_or_create_collection(name=name)

    def ingest_file(self, path: Path, patient_id: str) -> int:
        text = extract_text(path)
        chunks = chunk_text(text)
        if not chunks:
            raise ValueError("No extractable text found in the uploaded file.")

        collection = self._collection(patient_id)
        embeddings = [self.client.embed(c) for c in chunks]
        ids = [f"{path.stem}_{i}" for i in range(len(chunks))]

        collection.add(
            ids=ids,
            documents=chunks,
            embeddings=embeddings,
            metadatas=[{"source": path.name} for _ in chunks],
        )
        return len(chunks)

    def has_documents(self, patient_id: str) -> bool:
        collection = self._collection(patient_id)
        return collection.count() > 0

    def answer_question(self, patient_id: str, question: str, top_k: int = 4) -> Dict:
        collection = self._collection(patient_id)
        query_embedding = self.client.embed(question)

        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=min(top_k, max(collection.count(), 1)),
        )

        retrieved_docs = results["documents"][0] if results["documents"] else []
        sources = [m.get("source", "unknown") for m in results.get("metadatas", [[]])[0]]

        context = "\n\n---\n\n".join(retrieved_docs) if retrieved_docs else "(no relevant context found)"

        user_prompt = f"CONTEXT:\n{context}\n\nPATIENT QUESTION:\n{question}"
        answer = self.client.chat(SYSTEM_PROMPT, user_prompt)

        return {"answer": answer, "sources": sorted(set(sources))}

    def delete_patient(self, patient_id: str) -> bool:
        name = f"patient_{patient_id}"
        try:
            self.chroma.delete_collection(name=name)
            return True
        except Exception:
            return False
