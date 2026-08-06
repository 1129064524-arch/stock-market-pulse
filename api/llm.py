import json
import os
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.request import Request
from pathlib import Path

from dotenv import load_dotenv

from api.network import open_url

load_dotenv()

CONFIG_KEYS = (
    "LLM_BASE_URL",
    "LLM_ENDPOINT",
    "LLM_API_KEY",
    "LLM_MODEL",
    "LLM_PROTOCOL",
    "LLM_TIMEOUT_SECONDS",
    "LLM_AUTO_ANALYSIS",
    "LLM_AUTO_ANALYSIS_MINUTES",
)
SHARED_CONFIG_KEYS = (
    "PROMPT_ANALYSIS_API_BASE_URL",
    "PROMPT_ANALYSIS_ENDPOINT",
    "PROMPT_ANALYSIS_API_KEY",
    "PROMPT_ANALYSIS_MODEL",
)


class LLMConfigurationError(RuntimeError):
    """Raised when an OpenAI-compatible endpoint has not been configured."""


class LLMProviderError(RuntimeError):
    """Raised when the configured provider cannot complete a request."""


@dataclass(frozen=True)
class LLMSettings:
    base_url: str
    endpoint: str
    api_key: str
    model: str
    protocol: str
    timeout_seconds: float

    @property
    def configured(self) -> bool:
        return bool(self.base_url and self.api_key and self.model)


def get_settings() -> LLMSettings:
    base_url = (os.getenv("LLM_BASE_URL") or os.getenv("PROMPT_ANALYSIS_API_BASE_URL") or "").rstrip("/")
    configured_endpoint = os.getenv("LLM_ENDPOINT") or os.getenv("PROMPT_ANALYSIS_ENDPOINT") or ""
    protocol = (os.getenv("LLM_PROTOCOL") or ("responses" if configured_endpoint.endswith("/responses") else "chat_completions")).lower()
    if protocol not in {"responses", "chat_completions"}:
        protocol = "chat_completions"
    endpoint = configured_endpoint.rstrip("/") or (
        f"{base_url}/responses" if protocol == "responses" else f"{base_url}/chat/completions"
    )
    return LLMSettings(
        base_url=base_url,
        endpoint=endpoint,
        api_key=os.getenv("LLM_API_KEY") or os.getenv("PROMPT_ANALYSIS_API_KEY") or "",
        model=os.getenv("LLM_MODEL") or os.getenv("PROMPT_ANALYSIS_MODEL") or "",
        protocol=protocol,
        timeout_seconds=float(os.getenv("LLM_TIMEOUT_SECONDS", "25")),
    )


def config_file_path() -> Path:
    configured_path = (os.getenv("MARKET_PULSE_CONFIG_PATH") or ".env").strip()
    return Path(configured_path).expanduser()


def _mask_api_key(api_key: str) -> str:
    if not api_key:
        return ""
    if len(api_key) <= 8:
        return "••••••••"
    return f"{api_key[:4]}••••{api_key[-4:]}"


def public_settings() -> dict[str, object]:
    settings = get_settings()
    try:
        auto_minutes = max(int(os.getenv("LLM_AUTO_ANALYSIS_MINUTES", "3")), 1)
    except ValueError:
        auto_minutes = 3
    return {
        "configured": settings.configured,
        "base_url": settings.base_url,
        "endpoint": settings.endpoint,
        "model": settings.model,
        "protocol": settings.protocol,
        "timeout_seconds": settings.timeout_seconds,
        "api_key_set": bool(settings.api_key),
        "api_key_masked": _mask_api_key(settings.api_key),
        "auto_analysis_enabled": os.getenv("LLM_AUTO_ANALYSIS", "false").strip().lower() in {"1", "true", "yes", "on"},
        "auto_analysis_minutes": auto_minutes,
        "config_path": str(config_file_path()),
    }


def _write_env_values(values: dict[str, str | None]) -> None:
    path = config_file_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    existing = path.read_text(encoding="utf-8") if path.exists() else ""
    lines = existing.splitlines()
    written: set[str] = set()
    output: list[str] = []
    for line in lines:
        stripped = line.strip()
        key = stripped.split("=", 1)[0].strip() if stripped and not stripped.startswith("#") and "=" in stripped else ""
        if key in values:
            value = values[key]
            if value is not None:
                output.append(f"{key}={value}")
            written.add(key)
        else:
            output.append(line)
    for key, value in values.items():
        if key not in written and value is not None:
            output.append(f"{key}={value}")
    path.write_text("\n".join(output).rstrip() + "\n", encoding="utf-8")
    for key, value in values.items():
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value
    load_dotenv(path, override=True)


def update_settings(values: dict[str, object]) -> dict[str, object]:
    settings = get_settings()
    api_key = str(values.get("api_key") or "").strip()
    if not api_key or api_key == "KEEP_EXISTING":
        api_key = settings.api_key
    protocol = str(values.get("protocol") or "chat_completions").lower()
    if protocol not in {"responses", "chat_completions"}:
        protocol = "chat_completions"
    timeout_seconds = max(float(values.get("timeout_seconds") or 25), 5)
    auto_minutes = max(int(values.get("auto_analysis_minutes") or 3), 1)
    base_url = str(values.get("base_url") or "").strip().rstrip("/")
    endpoint = str(values.get("endpoint") or "").strip().rstrip("/")
    model = str(values.get("model") or "").strip()
    if not endpoint:
        endpoint = f"{base_url}/responses" if protocol == "responses" else f"{base_url}/chat/completions"
    _write_env_values({
        "LLM_BASE_URL": base_url,
        "LLM_ENDPOINT": endpoint,
        "LLM_API_KEY": api_key,
        "LLM_MODEL": model,
        "LLM_PROTOCOL": protocol,
        "LLM_TIMEOUT_SECONDS": str(timeout_seconds),
        "LLM_AUTO_ANALYSIS": "true" if bool(values.get("auto_analysis_enabled")) else "false",
        "LLM_AUTO_ANALYSIS_MINUTES": str(auto_minutes),
    })
    return public_settings()


def reset_settings() -> dict[str, object]:
    path = config_file_path()
    if path.exists():
        existing = path.read_text(encoding="utf-8")
        keep_lines = []
        keys = set(CONFIG_KEYS) | set(SHARED_CONFIG_KEYS)
        for line in existing.splitlines():
            stripped = line.strip()
            key = stripped.split("=", 1)[0].strip() if stripped and not stripped.startswith("#") and "=" in stripped else ""
            if key not in keys:
                keep_lines.append(line)
        path.write_text("\n".join(keep_lines).rstrip() + "\n", encoding="utf-8")
    for key in set(CONFIG_KEYS) | set(SHARED_CONFIG_KEYS):
        os.environ.pop(key, None)
    load_dotenv(path, override=True)
    return public_settings()


def test_connection() -> dict[str, object]:
    result = _request_json_analysis(
        """You are a connection probe. Return valid JSON only: {\"ok\":true}.""",
        {"probe": "connection"},
    )
    if result.get("ok") is not True:
        raise LLMProviderError("Provider connection probe returned an unexpected payload")
    return {"ok": True, "model": get_settings().model, "protocol": get_settings().protocol}


def _strip_code_fence(content: str) -> str:
    content = content.strip()
    if content.startswith("```"):
        return content.split("\n", 1)[1].rsplit("```", 1)[0].strip()
    return content


def _response_output_text(payload: dict) -> str:
    if isinstance(payload.get("output_text"), str) and payload["output_text"].strip():
        return payload["output_text"].strip()
    parts = []
    for item in payload.get("output", []):
        for content in item.get("content", []):
            value = content.get("text") or content.get("output_text")
            if isinstance(value, str):
                parts.append(value)
    return "".join(parts).strip()


def _parse_analysis_payload(payload: dict, protocol: str) -> dict:
    try:
        content = _response_output_text(payload) if protocol == "responses" else payload["choices"][0]["message"]["content"]
        return json.loads(_strip_code_fence(content))
    except (KeyError, IndexError, AttributeError, TypeError, json.JSONDecodeError) as error:
        raise LLMProviderError("Provider returned an invalid analysis payload") from error


def _request_json_analysis(system_prompt: str, context: dict) -> dict:
    """Send a bounded, local-data-only research context to the configured provider."""
    settings = get_settings()
    if not settings.configured:
        raise LLMConfigurationError("Configure LLM_* or the shared PROMPT_ANALYSIS_* channel")

    context_json = json.dumps(context, ensure_ascii=False)
    request_body = (
        {
            "model": settings.model,
            "input": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": context_json},
            ],
            "text": {"format": {"type": "json_object"}},
        }
        if settings.protocol == "responses"
        else {
            "model": settings.model,
            "temperature": 0.2,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": context_json},
            ],
        }
    )
    request = Request(
        settings.endpoint,
        data=json.dumps(request_body).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {settings.api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with open_url(request, timeout=settings.timeout_seconds) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except HTTPError as error:
        raise LLMProviderError(f"Provider returned HTTP {error.code}") from error
    except (URLError, TimeoutError) as error:
        raise LLMProviderError("Could not reach the configured model provider") from error

    return _parse_analysis_payload(payload, settings.protocol)


def analyze_market(snapshot: dict) -> dict:
    system_prompt = """You are a cautious market-research assistant for a personal stock analysis tool.
Use only the supplied market snapshot. Do not invent news, prices, financial facts, or certainty.
Do not give buy, sell, position-size, or guaranteed-return advice. Explain evidence and risk in concise Chinese.
Return valid JSON only, with this exact schema:
{
  "stance": "偏强|中性|谨慎|偏弱",
  "summary": "one concise Chinese sentence",
  "evidence": ["up to 3 factual observations from the snapshot"],
  "risks": ["up to 3 risks explicitly present in the snapshot"],
  "watchlist": [{"code":"string", "name":"string", "reason":"string"}],
  "disclaimer": "固定使用：该分析仅供研究参考，不构成投资建议。"
}
"""
    return _request_json_analysis(system_prompt, snapshot)


def analyze_signal(signal_context: dict) -> dict:
    """Explain one rule signal without turning it into a trading recommendation."""
    system_prompt = """You are a cautious market-research assistant for a personal stock analysis tool.
Use only the supplied local rule signal, market context, and locally stored daily bars. Do not invent news,
intraday data, fundamentals, price levels, catalysts, or certainty. Do not give buy, sell, hold, position-size,
entry, exit, or guaranteed-return advice. The output is a research checklist, not a recommendation.
Return valid JSON only, with this exact schema:
{
  "summary": "one concise Chinese sentence describing what the rule detected",
  "why_now": ["up to 3 factual observations directly grounded in supplied fields"],
  "confirmations": ["up to 3 observable conditions that would strengthen the research signal"],
  "invalidations": ["up to 3 observable conditions that would weaken the research signal"],
  "next_session_checklist": ["up to 3 neutral checks for the next session"],
  "risks": ["up to 3 risks present in the supplied fields or due to missing data"],
  "disclaimer": "固定使用：该分析仅供研究参考，不构成投资建议。"
}
"""
    return _request_json_analysis(system_prompt, signal_context)


def analyze_cross_market(context: dict) -> dict:
    """Coordinate stock and fund evidence without allowing the model to become a data source."""
    system_prompt = """You are the coordination layer for a personal stock-and-fund market research engine.
Use only the supplied normalized stock snapshot, fund market scan, and deterministic linkage output.
Never invent holdings, news, prices, returns, catalysts, or certainty. A style mapping is not a disclosed holding.
Do not provide buy, sell, hold, subscription, redemption, position-size, entry, exit, or guaranteed-return advice.
Explain cross-market resonance, divergence, missing evidence, and what should be verified next in concise Chinese.
Return valid JSON only, with this exact schema:
{
  "regime": "股基共振|股票偏强|基金偏强|同步偏弱|明显分化|中性观察",
  "summary": "one concise Chinese sentence",
  "stock_view": ["up to 3 observations grounded in stock data"],
  "fund_view": ["up to 3 observations grounded in fund data"],
  "linkages": [{"theme":"string", "state":"string", "evidence":"string"}],
  "divergences": ["up to 3 cross-market divergences or missing-evidence warnings"],
  "next_checks": ["up to 4 neutral checks for the next refresh/session"],
  "risks": ["up to 3 risks grounded in supplied data limitations"],
  "disclaimer": "固定使用：该分析仅供研究参考，不构成投资建议。"
}
"""
    return _request_json_analysis(system_prompt, context)


def analyze_allocation_reference(context: dict) -> dict:
    """Turn normalized sector facts into research-only decision reference cards."""
    system_prompt = """You are a cautious sector research assistant for a personal stock-and-fund analysis tool.
Use only the supplied normalized sector facts and cross-market linkage. Never invent valuation, flow, returns,
news, holdings, catalysts, certainty, or missing values. A status is a research priority, not a buy/sell order.
Do not give buy, sell, hold, subscription, redemption, position-size, entry, exit, or guaranteed-return advice.
Return valid JSON only, with this exact schema:
{
  "cards": [
    {
      "theme": "exact supplied sector name",
      "decision": "重点跟踪|逢低核对|持有观望|风险收敛|趋势观察",
      "analysis": "one concise Chinese sentence grounded in supplied facts",
      "risk": "one concise Chinese risk or missing-data note"
    }
  ]
}
Keep one card for each supplied sector and preserve the supplied order.
"""
    return _request_json_analysis(system_prompt, context)
