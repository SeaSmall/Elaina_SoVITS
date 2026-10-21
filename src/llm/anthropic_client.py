# -*- coding: utf-8 -*-
"""Anthropic Messages 协议客户端。

MiMo 除了 OpenAI 兼容入口，还有一个 anthropic 入口：
    https://token-plan-cn.xiaomimimo.com/anthropic
它的路径是 /v1/messages，鉴权走 x-api-key（不是 Bearer）。
"""
from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional

from .openai_client import LLMError

ANTHROPIC_VERSION = "2023-06-01"


class AnthropicClient:
    def __init__(
        self,
        base_url: str,
        api_key: str,
        model: str,
        timeout: float = 60.0,
        temperature: float = 0.8,
        max_tokens: int = 800,
    ) -> None:
        self.base_url = (base_url or "").strip().rstrip("/")
        self.api_key = (api_key or "").strip()
        self.model = model
        self.timeout = float(timeout)
        self.temperature = float(temperature)
        self.max_tokens = int(max_tokens)

    @property
    def endpoint(self) -> str:
        if self.base_url.endswith("/messages"):
            return self.base_url
        return self.base_url + "/v1/messages"

    @staticmethod
    def _split_system(messages: List[Dict[str, Any]]):
        """Anthropic 的 system 是顶层字段，不在 messages 里。"""
        system_parts: List[str] = []
        rest: List[Dict[str, Any]] = []
        for m in messages:
            if m.get("role") == "system":
                c = m.get("content")
                if isinstance(c, str):
                    system_parts.append(c)
                elif isinstance(c, list):
                    system_parts.extend(
                        b.get("text", "") for b in c if isinstance(b, dict)
                    )
            else:
                rest.append(m)
        return ("\n\n".join(p for p in system_parts if p) or None), rest

    def _post(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "x-api-key": self.api_key,
            "anthropic-version": ANTHROPIC_VERSION,
            "User-Agent": "Elaina_SoVITS/0.1",
        }
        last_err: Optional[str] = None
        for attempt in range(3):
            req = urllib.request.Request(self.endpoint, data=data, headers=headers, method="POST")
            try:
                with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                    body = resp.read().decode("utf-8", "replace")
                return json.loads(body)
            except urllib.error.HTTPError as exc:
                detail = ""
                try:
                    detail = exc.read().decode("utf-8", "replace")[:600]
                except Exception:
                    pass
                last_err = f"HTTP {exc.code} {exc.reason} {detail}".strip()
                if exc.code != 429 and 400 <= exc.code < 500:
                    raise LLMError(last_err) from exc
            except urllib.error.URLError as exc:
                last_err = f"网络不可达: {exc.reason}"
            except TimeoutError:
                last_err = f"超时（>{self.timeout}s）"
            except json.JSONDecodeError as exc:
                raise LLMError(f"返回不是合法 JSON: {exc}") from exc
            if attempt < 2:
                time.sleep(1.2 * (attempt + 1))
        raise LLMError(last_err or "未知错误")

    def chat_raw(self, messages: List[Dict[str, Any]], **overrides: Any) -> Dict[str, Any]:
        system, rest = self._split_system(messages)
        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": rest,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
        }
        if system:
            payload["system"] = system
        payload.update(overrides or {})
        return self._post(payload)

    def chat(self, messages: List[Dict[str, Any]], **overrides: Any) -> str:
        data = self.chat_raw(messages, **overrides)
        blocks = data.get("content") or []
        parts: List[str] = []
        for b in blocks:
            if isinstance(b, dict) and b.get("type") == "text":
                parts.append(b.get("text") or "")
        text = "".join(parts).strip()
        if not text:
            raise LLMError(
                "Anthropic 返回正文为空："
                + json.dumps(data, ensure_ascii=False)[:400]
            )
        return text
