"""Pluggable LLM provider abstraction for the transcription-assist customization.

Selected via env LLM_PROVIDER=ollama|openai (see config.py). Both providers
expose the same `transcribe_image(image_bytes, prompt) -> str` call so the
rest of the app doesn't care which backend is used.
"""

import base64

import httpx

import config


class LLMError(RuntimeError):
    pass


class OllamaProvider:
    def __init__(self, base_url: str, model: str):
        self.base_url = base_url.rstrip("/")
        self.model = model

    def transcribe_image(self, image_bytes: bytes, prompt: str) -> str:
        b64 = base64.b64encode(image_bytes).decode("ascii")
        payload = {
            "model": self.model,
            "messages": [
                {"role": "user", "content": prompt, "images": [b64]},
            ],
            "stream": False,
        }
        try:
            resp = httpx.post(
                f"{self.base_url}/api/chat", json=payload, timeout=120
            )
            resp.raise_for_status()
        except httpx.HTTPError as exc:
            raise LLMError(f"Ollama request failed: {exc}") from exc
        data = resp.json()
        return data.get("message", {}).get("content", "").strip()


class OpenAICompatibleProvider:
    def __init__(self, base_url: str, api_key: str, model: str):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model

    def transcribe_image(self, image_bytes: bytes, prompt: str) -> str:
        b64 = base64.b64encode(image_bytes).decode("ascii")
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/png;base64,{b64}"},
                        },
                    ],
                }
            ],
        }
        headers = {"Authorization": f"Bearer {self.api_key}"}
        try:
            resp = httpx.post(
                f"{self.base_url}/chat/completions",
                json=payload,
                headers=headers,
                timeout=120,
            )
            resp.raise_for_status()
        except httpx.HTTPError as exc:
            raise LLMError(f"Remote LLM request failed: {exc}") from exc
        data = resp.json()
        return data["choices"][0]["message"]["content"].strip()


def get_provider():
    if config.LLM_PROVIDER == "openai":
        return OpenAICompatibleProvider(
            config.OPENAI_BASE_URL, config.OPENAI_API_KEY, config.LLM_MODEL
        )
    return OllamaProvider(config.OLLAMA_BASE_URL, config.LLM_MODEL)


DEFAULT_PROMPT = (
    "Transcribe exactly the handwritten or printed answer visible in this "
    "cropped exam answer box. Reply with only the transcribed answer, no "
    "commentary."
)
