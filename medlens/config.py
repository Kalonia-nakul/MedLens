"""Configuration for MedLens."""

import os

# Ollama connection settings. Override with an OLLAMA_HOST env var if your
# server runs somewhere other than the default local port.
OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")

# Default model: Llama 3.1 8B is a strong general-purpose instruction-follower
# that runs comfortably on consumer hardware (CPU or a single GPU) and is
# reliable at returning well-formed structured (JSON) output, which this app
# depends on. That combination makes it a better default than a pure
# "medical" model for this task.
DEFAULT_MODEL = "llama3.1:8b"

# Alternatives offered in the sidebar:
# - meditron:7b   -> continually pretrained on medical literature (PubMed,
#                    clinical guidelines, replication trials). Brings more
#                    domain knowledge, but is weaker than llama3.1 at
#                    following strict formatting instructions, so JSON
#                    parsing may fall back to plain text more often.
# - qwen2.5:7b    -> solid, fast general-purpose fallback.
# - mistral       -> lightweight general-purpose fallback.
# - llama3.2      -> smaller/faster llama if 8b is too slow on your machine.
AVAILABLE_MODELS = [
    "llama3.1:8b",
    "meditron:7b",
    "qwen2.5:7b",
    "mistral",
    "llama3.2",
]

REQUEST_TIMEOUT = 180  # seconds - local CPU generation can be slow
