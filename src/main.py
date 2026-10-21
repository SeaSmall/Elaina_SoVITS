# -*- coding: utf-8 -*-
"""主入口（P1 阶段：纯文字链路已通，语音链路在 P2 接）。

用法：
    python src\\main.py                  # 交互式文字对话
    python src\\main.py --selftest       # 跑一次云端 LLM 自检，打印耗时
    python src\\main.py --once "你好"    # 只问一句就退出
    python src\\main.py --print-config   # 打印当前配置（key 打码）
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src import config as cfgmod  # noqa: E402
from src.llm import LLMError, factory  # noqa: E402
from src.util import log as logmod  # noqa: E402
from src.util import paths  # noqa: E402


def build_messages(cfg, history):
    msgs = [{"role": "system", "content": cfg["persona"]["system_prompt"]}]
    keep = max(2, int(cfg.get("history_turns") or 20)) * 2
    msgs.extend(history[-keep:])
    return msgs


def ask(client, cfg, history, user_text: str):
    """发一轮，返回 (asr_text, reply_text, seconds)。"""
    history.append({"role": "user", "content": user_text})
    t0 = time.time()
    try:
        reply = client.chat(build_messages(cfg, history))
    except Exception:
        history.pop()
        raise
    dt = time.time() - t0
    history.append({"role": "assistant", "content": reply})
    return user_text, reply, dt


def print_config(cfg) -> None:
    llm = cfg["llm"]
    print(f"  配置文件   : {paths.CONFIG_FILE}  (存在={paths.CONFIG_FILE.exists()})")
    print(f"  模式       : {cfg.get('mode')} / 语言={cfg.get('lang')}")
    print(f"  LLM        : provider={llm.get('provider')} model={llm.get('model')}")
    print(f"  LLM 地址   : {llm.get('base_url')}")
    print(f"  LLM key    : {cfgmod.mask(llm.get('api_key'))}")
    v = cfg["vision"]
    print(f"  识图       : mode={v.get('mode')} gate={v.get('gate')} model={v.get('model')}")
    print(f"  识图 key   : {cfgmod.mask(v.get('api_key'))}")
    print(f"  翻译       : enabled={cfg['translation'].get('enabled')}")
    print(f"  TTS        : enabled={cfg['tts'].get('enabled')} ref={cfg['tts'].get('ref_audio') or '(空)'}")
    print(f"  声纹       : enabled={cfg['voiceprint'].get('enabled')} "
          f"已录入={paths.VOICEPRINT_FILE.exists()}")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument("--selftest", action="store_true", help="跑一次云端调用自检")
    ap.add_argument("--once", default="", help="只问一句就退出")
    ap.add_argument("--print-config", action="store_true")
    args = ap.parse_args(argv)

    paths.ensure_dirs()
    log = logmod.setup("main")

    cfg = cfgmod.load()

    if args.print_config:
        print_config(cfg)
        return 0

    problems = cfgmod.validate(cfg)
    hard = [p for p in problems if p[0] == "fail"]
    for lvl, field, msg in problems:
        (log.error if lvl == "fail" else log.warning)("%-12s %s: %s", f"[{lvl}]", field, msg)
    if hard:
        log.error("配置有 %d 项必填缺失，请先运行 配置.bat（或 scripts\\wizard.py）", len(hard))
        return 2

    try:
        client = factory.build(cfg["llm"])
    except LLMError as exc:
        log.error("构造 LLM 客户端失败: %s", exc)
        return 2
    log.info("LLM 就绪: %s  %s  key=%s",
             cfg["llm"]["model"], client.endpoint, cfgmod.mask(cfg["llm"]["api_key"]))

    history: list = []

    if args.selftest:
        log.info("自检：向云端发一句话…")
        try:
            _, reply, dt = ask(client, cfg, history, "你好，用一句话打个招呼。")
        except Exception as exc:
            log.error("自检失败: %s", exc)
            return 3
        log.info("自检成功  %.2fs  回复: %s", dt, reply)
        return 0

    if args.once:
        try:
            _, reply, dt = ask(client, cfg, history, args.once)
        except Exception as exc:
            log.error("调用失败: %s", exc)
            return 3
        print(f"[{dt:.2f}s] {reply}")
        return 0

    print("=" * 60)
    print(" 文字对话模式（P1）。输入 /quit 退出，/reset 清空上下文。")
    print("=" * 60)
    while True:
        try:
            line = input("你说> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not line:
            continue
        if line in ("/quit", "/exit", "/q"):
            break
        if line == "/reset":
            history.clear()
            print("（上下文已清空）")
            continue
        try:
            _, reply, dt = ask(client, cfg, history, line)
        except Exception as exc:
            log.error("调用失败: %s", exc)
            continue
        print(f"AI({dt:.2f}s)> {reply}")

    log.info("退出。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
