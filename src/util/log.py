# -*- coding: utf-8 -*-
"""日志：控制台 + 文件双写。

编码铁律（旧项目踩过）：
  * 控制台只设 errors="replace"，**绝不**设 encoding="utf-8"
    （Windows 控制台是 GBK，硬设 utf-8 中文全糊）
  * 文件用 utf-8 显式写，方便事后查看
"""
from __future__ import annotations

import logging
import sys
from datetime import datetime
from typing import Optional

from . import paths

_FORMAT = "%(asctime)s %(levelname)-5s %(message)s"
_DATEFMT = "%H:%M:%S"
_configured = False


def _fix_console() -> None:
    """把 stdout/stderr 的编码错误策略改成 replace，避免 emoji/生僻字炸掉整行。"""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(errors="replace")  # type: ignore[attr-defined]
        except Exception:
            pass


def setup(tag: str = "main", level: int = logging.INFO,
          to_file: bool = True) -> logging.Logger:
    """初始化根 logger。tag 决定日志文件名。重复调用安全。"""
    global _configured
    _fix_console()

    root = logging.getLogger("elaina")
    if _configured:
        return root

    root.setLevel(level)
    root.handlers.clear()

    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(logging.Formatter(_FORMAT, _DATEFMT))
    root.addHandler(console)

    if to_file:
        try:
            paths.LOGS.mkdir(parents=True, exist_ok=True)
            fp = paths.LOGS / f"{tag}-{datetime.now():%Y%m%d}.log"
            fh = logging.FileHandler(fp, encoding="utf-8", errors="replace")
            fh.setFormatter(logging.Formatter(
                "%(asctime)s %(levelname)-5s [%(name)s:%(lineno)d] %(message)s",
                "%Y-%m-%d %H:%M:%S"))
            root.addHandler(fh)
        except Exception as exc:  # 磁盘满了也不该挡住主流程
            console.setFormatter(logging.Formatter(_FORMAT, _DATEFMT))
            root.warning("日志文件打开失败，仅输出到控制台: %s", exc)

    _configured = True
    return root


def get(name: str = "main") -> logging.Logger:
    return logging.getLogger(f"elaina.{name}")


def banner(log: Optional[logging.Logger], text: str) -> None:
    """打一条带框的分隔，方便在长日志里找轮次。"""
    log = log or get()
    line = "=" * 8
    log.info("%s %s %s", line, text, line)
