# -*- coding: utf-8 -*-
"""配置读写 + 校验。

设计原则：
  * `config/config.json` 是**用户私有**的（含 key），首次运行时由 wizard.py 生成，
    不进版本库、不随包分发。
  * `config/config.example.json` 是**公开模板**（key 全空），随包分发。
  * 所有缺省值集中在 DEFAULTS，读的时候做深合并，所以模板可以只写想改的字段。
"""
from __future__ import annotations

import copy
import json
from typing import Any, Dict, List, Tuple

from .util import paths

DEFAULT_SYSTEM_PROMPT = (
    "你是一个住在用户电脑里的 AI 伙伴，说话自然、口语化，像真人聊天。\n"
    "规则：\n"
    "1. 用中文（或用户当前使用的语言）口语回答，不要用书面语长句。\n"
    "2. 一般一到三句话就够，除非用户明确要求详细解释。\n"
    "3. 不知道就说不知道，不要编。\n"
    "4. 不要输出 markdown、列表符号、括号注释，输出的是会被念出来的话。\n"
    "（把这段换成你想要的任何人格设定。）"
)

DEFAULTS: Dict[str, Any] = {
    "version": 1,
    # local = 本机麦克风/扬声器；qq = 拨打电话场景
    "mode": "local",
    # 对话语言：zh / ja
    "lang": "zh",
    "persona": {
        "name": "Elaina",
        "system_prompt": DEFAULT_SYSTEM_PROMPT,
    },
    "llm": {
        "provider": "deepseek",          # deepseek | mimo | custom
        "base_url": "https://api.deepseek.com/v1",
        "api_key": "",
        "model": "deepseek-chat",
        "temperature": 0.8,
        "max_tokens": 800,
        "timeout": 60,
    },
    # 中→日翻译。默认复用主 LLM（不开则直接用主 LLM 的 key）。
    "translation": {
        "enabled": False,
        "use_main_llm": True,
        "provider": "",
        "base_url": "",
        "api_key": "",
        "model": "",
        "target_lang": "ja",
    },
    # 识图。mode: off | cloud | local；gate: auto(Laya 判断) | always | never
    "vision": {
        "mode": "off",
        "gate": "auto",
        "provider": "mimo",
        "base_url": "https://token-plan-cn.xiaomimimo.com/v1",
        "api_key": "",
        "model": "mimo-v2.6-pro",
        "reasoning_effort": "none",
        "max_width": 1920,
        "max_tokens": 4000,
    },
    "asr": {
        "mode": "local",                 # local(9881) | cloud
        "url": "http://127.0.0.1:9881",
        "lang": "auto",
    },
    "tts": {
        "enabled": True,
        "url": "http://127.0.0.1:9880",
        "ref_audio": "",                 # 用户自备参考音频（不发包）
        "prompt_text": "",
        "prompt_lang": "zh",
        "text_lang": "zh",
    },
    "voiceprint": {
        "enabled": False,
        "threshold": 0.35,
    },
    "audio": {
        "input": "",                     # 设备名或索引，wizard 枚举后填
        "output": "",
    },
    "history_turns": 20,
}

# 必填（空字符串即视为缺失）
REQUIRED = (
    "llm.base_url",
    "llm.api_key",
    "llm.model",
)


def _deep_merge(base: Dict[str, Any], over: Dict[str, Any]) -> Dict[str, Any]:
    out = copy.deepcopy(base)
    for k, v in (over or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = v
    return out


def defaults() -> Dict[str, Any]:
    return copy.deepcopy(DEFAULTS)


def load(path=None) -> Dict[str, Any]:
    """读 config.json；不存在则返回纯默认值（不抛异常，由 check.py 报红）。"""
    p = paths.CONFIG_FILE if path is None else path
    raw: Dict[str, Any] = {}
    try:
        with open(p, "r", encoding="utf-8") as f:
            raw = json.load(f) or {}
    except FileNotFoundError:
        raw = {}
    except Exception:
        raise
    return _deep_merge(DEFAULTS, raw)


def save(cfg: Dict[str, Any], path=None) -> None:
    p = paths.CONFIG_FILE if path is None else path
    paths.CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    tmp = str(p) + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)
    import os
    os.replace(tmp, p)


def get(cfg: Dict[str, Any], dotted: str, default=None):
    cur: Any = cfg
    for part in dotted.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return default
        cur = cur[part]
    return cur


def set_(cfg: Dict[str, Any], dotted: str, value) -> None:
    parts = dotted.split(".")
    cur = cfg
    for part in parts[:-1]:
        cur = cur.setdefault(part, {})
    cur[parts[-1]] = value


def validate(cfg: Dict[str, Any]) -> List[Tuple[str, str, str]]:
    """返回 [(level, field, message)]，level ∈ fail / warn。

    fail = 挡住了跑不起来，必须让 wizard 补。
    warn = 能跑但功能会缺（比如没放模型）。
    """
    out: List[Tuple[str, str, str]] = []
    for dotted in REQUIRED:
        if not str(get(cfg, dotted, "") or "").strip():
            out.append(("fail", dotted, "必填项为空"))

    base = str(get(cfg, "llm.base_url", "") or "")
    if base and not (base.startswith("http://") or base.startswith("https://")):
        out.append(("fail", "llm.base_url", "必须以 http:// 或 https:// 开头"))

    mode = get(cfg, "vision.mode", "off")
    if mode == "cloud":
        if not str(get(cfg, "vision.base_url", "") or "").strip():
            out.append(("fail", "vision.base_url", "识图=云端但没填地址"))
        if not str(get(cfg, "vision.api_key", "") or "").strip():
            out.append(("fail", "vision.api_key", "识图=云端但没填 key"))
        if not str(get(cfg, "vision.model", "") or "").strip():
            out.append(("fail", "vision.model", "识图=云端但没填模型"))

    if get(cfg, "tts.enabled", True) and not str(get(cfg, "tts.ref_audio", "") or "").strip():
        out.append(("warn", "tts.ref_audio", "参考音频为空，TTS 无法出声"))

    if get(cfg, "voiceprint.enabled", False) and not paths.VOICEPRINT_FILE.exists():
        out.append(("warn", "voiceprint.enabled", "开了声纹校验但还没录声纹"))
    if get(cfg, "voiceprint.enabled", False) and not paths.VOICEPRINT_CFG.exists():
        out.append(("warn", "voiceprint.threshold", "还没标定阈值（vpcfg.json 不存在）"))

    return out


def mask(secret: str) -> str:
    """日志里显示 key 用。"""
    s = str(secret or "")
    if not s:
        return "(空)"
    if len(s) <= 8:
        return s[:2] + "***"
    return f"{s[:4]}***{s[-3:]}"
