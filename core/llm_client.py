from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin
from urllib.request import Request, urlopen

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - optional dependency
    def load_dotenv(*args: Any, **kwargs: Any) -> bool:
        return False


@dataclass(frozen=True)
class LlmConfig:
    provider: str
    api_key: str
    model: str
    base_url: str
    timeout_s: float = 60.0


def load_config() -> LlmConfig:
    load_dotenv(override=False)

    provider = (os.getenv("LLM_PROVIDER", "") or "").strip().lower()

    anthropic_api_key = (os.getenv("ANTHROPIC_API_KEY", "") or "").strip()
    anthropic_model = (
        (os.getenv("ANTHROPIC_MODEL", "") or "").strip()
        or (os.getenv("CLAUDE_MODEL", "") or "").strip()
    )

    openai_api_key = (os.getenv("OPENAI_API_KEY", "") or "").strip()
    openai_model = (os.getenv("OPENAI_MODEL", "") or "").strip()
    openai_base_url = (os.getenv("OPENAI_BASE_URL", "") or "").strip() or "https://api.openai.com/v1"
    timeout_s = float(os.getenv("LLM_TIMEOUT_S", os.getenv("OPENAI_TIMEOUT_S", "60")) or "60")

    if not provider:
        if anthropic_api_key and anthropic_model:
            provider = "anthropic"
        elif openai_api_key and openai_model:
            provider = "openai_compatible"
        else:
            provider = "mock"

    if provider == "anthropic":
        return LlmConfig(
            provider=provider,
            api_key=anthropic_api_key,
            model=anthropic_model,
            base_url=(os.getenv("ANTHROPIC_BASE_URL", "") or "").strip() or "https://api.anthropic.com",
            timeout_s=timeout_s,
        )

    if provider == "openai_compatible":
        return LlmConfig(
            provider=provider,
            api_key=openai_api_key,
            model=openai_model,
            base_url=openai_base_url,
            timeout_s=timeout_s,
        )

    return LlmConfig(provider="mock", api_key="", model="", base_url="", timeout_s=timeout_s)


def _strip_code_fences(text: str) -> str:
    value = text.strip()
    if value.startswith("```"):
        value = re.sub(r"^```[a-zA-Z0-9_-]*\s*", "", value)
        value = re.sub(r"\s*```$", "", value)
    return value.strip()


def _extract_json(text: str) -> Any:
    candidate = _strip_code_fences(text)
    try:
        return json.loads(candidate)
    except Exception:
        match = re.search(r"(\{.*\}|\[.*\])", candidate, flags=re.DOTALL)
        if not match:
            raise
        return json.loads(match.group(1))


class LlmClient:
    def __init__(self, config: Optional[LlmConfig] = None) -> None:
        self.config = config or load_config()

    @property
    def enabled(self) -> bool:
        return bool(self.config.api_key and self.config.model and self.config.base_url)

    def chat(self, system: str, user: str, temperature: float = 0.2, max_tokens: int = 2000) -> str:
        if not self.enabled:
            raise RuntimeError("LLM is not configured.")

        if self.config.provider == "anthropic":
            url = urljoin(f"{self.config.base_url.rstrip('/')}/", "v1/messages")
            request = Request(
                url,
                data=json.dumps(
                    {
                        "model": self.config.model,
                        "max_tokens": max_tokens,
                        "system": system,
                        "messages": [{"role": "user", "content": user}],
                        "temperature": temperature,
                    }
                ).encode("utf-8"),
                headers={
                    "x-api-key": self.config.api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                method="POST",
            )
            with urlopen(request, timeout=self.config.timeout_s) as response:
                data = json.loads(response.read().decode("utf-8"))
            content = data.get("content", [])
            text_parts = [part.get("text", "") for part in content if isinstance(part, dict)]
            return "\n".join(part for part in text_parts if part).strip()

        url = urljoin(f"{self.config.base_url.rstrip('/')}/", "chat/completions")
        request = Request(
            url,
            data=json.dumps(
                {
                    "model": self.config.model,
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": user},
                    ],
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                }
            ).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.config.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with urlopen(request, timeout=self.config.timeout_s) as response:
            data = json.loads(response.read().decode("utf-8"))
        return (
            data.get("choices", [{}])[0]
            .get("message", {})
            .get("content", "")
            .strip()
        )

    def json_completion(self, system: str, user: str) -> Dict[str, Any]:
        payload = _extract_json(self.chat(system=system, user=user))
        if not isinstance(payload, dict):
            raise ValueError("Expected a JSON object.")
        return payload

    def json_any_completion(self, system: str, user: str) -> Any:
        return _extract_json(self.chat(system=system, user=user))

    def json_list_completion(self, system: str, user: str) -> List[Dict[str, Any]]:
        payload = _extract_json(self.chat(system=system, user=user))
        if not isinstance(payload, list):
            raise ValueError("Expected a JSON list.")
        return [item for item in payload if isinstance(item, dict)]
