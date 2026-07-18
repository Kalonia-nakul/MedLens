# Patient RAG Advisor

A local FastAPI service that lets a patient upload a document (lab report,
discharge summary, prescription notes, etc.), indexes it with a local vector
database, and answers questions about it using a locally-running **Ollama**
model — grounded only in what's in the uploaded document.

> ⚠️ **This is an informational tool, not a medical device.** It does not
> diagnose, prescribe, or replace a licensed clinician. Every answer includes
> a disclaimer and the model is instructed to recommend professional care,
> especially for anything urgent. Do not deploy this for real patient use
> without a clinician review process, proper consent language, and
> compliance with your local health-data regulations (e.g. HIPAA, GDPR).

## How it works

1. **Upload** (`POST /upload`) — a PDF/TXT/MD/DOCX file is parsed, split into
   overlapping text chunks, embedded with an Ollama embedding model
   (`nomic-embed-text` by default), and stored in a per-patient collection in
   a local [ChromaDB](https://www.trychroma.com/) database (`chroma_db/`).
2. **Ask** (`POST /ask`) — your question is embedded, the most relevant chunks
   from that patient's document are retrieved, and both are sent to an Ollama
   chat model (`llama3.1` by default) with a system prompt that restricts it
   to the retrieved context and pushes it to recommend professional care
   where relevant.
3. **Delete** (`DELETE /patient/{patient_id}`) — wipes a patient's indexed
   data.

## Prerequisites

- Python 3.10+
- [Ollama](https://ollama.com/) installed and running locally
- Pull the models you'll use:
  ```bash
  ollama pull llama3.1
  ollama pull nomic-embed-text
  ```

## Setup

```bash
cd patient-rag-advisor
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env            # adjust model names if you like
```

Make sure Ollama is running (`ollama serve`, or it's already running as a
background service), then start the API:

```bash
uvicorn main:app --reload
```

The API is now at `http://localhost:8000`, with interactive docs at
`http://localhost:8000/docs`.

## Usage

### 1. Upload a document

```bash
curl -X POST http://localhost:8000/upload \
  -F "file=@/path/to/lab_report.pdf" \
  -F "patient_id=patient_001"
```

Response:
```json
{
  "patient_id": "patient_001",
  "filename": "lab_report.pdf",
  "chunks_indexed": 6,
  "message": "Document indexed. You can now ask questions using this patient_id."
}
```

(If you omit `patient_id`, one is generated for you and returned — save it.)

### 2. Ask a question

```bash
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{
    "patient_id": "patient_001",
    "question": "What does my cholesterol result mean and should I be worried?"
  }'
```

Response:
```json
{
  "answer": "Based on your uploaded report, your LDL cholesterol is listed as ...",
  "sources": ["lab_report.pdf"],
  "disclaimer": "This is general information based only on the document you provided, ..."
}
```

### 3. Delete a patient's data

```bash
curl -X DELETE http://localhost:8000/patient/patient_001
```

## Configuration

All via environment variables (see `.env.example`):

| Variable            | Default                   | Description                          |
|---------------------|----------------------------|---------------------------------------|
| `OLLAMA_BASE_URL`   | `http://localhost:11434`  | Ollama server URL                     |
| `OLLAMA_LLM_MODEL`  | `llama3.1`                | Chat/generation model                 |
| `OLLAMA_EMBED_MODEL`| `nomic-embed-text`        | Embedding model                       |
| `CHROMA_DIR`        | `chroma_db`                | Local path for the vector database    |

## Project structure

```
patient-rag-advisor/
├── main.py          # FastAPI app & routes
├── rag_engine.py     # File parsing, chunking, embeddings, retrieval, generation
├── requirements.txt
├── .env.example
├── uploads/          # raw uploaded files (created at runtime)
└── chroma_db/        # persisted vector store (created at runtime)
```

## Extending this

- **Swap vector stores**: replace the ChromaDB calls in `rag_engine.py` with
  FAISS, Qdrant, or pgvector if you outgrow local storage.
- **Streaming answers**: set `"stream": True` in the `/api/chat` call and
  proxy the stream back through a FastAPI `StreamingResponse`.
- **Auth**: add an auth dependency (e.g. API key or JWT) to `/upload`,
  `/ask`, and `/patient/{id}` before exposing this beyond localhost.
- **Structured extraction**: for lab reports, consider a preprocessing step
  that pulls out (test name, value, reference range) triples so the model
  reasons over structured data rather than raw text.
- **Better chunking**: swap the naive sliding-window chunker for a
  sentence/paragraph-aware splitter (e.g. `langchain`'s
  `RecursiveCharacterTextSplitter`) if answer quality on long documents needs
  improvement.

## Safety notes

- The system prompt in `rag_engine.py` (`SYSTEM_PROMPT`) is the main lever
  for keeping answers cautious — read and adjust it before any real-world
  use. It currently instructs the model to avoid diagnosing, avoid
  prescribing/adjusting medication, and to flag urgent-sounding content for
  prompt medical attention.
- Everything runs locally by default (Ollama + ChromaDB on disk) — no patient
  data leaves the machine unless you change `OLLAMA_BASE_URL` to a remote
  server.
- Add real authentication and encryption at rest before handling actual
  patient data.
