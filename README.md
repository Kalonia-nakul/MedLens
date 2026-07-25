# MedLens

MedLens is a local, private AI agent that reads a patient's medical report
(lab results, imaging notes, discharge summaries, etc.) and gives back a
plain-language, structured "first read": a summary, key findings, risk
flags, forward-looking things to watch ("foresight"), questions to bring to
your doctor, and general lifestyle notes.

Everything runs locally through [Ollama](https://ollama.com) - no report
text is sent to any external API.

**MedLens does not diagnose.** It's a reading aid to help you prepare for a
conversation with a real clinician. See the disclaimer shown in the app.

## Project structure

```
medlens/
├── app.py                      # Streamlit UI entry point
├── medlens/
│   ├── __init__.py
│   ├── config.py                # Ollama host + model choices
│   ├── prompts.py                # System prompt + JSON schema for output
│   ├── report_parser.py         # Extracts text from PDF/TXT uploads
│   └── ollama_client.py         # Calls the local Ollama server, parses JSON
├── sample_reports/
│   └── sample_report.txt        # Fictional report for testing
├── requirements.txt
└── README.md
```

## Setup

1. **Install Ollama** (if you haven't already): https://ollama.com/download

2. **Pull a model.** The default is Llama 3.1 8B, a strong general-purpose
   instruction-following model that's reliable at returning well-formed JSON
   (which this app depends on to render the UI):

   ```bash
   ollama pull llama3.1:8b
   ```

   Other options selectable in the app's sidebar:
   - `meditron:7b` - continually pretrained on medical literature (PubMed,
     clinical guidelines). More domain knowledge, but less reliable at
     strict JSON formatting than llama3.1.
   - `qwen2.5:7b`, `mistral`, `llama3.2` - lighter/faster general fallbacks.

   Pull whichever you plan to use, e.g. `ollama pull meditron:7b`.

3. **Make sure the Ollama server is running** (the desktop app running in
   the background is enough, or run `ollama serve` manually).

4. **Install Python dependencies:**

   ```bash
   cd medlens
   python -m venv .venv && source .venv/bin/activate   # optional but recommended
   pip install -r requirements.txt
   ```

5. **Run the app:**

   ```bash
   streamlit run app.py
   ```

   It will open in your browser, usually at `http://localhost:8501`.

## Using it

1. Pick a model in the sidebar (must already be pulled - see above).
2. Either upload a `.pdf`/`.txt` report, or paste the report text directly.
3. Optionally add context (symptoms, history, medications).
4. Click **Analyze report**.
5. Review the summary, risk flags, foresight items, and suggested questions.

Try it first with `sample_reports/sample_report.txt` (a fictional report) to
confirm your setup works end to end.

## How the "foresight" works

The system prompt (in `medlens/prompts.py`) instructs the model to return a
single JSON object with these sections:

- `summary` - plain-language overview
- `key_findings` - what's in the report, explained
- `risk_flags` - anything concerning, tagged `low` / `medium` / `high`
  severity (high-severity items are meant for anything urgent, with advice
  to seek care promptly)
- `foresight` - forward-looking observations (e.g. "if this trend
  continues...", "worth rechecking at your next visit") with a timeframe and
  rationale grounded in the report's own content
- `recommended_questions` - questions to ask your doctor
- `lifestyle_suggestions` - general, non-prescriptive notes
- `disclaimer` - always included

The model is explicitly instructed never to state a definitive diagnosis,
never invent values not present in the report, and to flag emergencies
clearly. If the model's reply isn't valid JSON, the app falls back to
showing the raw text so nothing is silently lost.

## Configuration

Environment variable `OLLAMA_HOST` can point the app at a non-default
Ollama server address (default `http://localhost:11434`). See
`medlens/config.py` for model lists and timeouts.

## Extending this project

Ideas for taking this further:
- Add OCR (e.g. `pytesseract`) for scanned PDF reports without a text layer.
- Track multiple reports over time and ask the model to compare trends
  across visits (the `foresight` section is built with this in mind).
- Add authentication and encrypted local storage if you want to keep a
  history of past reports.
- Swap in a vision-capable local model to read embedded charts/images in
  imaging reports.

## Disclaimer

MedLens is not a substitute for professional medical advice, diagnosis, or
treatment. Always seek the advice of a qualified health provider with any
questions about a medical condition. If you think you may have a medical
emergency, call your local emergency number immediately.
