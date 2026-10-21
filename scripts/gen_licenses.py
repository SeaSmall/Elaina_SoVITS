# -*- coding: utf-8 -*-
"""生成 licenses/THIRD_PARTY_LICENSES.md。

扫所有内置依赖目录里的 dist-info / egg-info，抽名字、版本、许可字段，
再把能找到的 LICENSE 文件原文附在后面。

打包前重跑一次：runtime\\py312\\python.exe scripts\\gen_licenses.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.util import paths  # noqa: E402

SCAN_DIRS = [
    paths.RUNTIME / "py312" / "Lib" / "site-packages",
    paths.ENVS / "sv_env",
    paths.ENVS / "sd_env",
    paths.GPT_API,
]
OUT = paths.LICENSES / "THIRD_PARTY_LICENSES.md"

_LIC_RE = re.compile(r"(LICENSE|LICENCE|COPYING|NOTICE)(\.(txt|md|rst|apache2)?)?$", re.I)
_MAX_LICENSE_CHARS = 1200          # 每个包最多摘这么多，避免文件爆炸
_MAX_PKG_LICENSE = 200             # 许可文本摘录上限（去换行后）


def _field(meta_text: str, name: str) -> str:
    m = re.search(rf"^{re.escape(name)}:\s*(.+)$", meta_text, re.M | re.I)
    return m.group(1).strip() if m else ""


def _read(p: Path, limit: int = 400_000) -> str:
    try:
        with open(p, "r", encoding="utf-8", errors="replace") as f:
            return f.read(limit)
    except Exception:
        return ""


def _find_license_file(pkg_dir: Path) -> Path | None:
    try:
        for c in sorted(pkg_dir.iterdir()):
            if c.is_file() and _LIC_RE.search(c.name):
                return c
    except Exception:
        return None
    return None


def collect() -> list[dict]:
    seen = {}
    for root in SCAN_DIRS:
        if not root.is_dir():
            continue
        for info in root.rglob("*.dist-info"):
            meta = info / "METADATA"
            if not meta.is_file():
                continue
            txt = _read(meta, 200_000)
            name = _field(txt, "Name") or info.parent.name
            ver = _field(txt, "Version")
            lic = _field(txt, "License-Expression") or _field(txt, "License")
            if not lic:
                m = re.search(r"^\s*Classifier:\s*License\s*::\s*(.+)$", txt, re.M)
                lic = m.group(1).strip() if m else ""
            key = (name.lower(), ver)
            if key in seen:
                continue
            lf = _find_license_file(info) or _find_license_file(info.parent / name)
            snippet = ""
            if lf:
                snippet = re.sub(r"\s+", " ", _read(lf)).strip()[: _MAX_PKG_LICENSE]
            seen[key] = {
                "name": name,
                "version": ver,
                "license": lic or "(未声明)",
                "license_file": lf.name if lf else "",
                "snippet": snippet,
                "source": paths.rel(info),
            }
    return sorted(seen.values(), key=lambda d: d["name"].lower())


def write(pkgs: list[dict]) -> None:
    lines = [
        "# 第三方 Python 包许可汇总",
        "",
        "> 本文件由 `scripts/gen_licenses.py` 自动生成，**请勿手改**。",
        f"> 扫描范围：{', '.join(paths.rel(d) for d in SCAN_DIRS if d.is_dir())}",
        f"> 包数量：**{len(pkgs)}**",
        "",
        "## 总览",
        "",
        "| 包 | 版本 | 许可 | LICENSE 文件 |",
        "|---|---|---|---|",
    ]
    for p in pkgs:
        lic = p["license"].replace("|", "\\|")
        lines.append(f"| {p['name']} | {p['version']} | {lic} | {p['license_file']} |")

    lines += ["", "---", "", "## 许可原文摘录", ""]
    for p in pkgs:
        lines.append(f"### {p['name']} {p['version']}")
        lines.append("")
        lines.append(f"- 许可：{p['license']}")
        if p["license_file"]:
            lines.append(f"- 许可文件：`{p['license_file']}`（{p['source']}）")
        if p["snippet"]:
            lines.append("")
            lines.append("```text")
            lines.append(p["snippet"])
            lines.append("```")
        lines.append("")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"已写入 {paths.rel(OUT)}  共 {len(pkgs)} 个包")


def main() -> int:
    present = [d for d in SCAN_DIRS if d.is_dir()]
    if not present:
        print("没有任何依赖目录存在，先构建 runtime\\py312 再跑。")
        return 1
    write(collect())
    return 0


if __name__ == "__main__":
    sys.exit(main())
