# -*- coding: utf-8 -*-
"""项目路径中心。

规矩：整个项目里**只有这一个文件**允许出现绝对路径。
其它任何脚本一律 `from util.paths import ...`，这样打包换盘符才不会崩。

旧项目里散落的 12 处硬编码（各种 sd_env / 模型目录的绝对路径）
全部收编到这里。
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

# <项目根>\src\util\paths.py -> parents[2] == <项目根>
# 按自身位置反推，所以换盘符、换目录、改项目名都不需要改这里。
ROOT = Path(__file__).resolve().parents[2]

# ---------- 配置 ----------
CONFIG_DIR = ROOT / "config"
CONFIG_FILE = CONFIG_DIR / "config.json"
CONFIG_EXAMPLE = CONFIG_DIR / "config.example.json"
READY_FILE = CONFIG_DIR / "ready.json"

# ---------- 代码 ----------
SRC = ROOT / "src"
SCRIPTS = ROOT / "scripts"

# ---------- 内置运行时（免环境的核心）----------
RUNTIME = ROOT / "runtime"
PY39 = RUNTIME / "py39" / "python.exe"
PY312 = RUNTIME / "py312" / "python.exe"

# ---------- 依赖注入目录 ----------
ENVS = ROOT / "envs"
SD_ENV = ENVS / "sd_env"      # soundcard / sounddevice
SV_ENV = ENVS / "sv_env"      # funasr 1.1.18（asr_server 用）

# ---------- GPT-SoVITS ----------
GPT = ROOT / "gpt-sovits"
GPT_API = GPT / "api"
GPT_WEIGHTS = GPT / "weights"
GPT_W_GPT = GPT / "GPT_weights_v2ProPlus"
GPT_W_SOVITS = GPT / "SoVITS_weights_v2ProPlus"

# ---------- 模型 ----------
MODEL = ROOT / "model"
MODEL_ASR = MODEL / "asr"          # SenseVoice-Small
MODEL_CAMPP = MODEL / "campplus"   # CAM++ 声纹
MODEL_LAYA = MODEL / "laya"        # Laya 微调版（识图判断）
MODEL_TTS = MODEL / "tts"          # GPT-SoVITS 权重（用户自备）
MODEL_VLM = MODEL / "vlm"          # 本地识图（可选，默认空）

# ---------- 数据 ----------
DATA = ROOT / "data"
MEMORY_DIR = DATA / "memory"
CAPTURE_DIR = DATA / "captures"
VOICEPRINT_DIR = DATA / "voiceprint"
VOICEPRINT_FILE = VOICEPRINT_DIR / "voiceprint.npy"
VOICEPRINT_CFG = VOICEPRINT_DIR / "vpcfg.json"
HISTORY_FILE = MEMORY_DIR / "history.jsonl"
OVERLAY_FILE = DATA / "overlay.txt"
OVERLAY_HIDE = DATA / "overlay_hide"

# ---------- 其它 ----------
VENDOR = ROOT / "vendor"
LICENSES = ROOT / "licenses"
LOGS = ROOT / "logs"

# 需要保证存在的可写目录
_WRITABLE = (CONFIG_DIR, MEMORY_DIR, CAPTURE_DIR, VOICEPRINT_DIR, LOGS)


def ensure_dirs() -> None:
    """建好所有可写目录。幂等。"""
    for d in _WRITABLE:
        d.mkdir(parents=True, exist_ok=True)


def rel(p) -> str:
    """把绝对路径转成相对项目根，便于写日志。"""
    try:
        return str(Path(p).resolve().relative_to(ROOT))
    except Exception:
        return str(p)


def inject(env_dir: Path) -> bool:
    """把一个第三方依赖目录塞进 sys.path 最前面（本项目不用 venv，靠这个）。"""
    p = str(env_dir)
    if Path(p).is_dir() and p not in sys.path:
        sys.path.insert(0, p)
        return True
    return False


def inject_sd_env() -> bool:
    """soundcard / sounddevice。必须用它，PortAudio 打开 VoiceMeeter 会没声音。"""
    return inject(SD_ENV)


def inject_sv_env() -> bool:
    """funasr 1.1.18。runtime 自带的 1.0.27 与 SenseVoice checkpoint 不兼容。"""
    return inject(SV_ENV)


def child_env(extra: dict | None = None) -> dict:
    """给子进程用的环境变量：强制 UTF-8，且把 PYTHONPATH 指到对应依赖目录。"""
    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8:replace"
    env["PYTHONUTF8"] = "1"
    if extra:
        env.update({str(k): str(v) for k, v in extra.items()})
    return env
