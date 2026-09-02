import os
from pathlib import Path

PROJECTS_DIR = Path(os.environ.get("AMC_PROJECTS_DIR", "/data/projects"))

LLM_PROVIDER = os.environ.get("LLM_PROVIDER", "ollama")
OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://ollama:11434")
LLM_MODEL = os.environ.get("LLM_MODEL", "qwen2.5vl:3b")

# Only used when LLM_PROVIDER=openai (remote OpenAI-compatible endpoint).
OPENAI_BASE_URL = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
