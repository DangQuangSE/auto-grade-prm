import hashlib
import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Dict, Optional


OPENROUTER_PROVIDER = "openrouter"
DEFAULT_OPENROUTER_MODEL = "openrouter/free"
DEFAULT_OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1/chat/completions"
OPENCODE_PROVIDER = "opencode"
DEFAULT_OPENCODE_MODEL = "mimo-v2.5-free"
DEFAULT_OPENCODE_BASE_URL = "https://opencode.ai/zen/v1"
DEFAULT_PROVIDER_TIMEOUT_SECONDS = 90.0
MAX_PROVIDER_TIMEOUT_SECONDS = 100.0
DEFAULT_PRIMARY_PROVIDER_TIMEOUT_SECONDS = 90.0
MAX_PRIMARY_PROVIDER_TIMEOUT_SECONDS = 100.0


class ProviderError(Exception):
    """Controlled provider failure safe to surface without credentials."""


@dataclass
class ProviderResult:
    ok: bool
    provider: str
    model: str
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


def _derive_seed(prompt: str) -> int:
    digest = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
    return int(digest[:8], 16)


def _get_model() -> str:
    return os.getenv("OPENROUTER_MODEL", DEFAULT_OPENROUTER_MODEL).strip() or DEFAULT_OPENROUTER_MODEL


def _get_timeout(
    env_name: str = "OPENROUTER_TIMEOUT_SECONDS",
    default: float = DEFAULT_PROVIDER_TIMEOUT_SECONDS,
    maximum: float = MAX_PROVIDER_TIMEOUT_SECONDS,
) -> float:
    raw_value = os.getenv(env_name, os.getenv("AI_PROVIDER_TIMEOUT_SECONDS", "")).strip()
    if not raw_value:
        return default
    try:
        timeout = float(raw_value)
    except ValueError:
        return default
    return min(maximum, max(1.0, timeout))


def get_provider_config() -> Dict[str, Any]:
    return {
        "provider": OPENCODE_PROVIDER,
        "model": os.getenv("OPENCODE_MODEL", DEFAULT_OPENCODE_MODEL).strip() or DEFAULT_OPENCODE_MODEL,
        "api_key_configured": bool(os.getenv("OPENCODE_API_KEY", "").strip()),
        "fallback_provider": OPENROUTER_PROVIDER,
        "fallback_model": _get_model(),
        "fallback_api_key_configured": bool(os.getenv("OPENROUTER_API_KEY", "").strip()),
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
        suggestion = detail.get("suggestion")
        if suggestion is None:
            detail["suggestion"] = ""
        elif not isinstance(suggestion, str):
            raise ProviderError("Provider response criterion suggestion must be a string.")

    if not isinstance(report.get("summary"), str):
        raise ProviderError("Provider response summary must be a string.")

    warnings = report.get("warnings")
    if warnings is None:
        report["warnings"] = []
    elif not isinstance(warnings, list):
        raise ProviderError("Provider response warnings must be a list.")

    return report


class OpenRouterProvider:
    api_key_env = "OPENROUTER_API_KEY"

    def __init__(self) -> None:
        self.provider = OPENROUTER_PROVIDER
        self.model = _get_model()
        self.base_url = (
            os.getenv("OPENROUTER_BASE_URL", DEFAULT_OPENROUTER_BASE_URL).strip()
            or DEFAULT_OPENROUTER_BASE_URL
        )
        self.api_key = os.getenv(self.api_key_env, "").strip()
        self.timeout = _get_timeout()

    def generate_json(self, prompt: str) -> ProviderResult:
        if not self.api_key:
            return ProviderResult(
                ok=False,
                provider=self.provider,
                model=self.model,
                error=f"{self.api_key_env} is not configured.",
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
                "temperature": 0,
                "seed": _derive_seed(prompt),
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
                "User-Agent": os.getenv(
                    "AI_PROVIDER_USER_AGENT",
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) FlutterCodeAutoGrader/1.0",
                ),
                "HTTP-Referer": os.getenv("OPENROUTER_HTTP_REFERER", "http://localhost:8000"),
                "X-Title": os.getenv("OPENROUTER_APP_TITLE", "Flutter Code Auto-Grader"),
            },
        )

        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                return response.read()
        except urllib.error.HTTPError as exc:
            details = exc.read().decode("utf-8", errors="replace")
            raise ProviderError(self._format_http_error(exc.code, details)) from exc
        except urllib.error.URLError as exc:
            raise ProviderError(f"{self.provider} connection error: {exc.reason}") from exc
        except TimeoutError as exc:
            raise ProviderError(f"{self.provider} request timed out.") from exc

    @staticmethod
    def parse_response(response_bytes: bytes) -> Dict[str, Any]:
        try:
            envelope = json.loads(response_bytes.decode("utf-8"))
            content = envelope["choices"][0]["message"]["content"]
        except (UnicodeDecodeError, json.JSONDecodeError, KeyError, IndexError, TypeError) as exc:
            raise ProviderError("Provider response envelope is invalid.") from exc

        try:
            report = json.loads(content)
        except json.JSONDecodeError as exc:
            raise ProviderError("Provider message content must be valid JSON.") from exc

        return validate_grading_report(report)

    def _sanitize_error(self, message: str) -> str:
        if self.api_key:
            return message.replace(self.api_key, "[redacted]")
        return message

    def _format_http_error(self, status_code: int, details: str) -> str:
        """Keep upstream failures useful without exposing a large metadata payload."""
        message = "Request failed."
        try:
            payload = json.loads(details)
            error = payload.get("error", {}) if isinstance(payload, dict) else {}
            if isinstance(error, dict) and isinstance(error.get("message"), str):
                message = error["message"].strip()[:300] or message
        except json.JSONDecodeError:
            if details.strip():
                message = details.strip()[:300]
        return f"{self.provider} HTTP error {status_code}: {message}"

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
                                "required": ["score", "feedback", "suggestion"],
                                "properties": {
                                    "score": {
                                        "type": "number",
                                        "minimum": 0,
                                        "maximum": 10,
                                    },
                                    "feedback": {"type": "string"},
                                    "suggestion": {"type": "string"},
                                },
                            },
                        },
                        "summary": {"type": "string"},
                        "warnings": {
                            "type": "array",
                            "items": {
                                "type": "string",
                                "description": (
                                    "Must start with the exact file name where the issue was found, "
                                    "e.g. 'app_router.dart: file has 910 lines, hard to maintain.'"
                                ),
                            },
                        },
                    },
                },
            },
        }


class OpenCodeProvider(OpenRouterProvider):
    api_key_env = "OPENCODE_API_KEY"

    def __init__(self) -> None:
        self.provider = OPENCODE_PROVIDER
        self.model = os.getenv("OPENCODE_MODEL", DEFAULT_OPENCODE_MODEL).strip() or DEFAULT_OPENCODE_MODEL
        base_url = os.getenv("OPENCODE_BASE_URL", DEFAULT_OPENCODE_BASE_URL).strip() or DEFAULT_OPENCODE_BASE_URL
        self.base_url = f"{base_url.rstrip('/')}/chat/completions"
        self.api_key = os.getenv(self.api_key_env, "").strip()
        self.timeout = _get_timeout(
            env_name="OPENCODE_TIMEOUT_SECONDS",
            default=DEFAULT_PRIMARY_PROVIDER_TIMEOUT_SECONDS,
            maximum=MAX_PRIMARY_PROVIDER_TIMEOUT_SECONDS,
        )

    @staticmethod
    def _response_format() -> Dict[str, Any]:
        return {"type": "json_object"}
