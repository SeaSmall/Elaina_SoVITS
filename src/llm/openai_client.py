# -*- coding: utf-8 -*-
"""OpenAI 兼容协议的对话客户端。

为什么不用 requests：本项目要减少依赖、避免 runtime 里装不上；
只用标准库 urllib 就够，且启动快。
"""
from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional


class LLMError(RuntimeError):
    """调用大模型失败。message 里带的是可读原因，不吞细节。"""


class OpenAICompatibleClient:
    def __init__(
        self,
        base_url: str,
        api_key: str,
        model: str,
        timeout: float = 60.0,
        temperature: float = 0.8,
        max_tokens: int = 800,
        extra_headers: Optional[Dict[str, str]] = None,
    ) -> None:
        self.base_url = (base_url or "").strip().rstrip("/")
        self.api_key = (api_key or "").strip()
        self.model = model
        self.timeout = float(timeout)
        self.temperature = float(temperature)
        self.max_tokens = int(max_tokens)
        self.extra_headers = dict(extra_headers or {})

    # ---------- 地址 ----------
    @property
    def endpoint(self) -> str:
        """base_url 可以给到 /v1，也可以直接给完整的 /chat/completions。"""
        if self.base_url.endswith("/chat/completions"):
            return self.base_url
        return self.base_url + "/chat/completions"

    # ---------- 底层 ----------
    def _post(self, payload: Dict[str, Any], timeout: Optional[float] = None) -> Dict[str, Any]:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": f"Bearer {self.api_key}",
            "User-Agent": "Elaina_SoVITS/0.1",
        }
        headers.update(self.extra_headers)

        last_err: Optional[str] = None
        for attempt in range(3):
            req = urllib.request.Request(self.endpoint, data=data, headers=headers, method="POST")
            try:
                with urllib.request.urlopen(req, timeout=timeout or self.timeout) as resp:
                    body = resp.read().decode("utf-8", "replace")
                return json.loads(body)
            except urllib.error.HTTPError as exc:
                detail = ""
                try:
                    detail = exc.read().decode("utf-8", "replace")[:600]
                except Exception:
                    pass
                last_err = f"HTTP {exc.code} {exc.reason} {detail}".strip()
                # 4xx 里只有 429 值得重试
                if exc.code != 429 and 400 <= exc.code < 500:
                    raise LLMError(last_err) from exc
            except urllib.error.URLError as exc:
                last_err = f"网络不可达: {exc.reason}"
            except TimeoutError:
                last_err = f"超时（>{timeout or self.timeout}s）"
            except json.JSONDecodeError as exc:
                raise LLMError(f"返回不是合法 JSON: {exc}") from exc
            if attempt < 2:
                time.sleep(1.2 * (attempt + 1))

        raise LLMError(last_err or "未知错误")

    def chat_raw(self, messages: List[Dict[str, Any]], **overrides: Any) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "stream": False,
        }
        payload.update(overrides or {})
        return self._post(payload)

    # ---------- 上层 ----------
    def chat(self, messages: List[Dict[str, Any]], **overrides: Any) -> str:
        data = self.chat_raw(messages, **overrides)
        return self._pick_text(data)

    @staticmethod
    def _pick_text(data: Dict[str, Any]) -> str:
        """取回复正文。

        旧项目的坑：视觉模型关掉推理后偶尔 content 为空、内容全在
        reasoning_content 里；这里做兜底，避免整轮没话说。
        """
        choices = data.get("choices") or []
        if not choices:
            err = data.get("error")
            if err:
                raise LLMError(f"接口返回错误: {err}")
            raise LLMError(f"返回里没有 choices: {json.dumps(data, ensure_ascii=False)[:400]}")
        msg = choices[0].get("message") or {}
        text = (msg.get("content") or "").strip()
        if not text:
            text = (msg.get("reasoning_content") or "").strip()
        if not text:
            raise LLMError(
                f"模型回复为空（finish_reason={choices[0].get('finish_reason')}）。"
                "可能是 max_tokens 太小或触发了内容过滤。"
            )
        return text

    # ---------- 多模态 ----------
    @staticmethod
    def image_part(data_url: str) -> Dict[str, Any]:
        return {"type": "image_url", "image_url": {"url": data_url}}

    @staticmethod
    def data_url(jpeg_bytes: bytes) -> str:
        import base64
        return "data:image/jpeg;base64," + base64.b64encode(jpeg_bytes).decode("ascii")
