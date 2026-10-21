# -*- coding: utf-8 -*-
"""首次配置向导。

原则：**只问缺的那几项**。
  * 正常流程：启动.bat 先跑 check.py，有 fail 才进这里；
  * 这里读 config/ready.json 的 missing 列表，已经 OK 的项一律不再问；
  * `--force` 才逐项重问（配置.bat 用这个）。
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src import config as cfgmod  # noqa: E402
from src.llm import factory  # noqa: E402
from src.util import paths  # noqa: E402


def ask(prompt: str, default: str = "") -> str:
    tip = f" [{default}]" if default else ""
    try:
        v = input(f"{prompt}{tip}: ").strip()
    except EOFError:
        raise SystemExit("输入被中断，配置未保存。")
    return v or default


def ask_choice(prompt: str, options, default_idx: int = 1) -> int:
    print()
    print(prompt)
    for i, (desc, _key) in enumerate(options, 1):
        print(f"  {i}. {desc}")
    while True:
        raw = ask("请选择编号", str(default_idx))
        try:
            n = int(raw)
        except ValueError:
            print("  ! 请输入数字")
            continue
        if 1 <= n <= len(options):
            return n
        print("  ! 超出范围")


def main(argv=None) -> int:
    argv = list(argv or [])
    force = "--force" in argv

    paths.ensure_dirs()
    cfg = cfgmod.load()

    # 找出 check.py 报过的缺项
    missing = set()
    if not force and paths.READY_FILE.exists():
        try:
            import json
            ready = json.loads(paths.READY_FILE.read_text(encoding="utf-8"))
            for m in ready.get("missing") or []:
                missing.add(str(m.get("name", "")))
        except Exception:
            pass

    def need(field: str, human: str) -> bool:
        if force:
            return True
        if any(field in m for m in missing):
            return True
        return not str(cfgmod.get(cfg, field, "") or "").strip()

    print("=" * 64)
    print(" 首次配置向导 —— 只问缺的项，已配好的直接回车跳过")
    print("=" * 64)

    # ---------- 主 LLM ----------
    if need("llm.api_key", "主模型") or need("llm.model", "主模型"):
        n = ask_choice("主对话模型：", [
            ("DeepSeek（deepseek-chat）", "deepseek"),
            ("小米 MiMo（mimo-v2.6-flash）", "mimo"),
            ("其他 / 自建（任何 OpenAI 兼容服务）", "custom"),
        ], default_idx=1)
        provider = ["deepseek", "mimo", "custom"][n - 1]
        p = factory.preset(provider)
        cfgmod.set_(cfg, "llm.provider", provider)

        if provider == "custom":
            base = ask("接口地址（到 /v1 这一层，例 http://127.0.0.1:11434/v1）",
                       cfgmod.get(cfg, "llm.base_url", "") or "")
            cfgmod.set_(cfg, "llm.base_url", base)
        else:
            cfgmod.set_(cfg, "llm.base_url", p["base_url"])

        model = ask("模型名", cfgmod.get(cfg, "llm.model", "") if force else p["model"])
        cfgmod.set_(cfg, "llm.model", model)

        key = ask("API Key（只存本地 config.json，不会上传）",
                  cfgmod.get(cfg, "llm.api_key", "") if force else "")
        if key:
            cfgmod.set_(cfg, "llm.api_key", key)

    # ---------- 识图 ----------
    if need("vision.mode", "识图") or force:
        n = ask_choice("识图（看用户屏幕）：", [
            ("关闭", "off"),
            ("本地模型（需要自己放 model\\vlm）", "local"),
            ("小米 MiMo（mimo-v2.6-pro）", "cloud"),
            ("其他云端（OpenAI 兼容视觉）", "cloud"),
        ], default_idx=1)
        mode = ["off", "local", "cloud", "cloud"][n - 1]
        cfgmod.set_(cfg, "vision.mode", mode)
        if mode == "cloud":
            if n == 3:
                cfgmod.set_(cfg, "vision.provider", "mimo")
                cfgmod.set_(cfg, "vision.base_url", "https://token-plan-cn.xiaomimimo.com/v1")
                cfgmod.set_(cfg, "vision.model", "mimo-v2.6-pro")
            else:
                cfgmod.set_(cfg, "vision.base_url",
                            ask("视觉接口地址", cfgmod.get(cfg, "vision.base_url", "")))
                cfgmod.set_(cfg, "vision.model",
                            ask("视觉模型名", cfgmod.get(cfg, "vision.model", "")))
            if not str(cfgmod.get(cfg, "vision.api_key", "") or "").strip():
                reuse = ask("视觉模型是否复用主模型的 Key？(y/n)", "y").lower()
                if reuse.startswith("y"):
                    cfgmod.set_(cfg, "vision.api_key", cfgmod.get(cfg, "llm.api_key", ""))
                else:
                    cfgmod.set_(cfg, "vision.api_key", ask("视觉 API Key"))

    # ---------- TTS 参考音频 ----------
    if need("tts.ref_audio", "TTS"):
        print()
        print("TTS 需要一段 5~10 秒的参考音频（用谁的声音就用谁的）。")
        print("留空也可以，之后放进 config.json 的 tts.ref_audio 即可。")
        ref = ask("参考音频路径（.wav）", cfgmod.get(cfg, "tts.ref_audio", ""))
        if ref:
            cfgmod.set_(cfg, "tts.ref_audio", ref.replace("/", "\\"))
            ptxt = ask("参考音频对应的文字（逐字一致，留空则自动识别）",
                       cfgmod.get(cfg, "tts.prompt_text", ""))
            if ptxt:
                cfgmod.set_(cfg, "tts.prompt_text", ptxt)

    # ---------- 落地 ----------
    cfgmod.save(cfg)
    print()
    print(f"已保存: {paths.CONFIG_FILE}")
    print()
    print("下一步：")
    print("  1. 把模型放进 model\\asr、model\\campplus、model\\laya（看 README）")
    print("  2. 把角色权重放进 gpt-sovits\\weights")
    print("  3. 双击 启动.bat —— 自检通过后会直接进入对话")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
