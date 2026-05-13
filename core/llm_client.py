from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
import httpx


@dataclass(frozen=True)
class LlmConfig:
    base_url: str
    api_key: str
    model: str
    timeout_s: float = 60.0


def load_config() -> LlmConfig:
    # Load .env from current working directory if present.
    load_dotenv(override=False)
    base_url = (os.getenv("OPENAI_BASE_URL", "") or "").strip()
    api_key = (os.getenv("OPENAI_API_KEY", "") or "").strip()
    model = (os.getenv("OPENAI_MODEL", "") or "").strip()
    timeout_s = float(os.getenv("OPENAI_TIMEOUT_S", "60") or "60")
    if not base_url:
        base_url = "https://ai.dianhuomao.shop/v1"
    return LlmConfig(base_url=base_url, api_key=api_key, model=model, timeout_s=timeout_s)


def _strip_code_fences(text: str) -> str:
    t = text.strip()
    if t.startswith("```"):
        t = re.sub(r"^```[a-zA-Z0-9_-]*\s*", "", t)
        t = re.sub(r"\s*```$", "", t)
    return t.strip()


def _extract_json(text: str) -> Any:
    t = _strip_code_fences(text)
    try:
        return json.loads(t)
    except Exception:
        # Best-effort: find first {...} or [...]
        m = re.search(r"(\{.*\}|\[.*\])", t, flags=re.DOTALL)
        if not m:
            raise
        return json.loads(m.group(1))


class LlmClient:
    """
    OpenAI Python SDK compatible client that supports custom base_url.
    Uses: client.chat.completions.create(...)
    """

    def __init__(self, config: Optional[LlmConfig] = None) -> None:
        self.config = config or load_config()
        self._client = None

    @property
    def enabled(self) -> bool:
        return bool(self.config.api_key) and bool(self.config.base_url) and bool(self.config.model)

    def _get_client(self):
        if self._client is not None:
            return self._client
        from openai import OpenAI

        http_client = httpx.Client(timeout=httpx.Timeout(self.config.timeout_s))
        self._client = OpenAI(
            api_key=self.config.api_key,
            base_url=self.config.base_url,
            http_client=http_client,
        )
        return self._client

    def chat(self, system: str, user: str, temperature: float = 0.2, max_tokens: int = 1200) -> str:
        if not self.enabled:
            raise RuntimeError("LLM is not configured. Set OPENAI_API_KEY, OPENAI_BASE_URL, OPENAI_MODEL.")
        client = self._get_client()
        resp = client.chat.completions.create(
            model=self.config.model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return (resp.choices[0].message.content or "").strip()

    def json_completion(self, system: str, user: str) -> Dict[str, Any]:
        text = self.chat(system=system, user=user)
        data = _extract_json(text)
        if not isinstance(data, dict):
            raise ValueError("Expected a JSON object.")
        return data

    def json_any_completion(self, system: str, user: str) -> Any:
        text = self.chat(system=system, user=user)
        return _extract_json(text)

    def json_list_completion(self, system: str, user: str) -> List[Dict[str, Any]]:
        text = self.chat(system=system, user=user)
        data = _extract_json(text)
        if not isinstance(data, list):
            raise ValueError("Expected a JSON array.")
        out: List[Dict[str, Any]] = []
        for item in data:
            if isinstance(item, dict):
                out.append(item)
        return out
