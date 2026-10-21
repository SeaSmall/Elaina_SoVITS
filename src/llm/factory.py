# -*- coding: utf-8 -*-
"""按配置造客户端。全项目只从这里拿 LLM，别的地方不要 new。"""
from __future__ import annotations

from typing import Any, Dict, Optional

from .anthropic_client import AnthropicClient
from .openai_client import LLMError, OpenAICompatibleClient

# provider 预设。base_url 一律填到 /v1 这一层，客户端自己补 /chat/completions。
PRESETS: Dict[str, Dict[str, str]] = {
    "deepseek": {
        "base_url": "https://api.deepseek.com/v1",
        "model": "deepseek-chat",
        "protocol": "openai",
        "note": "官方 OpenAI 兼容入口",
    },
    "mimo": {
        "base_url": "https://token-plan-cn.xiaomimimo.com/v1",
        "model": "mimo-v2.6-flash",
        "protocol": "openai",
        "note": "小米 MiMo token-plan 入口（OpenAI 兼容）",
    },
    "mimo-anthropic": {
        "base_url": "https://token-plan-cn.xiaomimimo.com/anthropic",
        "model": "mimo-v2.6-flash",
        "protocol": "anthropic",
        "note": "同一个 MiMo 的 Anthropic 入口",
    },
    "custom": {
        "base_url": "",
        "model": "",
        "protocol": "openai",
        "note": "任何 OpenAI 兼容服务（ollama / vllm / one-api / 官方）",
    },
}


def preset(provider: str) -> Dict[str, str]:
    return dict(PRESETS.get(provider or "custom", PRESETS["custom"]))


def provider_names():
    return list(PRESETS.keys())


def build(cfg_llm: Dict[str, Any]) -> Any:
    """按 config['llm'] 造客户端。缺字段抛 LLMError（check.py 会先拦）。"""
    c = dict(cfg_llm or {})
    provider = c.get("provider") or "custom"
    p = preset(provider)

    base_url = (c.get("base_url") or p["base_url"] or "").strip()
    model = (c.get("model") or p["model"] or "").strip()
    api_key = (c.get("api_key") or "").strip()

    if not base_url:
        raise LLMError(f"provider={provider} 没配 base_url")
    if not model:
        raise LLMError(f"provider={provider} 没配 model")
    if not api_key:
        raise LLMError(f"provider={provider} 没配 api_key")

    protocol = p["protocol"]
    common = dict(
        base_url=base_url,
        api_key=api_key,
        model=model,
        timeout=float(c.get("timeout", 60) or 60),
        temperature=float(c.get("temperature", 0.8) or 0.8),
        max_tokens=int(c.get("max_tokens", 800) or 800),
    )
    if protocol == "anthropic":
        return AnthropicClient(**common)
    return OpenAICompatibleClient(**common)


def build_translator(cfg: Dict[str, Any]) -> Optional[Any]:
    """翻译用的客户端：默认复用主 LLM，配置了独立 provider 就用独立的。"""
    tr = cfg.get("translation") or {}
    if not tr.get("enabled"):
        return None
    if tr.get("use_main_llm", True) or not (tr.get("api_key") or "").strip():
        return build(cfg.get("llm") or {})
    merged = dict(cfg.get("llm") or {})
    for k in ("provider", "base_url", "api_key", "model"):
        if str(tr.get(k) or "").strip():
            merged[k] = tr[k]
    return build(merged)
