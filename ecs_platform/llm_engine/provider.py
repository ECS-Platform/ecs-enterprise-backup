"""LLM provider abstraction. Provider is config-selected; SDKs imported lazily.

Supported: gemini (default), openai, azure_openai, claude. Each provider is
credential-optional: the object constructs without keys, and only network calls
require them, so importing this module never breaks the app.
"""

from __future__ import annotations

import json
import os
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

    def generate_with_metadata(self, prompt: str, *, system: str = "") -> tuple[str, dict[str, Any]]:
        """Generate text and return provider usage metadata when available."""
        text = self.generate(prompt, system=system)
        return text, {}

    def _post_json(self, url: str, payload: dict[str, Any], headers: dict[str, str]) -> dict[str, Any]:
        body = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=body, method="POST",
                                     headers={"Content-Type": "application/json", **headers})
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                content_len_hdr = resp.headers.get("Content-Length")
                # Avoid waiting indefinitely on read-to-EOF if a server keeps the
                # connection open; prefer bounded read when Content-Length is present.
                if content_len_hdr:
                    raw = resp.read(int(content_len_hdr))
                else:
                    raw = resp.read()
                return json.loads(raw.decode("utf-8"))
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

    def generate_with_metadata(self, prompt: str, *, system: str = "") -> tuple[str, dict[str, Any]]:
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
            text = data["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError) as exc:
            raise LLMError(f"Unexpected Gemini response: {data}") from exc
        usage = data.get("usageMetadata", {}) or {}
        return text, {
            "input_tokens": int(usage.get("promptTokenCount", 0) or 0),
            "output_tokens": int(usage.get("candidatesTokenCount", 0) or 0),
            "total_tokens": int(usage.get("totalTokenCount", 0) or 0),
        }

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

    def generate_with_metadata(self, prompt: str, *, system: str = "") -> tuple[str, dict[str, Any]]:
        if not self.configured():
            raise LLMError("OPENAI_API_KEY is not set")
        messages = ([{"role": "system", "content": system}] if system else []) + [
            {"role": "user", "content": prompt}]
        data = self._post_json(
            f"{self._base()}/chat/completions",
            {"model": self.model, "messages": messages,
             "temperature": self.temperature, "max_tokens": self.max_tokens},
            self._headers(),
        )
        usage = data.get("usage", {}) or {}
        return data["choices"][0]["message"]["content"], {
            "input_tokens": int(usage.get("prompt_tokens", 0) or 0),
            "output_tokens": int(usage.get("completion_tokens", 0) or 0),
            "total_tokens": int(usage.get("total_tokens", 0) or 0),
        }

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

    def generate_with_metadata(self, prompt: str, *, system: str = "") -> tuple[str, dict[str, Any]]:
        if not self.configured():
            raise LLMError("AZURE_OPENAI_API_KEY is not set")
        base = self.provider_cfg.get("base_url", "").rstrip("/")
        deployment = resolve_secret(self.provider_cfg.get("deployment_env", "AZURE_OPENAI_DEPLOYMENT")) or self.model
        api_version = self.provider_cfg.get("api_version", "2024-02-15-preview")
        url = f"{base}/openai/deployments/{deployment}/chat/completions?api-version={api_version}"
        messages = ([{"role": "system", "content": system}] if system else []) + [
            {"role": "user", "content": prompt}]
        data = self._post_json(
            url,
            {"messages": messages, "temperature": self.temperature, "max_tokens": self.max_tokens},
            {"api-key": self.api_key()},
        )
        usage = data.get("usage", {}) or {}
        return data["choices"][0]["message"]["content"], {
            "input_tokens": int(usage.get("prompt_tokens", 0) or 0),
            "output_tokens": int(usage.get("completion_tokens", 0) or 0),
            "total_tokens": int(usage.get("total_tokens", 0) or 0),
        }


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

    def generate_with_metadata(self, prompt: str, *, system: str = "") -> tuple[str, dict[str, Any]]:
        if not self.configured():
            raise LLMError("ANTHROPIC_API_KEY is not set")
        payload: dict[str, Any] = {"model": self.model, "max_tokens": self.max_tokens,
                                   "temperature": self.temperature,
                                   "messages": [{"role": "user", "content": prompt}]}
        if system:
            payload["system"] = system
        data = self._post_json(
            f"{self._base()}/v1/messages",
            payload,
            {"x-api-key": self.api_key(), "anthropic-version": "2023-06-01"},
        )
        text = "".join(block.get("text", "") for block in data.get("content", []))
        usage = data.get("usage", {}) or {}
        input_tokens = int(usage.get("input_tokens", 0) or 0)
        output_tokens = int(usage.get("output_tokens", 0) or 0)
        return text, {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": input_tokens + output_tokens,
        }

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

    def _keep_alive(self) -> str:
        # Keep the model resident to avoid repeated cold starts. Configurable via
        # ECS_OLLAMA_KEEP_ALIVE (e.g. "30m", "-1" for forever, "0" to unload).
        return str(self.provider_cfg.get("keep_alive", self.cfg.get("keep_alive", "30m")))

    def _num_predict(self) -> int:
        # For benchmark stability, default Ollama generation length to 512.
        # Preserve explicit environment override when provided.
        if os.environ.get("ECS_LLM_MAX_TOKENS", "").strip():
            return self.max_tokens
        return int(self.provider_cfg.get("num_predict", 512))

    @staticmethod
    def _response_text(data: dict[str, Any]) -> str:
        msg = (data.get("message", {}) or {})
        content = (msg.get("content", "") or "").strip()
        if content:
            return _strip_think(content)
        # Accept max-length termination as a valid completion and fall back to
        # "thinking" text when assistant content is empty.
        if str(data.get("done_reason", "")).lower() == "length":
            thinking = (msg.get("thinking", "") or "").strip()
            if thinking:
                return thinking
        return ""

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
            "think": False,
            "keep_alive": self._keep_alive(),
            "options": {"temperature": self.temperature, "num_predict": self._num_predict()},
        }
        data = self._post_json(f"{self._base()}/api/chat", payload, {})
        content = self._response_text(data)
        if not content:
            raise LLMError(f"Unexpected Ollama response: {data}")
        return content

    def generate_with_metadata(self, prompt: str, *, system: str = "") -> tuple[str, dict[str, Any]]:
        messages = ([{"role": "system", "content": system}] if system else []) + [
            {"role": "user", "content": prompt}]
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "think": False,
            "keep_alive": self._keep_alive(),
            "options": {"temperature": self.temperature, "num_predict": self._num_predict()},
        }
        data = self._post_json(f"{self._base()}/api/chat", payload, {})
        content = self._response_text(data)
        if not content:
            raise LLMError(f"Unexpected Ollama response: {data}")
        input_tokens = int(data.get("prompt_eval_count", 0) or 0)
        output_tokens = int(data.get("eval_count", 0) or 0)
        return content, {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": input_tokens + output_tokens,
        }

    def embed(self, texts: list[str]) -> list[list[float]]:
        model = self.embedding_model or self.model
        out: list[list[float]] = []
        for text in texts:
            data = self._post_json(f"{self._base()}/api/embeddings",
                                   {"model": model, "prompt": text,
                                    "keep_alive": self._keep_alive()}, {})
            vec = data.get("embedding", [])
            if not vec:
                raise LLMError(f"Ollama embeddings returned empty vector (model={model})")
            out.append(vec)
        return out

    def warm(self) -> dict[str, Any]:
        """Load generation + embedding models into memory (resident via keep_alive).

        Sends a tiny request to each so the first real query isn't a cold start.
        Never raises; returns a status dict."""
        status: dict[str, Any] = {"chat_warm": False, "embed_warm": False, "detail": ""}
        try:
            self._post_json(f"{self._base()}/api/chat",
                            {"model": self.model, "messages": [{"role": "user", "content": "ok"}],
                             "stream": False, "keep_alive": self._keep_alive(),
                             "options": {"num_predict": 1}}, {})
            status["chat_warm"] = True
        except Exception as exc:  # noqa: BLE001
            status["detail"] = f"chat warm failed: {exc}"
        try:
            self.embed(["warm"])
            status["embed_warm"] = True
        except Exception as exc:  # noqa: BLE001
            status["detail"] += f"; embed warm failed: {exc}"
        return status


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
