"""Thin wrapper around the local Ollama server."""

from __future__ import annotations

import json

import ollama

from . import config


class MedLensError(RuntimeError):
    """Raised when the local Ollama server or model can't be reached/used."""


_STANDARD_DISCLAIMER = (
    "MedLens is not a substitute for professional medical advice, diagnosis, "
    "or treatment. Always seek the advice of a qualified health provider "
    "with any questions about a medical condition."
)


def get_client() -> ollama.Client:
    return ollama.Client(host=config.OLLAMA_HOST, timeout=config.REQUEST_TIMEOUT)


def list_local_models() -> list[str]:
    """Returns model names currently pulled on the local Ollama instance."""
    try:
        client = get_client()
        response = client.list()
        return [m.get("model", m.get("name", "")) for m in response.get("models", [])]
    except Exception as exc:
        raise MedLensError(
            f"Could not reach Ollama at {config.OLLAMA_HOST}. "
            f"Is the Ollama app/service running? Original error: {exc}"
        ) from exc


def analyze_report(
    system_prompt: str,
    user_prompt: str,
    model: str,
    temperature: float = 0.2,
) -> dict:
    """Sends the prompt to the local model and parses the JSON response."""
    client = get_client()
    try:
        response = client.chat(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            options={"temperature": temperature},
        )
    except Exception as exc:
        raise MedLensError(
            f"Ollama request failed for model '{model}'. Make sure you've "
            f"run `ollama pull {model}` first. Original error: {exc}"
        ) from exc

    content = response["message"]["content"].strip()
    return _parse_json_response(content)


def _parse_json_response(content: str) -> dict:
    """Best-effort extraction of a JSON object from the model's reply."""
    cleaned = content.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        if cleaned.lower().startswith("json"):
            cleaned = cleaned[4:]
    cleaned = cleaned.strip()

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        start, end = cleaned.find("{"), cleaned.rfind("}")
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(cleaned[start : end + 1])
            except json.JSONDecodeError:
                pass

    # Fall back: surface the raw text so the UI can still show something.
    return {
        "summary": content,
        "key_findings": [],
        "risk_flags": [],
        "foresight": [],
        "recommended_questions": [],
        "lifestyle_suggestions": [],
        "disclaimer": _STANDARD_DISCLAIMER,
        "_parse_error": True,
    }
