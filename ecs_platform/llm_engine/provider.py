"""LLM provider abstraction. Provider is config-selected; SDKs imported lazily.

Supported: gemini (default), openai, azure_openai, claude. Each provider is
credential-optional: the object constructs without keys, and only network calls
require them, so importing this module never breaks the app.
"""

from __future__ import annotations

import json
import re
import urllib.request
from abc import ABC, abstractmethod
from typing import Any

from ecs_platform.config import load_llm_config, resolve_secret

_THINK_RE = re.compile(r"<think>.*?</think>", re.DOTALL | re.IGNORECASE)


def _strip_think(text: str) -> str:
    """Remove qwen/deepseek-style <think>...</think> reasoning blocks from output."""
    return _THINK_RE.sub("", text or "").strip()


class LLMError(RuntimeError):
    pass


class LLMProvider(ABC):
    def __init__(self, cfg: dict[str, Any], provider_cfg: dict[str, Any]):
        self.cfg = cfg
        self.provider_cfg = provider_cfg
        self.model = cfg.get("model", "")
        self.embedding_model = cfg.get("embedding_model", "")
        self.temperature = float(cfg.get("temperature", 0.1))
        self.max_tokens = int(cfg.get("max_output_tokens", 2048))
        self.timeout = int(cfg.get("request_timeout_sec", 60))

    def api_key(self) -> str:
        return resolve_secret(self.provider_cfg.get("api_key_env", ""))

    def configured(self) -> bool:
        return bool(self.api_key())

    @abstractmethod
    def generate(self, prompt: str, *, system: str = "") -> str: ...

    @abstractmethod
    def embed(self, texts: list[str]) -> list[list[float]]: ...

    def _post_json(self, url: str, payload: dict[str, Any], headers: dict[str, str]) -> dict[str, Any]:
        body = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=body, method="POST",
                                     headers={"Content-Type": "application/json", **headers})
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as exc:  # noqa: BLE001
            raise LLMError(f"LLM request failed: {exc}") from exc


class GeminiProvider(LLMProvider):
    def _base(self) -> str:
        return self.provider_cfg.get("base_url", "https://generativelanguage.googleapis.com").rstrip("/")

    def generate(self, prompt: str, *, system: str = "") -> str:
        if not self.configured():
            raise LLMError("GEMINI_API_KEY is not set")
        url = f"{self._base()}/v1beta/models/{self.model}:generateContent?key={self.api_key()}"
        payload: dict[str, Any] = {
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": self.temperature, "maxOutputTokens": self.max_tokens},
        }
        if system:
            payload["systemInstruction"] = {"parts": [{"text": system}]}
        data = self._post_json(url, payload, {})
        try:
            return data["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError) as exc:
            raise LLMError(f"Unexpected Gemini response: {data}") from exc

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not self.configured():
            raise LLMError("GEMINI_API_KEY is not set")
        out: list[list[float]] = []
        for text in texts:
            url = f"{self._base()}/v1beta/models/{self.embedding_model}:embedContent?key={self.api_key()}"
            payload = {"model": f"models/{self.embedding_model}",
                       "content": {"parts": [{"text": text}]}}
            data = self._post_json(url, payload, {})
            out.append(data.get("embedding", {}).get("values", []))
        return out


class OpenAIProvider(LLMProvider):
    def _base(self) -> str:
        return self.provider_cfg.get("base_url", "https://api.openai.com/v1").rstrip("/")

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.api_key()}"}

    def generate(self, prompt: str, *, system: str = "") -> str:
        if not self.configured():
            raise LLMError("OPENAI_API_KEY is not set")
        messages = ([{"role": "system", "content": system}] if system else []) + [
            {"role": "user", "content": prompt}]
        data = self._post_json(f"{self._base()}/chat/completions",
                               {"model": self.model, "messages": messages,
                                "temperature": self.temperature, "max_tokens": self.max_tokens},
                               self._headers())
        return data["choices"][0]["message"]["content"]

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not self.configured():
            raise LLMError("OPENAI_API_KEY is not set")
        data = self._post_json(f"{self._base()}/embeddings",
                               {"model": self.embedding_model, "input": texts}, self._headers())
        return [d["embedding"] for d in data.get("data", [])]


class AzureOpenAIProvider(OpenAIProvider):
    def generate(self, prompt: str, *, system: str = "") -> str:
        if not self.configured():
            raise LLMError("AZURE_OPENAI_API_KEY is not set")
        base = self.provider_cfg.get("base_url", "").rstrip("/")
        deployment = resolve_secret(self.provider_cfg.get("deployment_env", "AZURE_OPENAI_DEPLOYMENT")) or self.model
        api_version = self.provider_cfg.get("api_version", "2024-02-15-preview")
        url = f"{base}/openai/deployments/{deployment}/chat/completions?api-version={api_version}"
        messages = ([{"role": "system", "content": system}] if system else []) + [
            {"role": "user", "content": prompt}]
        data = self._post_json(url, {"messages": messages, "temperature": self.temperature,
                                     "max_tokens": self.max_tokens}, {"api-key": self.api_key()})
        return data["choices"][0]["message"]["content"]


class ClaudeProvider(LLMProvider):
    def _base(self) -> str:
        return self.provider_cfg.get("base_url", "https://api.anthropic.com").rstrip("/")

    def generate(self, prompt: str, *, system: str = "") -> str:
        if not self.configured():
            raise LLMError("ANTHROPIC_API_KEY is not set")
        payload: dict[str, Any] = {"model": self.model, "max_tokens": self.max_tokens,
                                   "temperature": self.temperature,
                                   "messages": [{"role": "user", "content": prompt}]}
        if system:
            payload["system"] = system
        data = self._post_json(f"{self._base()}/v1/messages", payload,
                               {"x-api-key": self.api_key(), "anthropic-version": "2023-06-01"})
        return "".join(block.get("text", "") for block in data.get("content", []))

    def embed(self, texts: list[str]) -> list[list[float]]:
        raise LLMError("Claude provider does not offer embeddings; configure a separate embedding provider")


class OllamaProvider(LLMProvider):
    """Local Ollama via its REST API (no API key required).

    Uses POST /api/chat for generation and POST /api/embeddings for embeddings.
    Endpoint defaults to host.docker.internal so the dockerized ECS app reaches an
    Ollama daemon running on the host. Credential-optional: 'configured' is true
    whenever a base URL is set (Ollama needs no key)."""

    def _base(self) -> str:
        return self.provider_cfg.get("base_url", "http://host.docker.internal:11434").rstrip("/")

    def api_key(self) -> str:  # Ollama is keyless
        return ""

    def configured(self) -> bool:
        return bool(self._base())

    def generate(self, prompt: str, *, system: str = "") -> str:
        messages = ([{"role": "system", "content": system}] if system else []) + [
            {"role": "user", "content": prompt}]
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {"temperature": self.temperature, "num_predict": self.max_tokens},
        }
        data = self._post_json(f"{self._base()}/api/chat", payload, {})
        content = (data.get("message", {}) or {}).get("content", "")
        if not content:
            raise LLMError(f"Unexpected Ollama response: {data}")
        return _strip_think(content)

    def embed(self, texts: list[str]) -> list[list[float]]:
        model = self.embedding_model or self.model
        out: list[list[float]] = []
        for text in texts:
            data = self._post_json(f"{self._base()}/api/embeddings",
                                   {"model": model, "prompt": text}, {})
            vec = data.get("embedding", [])
            if not vec:
                raise LLMError(f"Ollama embeddings returned empty vector (model={model})")
            out.append(vec)
        return out


_PROVIDERS = {
    "gemini": GeminiProvider,
    "openai": OpenAIProvider,
    "azure_openai": AzureOpenAIProvider,
    "claude": ClaudeProvider,
    "ollama": OllamaProvider,
}


def get_provider(config: dict[str, Any] | None = None) -> LLMProvider:
    cfg = (config or load_llm_config()).get("llm", {})
    name = cfg.get("provider", "gemini")
    provider_cfg = (cfg.get("providers", {}) or {}).get(name, {})
    cls = _PROVIDERS.get(name)
    if not cls:
        raise LLMError(f"Unknown LLM provider: {name}")
    return cls(cfg, provider_cfg)
