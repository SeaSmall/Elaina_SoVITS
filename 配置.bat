@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"
title Elaina_SoVITS - 配置

set "PY=%~dp0runtime\py312\python.exe"
if exist "%PY%" goto :has_py
where python >nul 2>nul
if errorlevel 1 (
  echo [FAIL] 找不到 Python。
  pause
  exit /b 1
)
set "PY=python"
:has_py

echo 逐项重新配置（已有值会作为默认值，直接回车保留）
echo.
"%PY%" "%~dp0scripts\wizard.py" --force
echo.
echo [*] 重新自检...
"%PY%" "%~dp0scripts\check.py"
pause
