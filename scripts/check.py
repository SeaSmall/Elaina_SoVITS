# -*- coding: utf-8 -*-
"""启动前自检。

  退出码 0 = 没有 fail（warn 允许，会打印出来）
  退出码 1 = 有 fail，需要跑 wizard.py 补

结果同时写进 config/ready.json，`启动.bat` 用它决定「是否快进到正式启动」。
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src import config as cfgmod  # noqa: E402
from src.util import paths  # noqa: E402

OK, WARN, FAIL = "ok", "warn", "fail"
_MARK = {OK: "[ OK ]", WARN: "[WARN]", FAIL: "[FAIL]"}
_items = []


def add(level: str, name: str, detail: str = "") -> None:
    _items.append({"level": level, "name": name, "detail": detail})


def _run(exe: Path, args, timeout=25):
    try:
        p = subprocess.run(
            [str(exe)] + [str(a) for a in args],
            capture_output=True, timeout=timeout,
        )
        out = (p.stdout or b"").decode("utf-8", "replace").strip()
        err = (p.stderr or b"").decode("utf-8", "replace").strip()
        return p.returncode, out, err
    except subprocess.TimeoutExpired:
        return -9, "", f"超时 {timeout}s"
    except Exception as exc:
        return -1, "", str(exc)


def check_runtime(tag: str, exe: Path, need_tk: bool = False, deep: bool = False) -> None:
    if not exe.exists():
        add(FAIL, f"运行环境 {tag}", f"找不到 {paths.rel(exe)}")
        return
    rc, out, err = _run(exe, ["-c", "import sys;print(sys.version.split()[0])"])
    if rc != 0:
        add(FAIL, f"运行环境 {tag}", f"启动失败: {(err or out)[:200]}")
        return
    detail = out.splitlines()[-1] if out else "?"
    if need_tk:
        rc2, out2, err2 = _run(exe, ["-c", "import tkinter;print(tkinter.TkVersion)"])
        if rc2 != 0:
            add(FAIL, f"运行环境 {tag}", f"缺 tkinter（浮窗会崩）: {(err2 or out2)[:160]}")
            return
        detail += f" / tkinter {out2.splitlines()[-1]}"
    if deep:
        rc3, out3, err3 = _run(exe, ["-c", "import torch;print(torch.__version__, torch.cuda.is_available())"],
                               timeout=120)
        if rc3 != 0:
            add(FAIL, f"运行环境 {tag}", f"import torch 失败: {(err3 or out3)[:200]}")
            return
        detail += f" / torch {out3.splitlines()[-1]}"
    add(OK, f"运行环境 {tag}", detail)


def check_envdir(tag: str, d: Path) -> None:
    if not d.is_dir():
        add(FAIL, f"依赖目录 {tag}", f"缺少 {paths.rel(d)}")
        return
    n = sum(1 for _ in d.rglob("*") if _.is_file())
    if n == 0:
        add(FAIL, f"依赖目录 {tag}", "目录是空的")
        return
    add(OK, f"依赖目录 {tag}", f"{n} 个文件")


DOC_SUFFIX = {".txt", ".md", ".rst", ".json.bak", ".url"}


def real_files(d: Path) -> list[Path]:
    """目录里真正的内容文件 —— 排除我们放的「放模型说明.txt」这类文档。

    早先版本直接数文件数，结果只放了一个说明 txt 也报 OK，是假通过。
    """
    if not d.is_dir():
        return []
    out = []
    for f in d.rglob("*"):
        if not f.is_file():
            continue
        if f.suffix.lower() in DOC_SUFFIX and f.stat().st_size < 200_000:
            continue
        if f.name.startswith("."):
            continue
        out.append(f)
    return out


def check_model(tag: str, d: Path, required: bool) -> None:
    files = real_files(d)
    if not files:
        add(FAIL if required else WARN, f"模型 {tag}",
            f"{paths.rel(d)} 里还没有模型（只有说明文件）")
        return
    size = sum(f.stat().st_size for f in files)
    add(OK, f"模型 {tag}", f"{len(files)} 个文件 / {size / 2**20:.0f} MB")


def main() -> int:
    t0 = time.time()
    paths.ensure_dirs()

    # 1) 当前解释器
    add(OK, "自检解释器", f"Python {sys.version.split()[0]}")

    # 2) 内置运行时
    check_runtime("py312", paths.PY312, need_tk=True)
    check_runtime("py39", paths.PY39)

    # 3) 依赖注入目录
    check_envdir("sd_env", paths.SD_ENV)
    check_envdir("sv_env", paths.SV_ENV)

    # 4) 配置
    if not paths.CONFIG_FILE.exists():
        add(FAIL, "配置文件", "config.json 不存在（需要跑一次向导）")
    else:
        try:
            cfg = cfgmod.load()
        except Exception as exc:
            add(FAIL, "配置文件", f"解析失败: {exc}")
            cfg = None
        if cfg is not None:
            add(OK, "配置文件", paths.rel(paths.CONFIG_FILE))
            for lvl, field, msg in cfgmod.validate(cfg):
                add(lvl, f"配置项 {field}", msg)

    # 5) GPT-SoVITS 代码（模型一律可以稍后放）
    if paths.GPT_API.is_dir() and any(paths.GPT_API.iterdir()):
        add(OK, "GPT-SoVITS 代码", paths.rel(paths.GPT_API))
    else:
        add(FAIL, "GPT-SoVITS 代码", f"{paths.rel(paths.GPT_API)} 为空")
    wfiles = real_files(paths.GPT_WEIGHTS)
    if wfiles:
        add(OK, "GPT-SoVITS 权重",
            f"{len(wfiles)} 个文件 / {sum(f.stat().st_size for f in wfiles) / 2**20:.0f} MB")
    else:
        add(WARN, "GPT-SoVITS 权重", "为空 —— 需要自己放角色权重，否则 TTS 不出声")

    # 6) 模型（按用户决定，暂时都不放）
    check_model("asr", paths.MODEL_ASR, required=False)
    check_model("campplus", paths.MODEL_CAMPP, required=False)
    check_model("laya", paths.MODEL_LAYA, required=False)

    # 7) 声纹
    if paths.VOICEPRINT_FILE.exists():
        add(OK, "声纹", f"已录入 {paths.rel(paths.VOICEPRINT_FILE)}")
    else:
        add(WARN, "声纹", "未录入（可选，录声纹.bat）")

    # 8) 声卡安装包
    inst = list(paths.VENDOR.glob("*.exe")) if paths.VENDOR.is_dir() else []
    if inst:
        add(OK, "声卡安装包", ", ".join(p.name for p in inst))
    else:
        add(WARN, "声卡安装包", "vendor\\ 下没有安装包")

    # 9) 可写
    try:
        probe = paths.LOGS / ".write_probe"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink()
        add(OK, "目录可写", paths.rel(paths.LOGS))
    except Exception as exc:
        add(FAIL, "目录可写", f"{paths.rel(paths.LOGS)}: {exc}")

    # ---- 输出 ----
    fails = [i for i in _items if i["level"] == FAIL]
    warns = [i for i in _items if i["level"] == WARN]
    for it in _items:
        line = f"  {_MARK[it['level']]} {it['name']}"
        if it["detail"]:
            line += f"  —  {it['detail']}"
        print(line)

    ok = not fails
    print()
    print(f"  小计: OK {len(_items) - len(fails) - len(warns)} / WARN {len(warns)} / FAIL {len(fails)}"
          f"   用时 {time.time() - t0:.1f}s")
    if fails:
        print("  需要补的（向导会只问这些）:")
        for it in fails:
            print(f"    - {it['name']}: {it['detail']}")

    ready = {
        "checked_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "ok": ok,
        "counts": {"ok": len(_items) - len(fails) - len(warns), "warn": len(warns), "fail": len(fails)},
        "items": _items,
        "missing": [{"name": i["name"], "detail": i["detail"]} for i in fails],
    }
    try:
        paths.READY_FILE.write_text(
            json.dumps(ready, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as exc:
        print(f"  [WARN] ready.json 写入失败: {exc}")

    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
