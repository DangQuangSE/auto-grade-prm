import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Dict, Optional


OPENROUTER_PROVIDER = "openrouter"
DEFAULT_OPENROUTER_MODEL = "tencent/hy3:free"
DEFAULT_OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1/chat/completions"


class ProviderError(Exception):
    """Controlled provider failure safe to surface without credentials."""


@dataclass
class ProviderResult:
    ok: bool
    provider: str
    model: str
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


def _get_model() -> str:
    return os.getenv("OPENROUTER_MODEL", DEFAULT_OPENROUTER_MODEL).strip() or DEFAULT_OPENROUTER_MODEL


def get_provider_config() -> Dict[str, Any]:
    api_key = os.getenv("OPENROUTER_API_KEY", "").strip()
    return {
        "provider": OPENROUTER_PROVIDER,
        "model": _get_model(),
        "api_key_configured": bool(api_key),
    }


def validate_grading_report(report: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(report, dict):
        raise ProviderError("Provider response must be a JSON object.")

    score = report.get("overall_score")
    if not isinstance(score, (int, float)) or not 0 <= float(score) <= 10:
        raise ProviderError("Provider response overall_score must be a number from 0.0 to 10.0.")

    breakdown = report.get("criteria_breakdown")
    if not isinstance(breakdown, dict) or not breakdown:
        raise ProviderError("Provider response criteria_breakdown must be a non-empty object.")

    for criterion, detail in breakdown.items():
        if not isinstance(criterion, str) or not isinstance(detail, dict):
            raise ProviderError("Provider response criteria_breakdown has an invalid item.")
        item_score = detail.get("score")
        feedback = detail.get("feedback")
        if not isinstance(item_score, (int, float)) or not 0 <= float(item_score) <= 10:
            raise ProviderError("Provider response criterion score must be a number from 0.0 to 10.0.")
        if not isinstance(feedback, str):
            raise ProviderError("Provider response criterion feedback must be a string.")

    if not isinstance(report.get("summary"), str):
        raise ProviderError("Provider response summary must be a string.")

    warnings = report.get("warnings")
    if warnings is None:
        report["warnings"] = []
    elif not isinstance(warnings, list):
        raise ProviderError("Provider response warnings must be a list.")

    return report


class OpenRouterProvider:
    def __init__(self) -> None:
        self.provider = OPENROUTER_PROVIDER
        self.model = _get_model()
        self.base_url = (
            os.getenv("OPENROUTER_BASE_URL", DEFAULT_OPENROUTER_BASE_URL).strip()
            or DEFAULT_OPENROUTER_BASE_URL
        )
        self.api_key = os.getenv("OPENROUTER_API_KEY", "").strip()

    def generate_json(self, prompt: str) -> ProviderResult:
        if not self.api_key:
            return ProviderResult(
                ok=False,
                provider=self.provider,
                model=self.model,
                error="OPENROUTER_API_KEY is not configured.",
            )

        try:
            body = {
                "model": self.model,
                "messages": [
                    {
                        "role": "system",
                        "content": "Return only valid JSON. Do not include markdown fences or prose.",
                    },
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.2,
                "response_format": self._response_format(),
            }
            response_bytes = self._post(body)
            parsed = self.parse_response(response_bytes)
            return ProviderResult(
                ok=True,
                provider=self.provider,
                model=self.model,
                data=parsed,
            )
        except ProviderError as exc:
            return ProviderResult(
                ok=False,
                provider=self.provider,
                model=self.model,
                error=self._sanitize_error(str(exc)),
            )

    def _post(self, body: Dict[str, Any]) -> bytes:
        payload = json.dumps(body).encode("utf-8")
        request = urllib.request.Request(
            self.base_url,
            data=payload,
            method="POST",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "Accept": "application/json",
                "HTTP-Referer": os.getenv("OPENROUTER_HTTP_REFERER", "http://localhost:8000"),
                "X-Title": os.getenv("OPENROUTER_APP_TITLE", "Flutter Code Auto-Grader"),
            },
        )

        try:
            with urllib.request.urlopen(request, timeout=120) as response:
                return response.read()
        except urllib.error.HTTPError as exc:
            details = exc.read().decode("utf-8", errors="replace")
            raise ProviderError(f"OpenRouter HTTP error {exc.code}: {details}") from exc
        except urllib.error.URLError as exc:
            raise ProviderError(f"OpenRouter connection error: {exc.reason}") from exc
        except TimeoutError as exc:
            raise ProviderError("OpenRouter request timed out.") from exc

    @staticmethod
    def parse_response(response_bytes: bytes) -> Dict[str, Any]:
        try:
            envelope = json.loads(response_bytes.decode("utf-8"))
            content = envelope["choices"][0]["message"]["content"]
        except (UnicodeDecodeError, json.JSONDecodeError, KeyError, IndexError, TypeError) as exc:
            raise ProviderError("OpenRouter response envelope is invalid.") from exc

        try:
            report = json.loads(content)
        except json.JSONDecodeError as exc:
            raise ProviderError("OpenRouter message content must be valid JSON.") from exc

        return validate_grading_report(report)

    def _sanitize_error(self, message: str) -> str:
        if self.api_key:
            return message.replace(self.api_key, "[redacted]")
        return message

    @staticmethod
    def _response_format() -> Dict[str, Any]:
        return {
            "type": "json_schema",
            "json_schema": {
                "name": "flutter_grading_report",
                "strict": True,
                "schema": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": [
                        "overall_score",
                        "criteria_breakdown",
                        "summary",
                        "warnings",
                    ],
                    "properties": {
                        "overall_score": {
                            "type": "number",
                            "minimum": 0,
                            "maximum": 10,
                        },
                        "criteria_breakdown": {
                            "type": "object",
                            "minProperties": 1,
                            "additionalProperties": {
                                "type": "object",
                                "additionalProperties": False,
                                "required": ["score", "feedback"],
                                "properties": {
                                    "score": {
                                        "type": "number",
                                        "minimum": 0,
                                        "maximum": 10,
                                    },
                                    "feedback": {"type": "string"},
                                },
                            },
                        },
                        "summary": {"type": "string"},
                        "warnings": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                    },
                },
            },
        }
