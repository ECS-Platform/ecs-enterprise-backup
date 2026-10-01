"""AI functional capabilities over ECS's real AI implementation (audit-LLM service, chatbot, RAG, evidence reuse).

No LLM is created or called directly by the framework: it only calls ECS routes, and ECS decides mock/live.
  POST /api/audit-llm/query {prompt_id, query, input_variables, use_rag, ...}      -> result (response, evidence_context, ...)
  POST /api/audit-llm/validate-grounding {result | answer+evidence_context}         -> grounding / citation evaluation
  POST /api/audit-llm/{classify,token-estimate,replay,compare}   GET /api/audit-llm/{prompts,profiles}
  POST /mvp/chat (form query, framework_name)  /chat  /mvp/api/chat-{response-mode,investigation,action}
  GET  /mvp/api/common-evidence-presets  POST /mvp/api/common-evidence-query (query_key|query, application, framework)
  GET  /mvp/ai-ops-assistant/summary/{mode}                                          -> AI-ops narrative summaries
  POST /api/evidence-reuse/analyze                                                   -> similarity / reuse candidates
LLM failure simulation is operator-driven: start ECS with the LLM provider disabled/unreachable (config/llm.yaml,
ECS_LLM_PROVIDER=none) and set ECS_FT_AI_FAILURE_READY=true.
"""

from __future__ import annotations

from typing import Any

from .api_client import ApiResponse, EcsApiClient
from .data_factory import DataFactory
from .errors import CapabilityBlocked


class AiHelper:
    def __init__(self, api: EcsApiClient, data: DataFactory) -> None:
        self.api, self.data = api, data

    # ---- prompt / query -----------------------------------------------------------------------------------------
    def prompts(self) -> ApiResponse:
        return self.api.get("/api/audit-llm/prompts")

    def query(self, query: str | None = None, *, prompt_id: str = "", use_rag: bool = True, persona: str | None = None,
              **variables: Any) -> ApiResponse:
        client = self.api.as_persona(persona) if persona else self.api
        return client.post("/api/audit-llm/query", json={"prompt_id": prompt_id, "query": query or self.data.prompt("evidence"),
                                                       "input_variables": variables, "use_rag": use_rag})

    def result_of(self, resp: ApiResponse) -> dict[str, Any]:
        body = resp.json()
        return body.get("result", body) if isinstance(body, dict) else {}

    def validate_grounding(self, result: dict[str, Any]) -> dict[str, Any]:
        resp = self.api.post("/api/audit-llm/validate-grounding", json={"result": result})
        return resp.json()

    def chat(self, question: str, *, framework_name: str = "", persona: str | None = None) -> ApiResponse:
        client = self.api.as_persona(persona) if persona else self.api
        return client.post("/mvp/chat", data={"query": question, "framework_name": framework_name, "return_url": "/dashboard"})

    def common_evidence_presets(self) -> ApiResponse:
        return self.api.get("/mvp/api/common-evidence-presets")

    def common_evidence_query(self, *, query_key: str = "", query: str = "", application: str = "", framework: str = "",
                              persona: str | None = None) -> ApiResponse:
        client = self.api.as_persona(persona) if persona else self.api
        return client.post("/mvp/api/common-evidence-query", data={
            "query_key": query_key, "query": query, "application": application or self.data.application(),
            "framework": framework or self.data.framework()})

    def ops_summary(self, mode: str) -> ApiResponse:
        return self.api.get(f"/mvp/ai-ops-assistant/summary/{mode}")

    # ---- similarity / reuse --------------------------------------------------------------------------------------------
    def similar_evidence(self, **scope: str) -> ApiResponse:
        return self.api.post("/api/evidence-reuse/analyze", params=scope)

    def reuse_records(self, **scope: str) -> ApiResponse:
        return self.api.get("/api/evidence-reuse/records", params=scope)

    # ---- inspections used by assertions ---------------------------------------------------------------------------------
    @staticmethod
    def citations(result: dict[str, Any]) -> list[Any]:
        for k in ("citations", "sources", "evidence_context", "evidence", "references"):
            v = result.get(k)
            if v:
                return v if isinstance(v, list) else [v]
        return []

    @staticmethod
    def is_no_answer(result: dict[str, Any]) -> bool:
        text = (str(result.get("response") or result.get("answer") or "")).lower()
        return not AiHelper.citations(result) or any(t in text for t in ("no evidence", "not found", "no relevant", "cannot", "unable", "don't have"))

    @staticmethod
    def provenance(result: dict[str, Any]) -> dict[str, Any]:
        keys = ("provider", "model", "provider_model", "mode", "simulated", "fallback", "fallback_reason", "prompt_id", "profile", "ram_profile")
        return {k: result[k] for k in keys if k in result}

    def require_failure_mode(self) -> None:
        if not self.api.cfg.get("hooks.ai_failure_ready"):
            raise CapabilityBlocked("AI-failure tests need ECS started with the LLM/vector provider disabled or unreachable "
                                    "(ECS_LLM_PROVIDER=none) and ECS_FT_AI_FAILURE_READY=true.", requires="AI failure environment")

    def require_live(self) -> None:
        if not self.api.cfg.feature("ai_live"):
            raise CapabilityBlocked("Live-LLM assertions are disabled (ECS_FT_AI_LIVE=false).", requires="ai_live flag")
