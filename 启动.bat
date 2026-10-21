@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"
title Elaina_SoVITS

set "FORCE_WIZ=0"
set "EXTRA=%*"
if /i "%~1"=="--wizard"  set "FORCE_WIZ=1"
if /i "%~1"=="--reconfig" set "FORCE_WIZ=1"
if "%FORCE_WIZ%"=="1" set "EXTRA="

REM ---------- 选解释器：优先用项目内置的，退而求其次用系统的 ----------
set "PY=%~dp0runtime\py312\python.exe"
if exist "%PY%" goto :has_py
where python >nul 2>nul
if errorlevel 1 (
  echo [FAIL] 没有找到 Python。
  echo        正常情况应该自带 runtime\py312\python.exe，说明这个包不完整。
  pause
  exit /b 1
)
set "PY=python"
:has_py

REM ---------- 1) 自检；全绿就快进 ----------
if "%FORCE_WIZ%"=="1" goto :wizard

echo [*] 自检中...
"%PY%" "%~dp0scripts\check.py"
if errorlevel 1 goto :wizard
goto :launch

REM ---------- 2) 只补缺的 ----------
:wizard
echo.
echo [*] 有未完成的配置或组件，进入向导。已经配好的项会直接跳过。
if "%FORCE_WIZ%"=="1" (
  "%PY%" "%~dp0scripts\wizard.py" --force
) else (
  "%PY%" "%~dp0scripts\wizard.py"
)
if errorlevel 1 (
  echo.
  echo [FAIL] 向导没有正常完成，已停止启动。
  pause
  exit /b 1
)

echo.
echo [*] 重新自检...
"%PY%" "%~dp0scripts\check.py"
if errorlevel 1 (
  echo.
  echo [FAIL] 自检仍有未通过项，已停止启动。上面 [FAIL] 那几行就是还缺什么。
  pause
  exit /b 1
)

REM ---------- 3) 正式启动 ----------
:launch
echo.
echo ============================================================
echo   自检通过，直接启动
echo ============================================================
"%PY%" "%~dp0src\main.py" %EXTRA%
set "RC=%ERRORLEVEL%"
echo.
echo 程序已退出，退出码 %RC%
pause
exit /b %RC%
