"""Reusable LLM-call logging utility.

Wraps any LLM call and records one JSON-lines entry per call: task_id,
call_number, tokens_in, tokens_out, timestamp. Built now so the future
agent loop (gap resolution via LLM) has consistent, file-based call
accounting from day one — this module makes no LLM calls itself and is
exercised only by the baseline runner's smoke test, never on the
deterministic (no-LLM) baseline path.

Token counts are taken from the wrapped call's own usage report when it
provides one; otherwise they fall back to ECS's existing deterministic
chars/4 estimator (`modules.audit_intelligence.llm.token_estimator`) so a
provider that doesn't report usage still gets a consistent estimate rather
than a missing value.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from modules.audit_intelligence.llm.token_estimator import estimate_tokens

DEFAULT_LOG_PATH = Path("benchmarks/output/llm_call_log.jsonl")


def _ts() -> str:
    return datetime.now(timezone.utc).isoformat()


class LLMCallLogger:
    """Per-task call counter + JSONL sink for LLM call accounting."""

    def __init__(self, log_path: Path | str = DEFAULT_LOG_PATH):
        self.log_path = Path(log_path)
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self._call_counters: dict[str, int] = {}

    def next_call_number(self, task_id: str) -> int:
        n = self._call_counters.get(task_id, 0) + 1
        self._call_counters[task_id] = n
        return n

    def record(
        self,
        task_id: str,
        *,
        tokens_in: int,
        tokens_out: int,
        call_number: int | None = None,
    ) -> dict[str, Any]:
        """Append one call record and return it. Use when you already have
        the token counts (e.g. from a provider's usage report)."""
        entry = {
            "task_id": task_id,
            "call_number": call_number if call_number is not None else self.next_call_number(task_id),
            "tokens_in": int(tokens_in),
            "tokens_out": int(tokens_out),
            "timestamp": _ts(),
        }
        with self.log_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry, default=str) + "\n")
        return entry

    def wrap_call(
        self,
        task_id: str,
        call_fn: Callable[[str], Any],
        prompt: str,
    ) -> Any:
        """Invoke `call_fn(prompt)`, log the call, and return its result unchanged.

        `call_fn` may return a plain string (the completion text) or a dict
        with a `"text"` key and optional `"tokens_in"`/`"tokens_out"` usage
        fields; missing token counts are estimated from the prompt/response
        text.
        """
        response = call_fn(prompt)
        if isinstance(response, dict):
            text = str(response.get("text", ""))
            tokens_in = response.get("tokens_in")
            tokens_out = response.get("tokens_out")
        else:
            text = str(response)
            tokens_in = None
            tokens_out = None
        self.record(
            task_id,
            tokens_in=tokens_in if tokens_in is not None else estimate_tokens(prompt),
            tokens_out=tokens_out if tokens_out is not None else estimate_tokens(text),
        )
        return response

    def read_all(self) -> list[dict[str, Any]]:
        """Read back every logged call (for tests/inspection)."""
        if not self.log_path.exists():
            return []
        with self.log_path.open("r", encoding="utf-8") as fh:
            return [json.loads(line) for line in fh if line.strip()]
