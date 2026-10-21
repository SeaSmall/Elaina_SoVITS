<#
    setup_runtime.ps1 —— 补齐"免环境"运行时（仅源码部署需要）
    ------------------------------------------------------------------
    在有 Release 完整包的情况下**不需要跑这个**：完整包里 runtime\ 已经装好了。

    这个脚本会做：
      1. 把 Python 3.12 装到 runtime\py312（免管理员，per-user 安装）
      2. 装 torch 2.7.1+cu118 及其依赖（CUDA 11.8 版，N 卡加速用）
      3. 把 Python 3.9.13 装到 runtime\py39，装 torch 2.0.0+cu118
      4. 建 envs\sd_env（soundcard）和 envs\sv_env（funasr 1.1.18，隔离安装）

    用法：
        powershell -NoProfile -ExecutionPolicy Bypass -File scripts\setup_runtime.ps1

    可选参数：
        -CpuOnly        装 CPU 版 torch（没有 N 卡时用，包小 1/3）
        -SkipPy39       不装 py39（不用变声时）
        -Force          已存在也重装

    国内加速（可选，先设环境变量再跑）：
        $env:PIP_INDEX_URL='https://pypi.tuna.tsinghua.edu.cn/simple'
#>
[CmdletBinding()]
param(
    [switch]$CpuOnly,
    [switch]$SkipPy39,
    [switch]$Force
)

$ErrorActionPreference = 'Stop'
$ProgressPreference    = 'SilentlyContinue'

$ROOT    = Split-Path -Parent $PSScriptRoot
$RUNTIME = Join-Path $ROOT 'runtime'
$ENVS    = Join-Path $ROOT 'envs'
$TMP     = Join-Path $env:TEMP 'elaina_setup'

$PY312_TARGET = Join-Path $RUNTIME 'py312'
$PY39_TARGET  = Join-Path $RUNTIME 'py39'

$PY312_VER = '3.12.7'
$PY39_VER  = '3.9.13'

# 镜像下载点（python.org 国内慢，走镜像；镜像挂了自动回落官方）
$PY_MIRRORS = @(
    "https://mirrors.huaweicloud.com/python/{0}/python-{0}-amd64.exe",
    "https://www.python.org/ftp/python/{0}/python-{0}-amd64.exe"
)

$TORCH_INDEX = if ($CpuOnly) { 'https://download.pytorch.org/whl/cpu' } else { 'https://download.pytorch.org/whl/cu118' }

function Say($msg, $color = 'Gray') { Write-Host $msg -ForegroundColor $color }
function Step($n, $msg) { Write-Host ""; Write-Host "[$n] $msg" -ForegroundColor Cyan }
function Ok($msg)   { Write-Host "    OK   $msg" -ForegroundColor Green }
function Warn($msg) { Write-Host "    WARN $msg" -ForegroundColor Yellow }
function Die($msg)  { Write-Host "    FAIL $msg" -ForegroundColor Red; exit 1 }

function New-Dir($p) { if (-not (Test-Path $p)) { New-Item -ItemType Directory -Path $p -Force | Out-Null } }

function Get-File($urls, $dst) {
    foreach ($u in $urls) {
        try {
            Say "    下载 $u"
            Invoke-WebRequest -Uri $u -OutFile $dst -UseBasicParsing -TimeoutSec 1800
            if ((Test-Path $dst) -and (Get-Item $dst).Length -gt 1MB) { return $true }
        } catch {
            Warn "这个地址失败：$($_.Exception.Message)"
        }
    }
    return $false
}

function Install-Python($ver, $target, $label) {
    $exe = Join-Path $target 'python.exe'
    if ((Test-Path $exe) -and (-not $Force)) {
        $v = & $exe -c "import sys;print(sys.version.split()[0])" 2>$null
        Ok "$label 已存在（Python $v），跳过"
        return $true
    }
    New-Dir $RUNTIME
    $setup = Join-Path $TMP "python-$ver-amd64.exe"
    if (-not (Test-Path $setup)) {
        $urls = $PY_MIRRORS | ForEach-Object { $_ -f $ver }
        if (-not (Get-File $urls $setup)) { Die "Python $ver 安装包下载失败，请手动下载后放到 $setup 再重跑" }
    }
    Say "    静默安装 $label 到 $target（约 1~3 分钟）"
    $args = @(
        '/quiet',
        'InstallAllUsers=0',
        "TargetDir=$target",
        'Include_launcher=0',
        'Include_test=0',
        'Include_pip=1',
        'Include_tcltk=1',
        'Include_doc=0',
        'AssociateFiles=0',
        'Shortcuts=0',
        'PrependPath=0'
    )
    $p = Start-Process -FilePath $setup -ArgumentList $args -Wait -PassThru
    if (-not (Test-Path $exe)) { Die "$label 安装失败（exit $($p.ExitCode)），检查是否有权限限制" }
    $v = & $exe -c "import sys;print(sys.version.split()[0])" 2>$null
    Ok "$label 装好（$v）"
    return $true
}

function Pip($py, $pkgs, $extraArgs = @()) {
    $a = @('-m', 'pip', 'install', '--no-warn-script-location', '--disable-pip-version-check') + $extraArgs + $pkgs
    & $py @a
    if ($LASTEXITCODE -ne 0) { Die "pip 安装失败：$($pkgs -join ' ')" }
}

# ============================================================
Step 1 '环境检查'
# ============================================================
New-Dir $RUNTIME
New-Dir $ENVS
New-Dir $TMP

$free = (Get-PSDrive -Name ((Split-Path $ROOT -Qualifier).TrimEnd(':')) -EA 0).Free
if ($free) {
    $needGB = if ($SkipPy39) { 8 } else { 15 }
    $freeGB = [math]::Round($free / 1GB, 1)
    Say "    目标盘剩余空间 ${freeGB} GB，需要约 ${needGB} GB"
    if ($freeGB -lt $needGB) { Die "空间不够，至少需要 ${needGB} GB" }
}
Say "    项目根目录：$ROOT"
Say "    torch 版本：$(if ($CpuOnly) { 'CPU 版' } else { 'CUDA 11.8 版' })"

# ============================================================
Step 2 "Python $PY312_VER → runtime\py312"
# ============================================================
Install-Python $PY312_VER $PY312_TARGET 'py312' | Out-Null
$PY312 = Join-Path $PY312_TARGET 'python.exe'

Say '    升级 pip / 装 wheel'
& $PY312 -m pip install --upgrade pip wheel --disable-pip-version-check --no-warn-script-location | Out-Null

Step 3 '安装 torch（这一步最慢，几个 GB）'
Say "    索引：$TORCH_INDEX"
Pip $PY312 @('torch==2.7.1') @('-i', $TORCH_INDEX)
Pip $PY312 @('numpy', 'pillow', 'soundfile', 'dxcam', 'comtypes', 'transformers', 'safetensors', 'huggingface_hub')
Say '    装 laya（识图判断模型）'
try {
    Pip $PY312 @('laya')
} catch {
    Warn 'laya 装失败，识图 gate=auto 不可用；可以先用 gate=always 或 never'
}

Step 4 '验证 py312'
$chk = & $PY312 -c "import torch, numpy, PIL; print('torch', torch.__version__); print('cuda', torch.cuda.is_available())" 2>&1
Say $chk
if ($chk -match 'True') { Ok 'GPU 可用' } else { Warn 'GPU 不可用，TTS 和识图会慢；检查 NVIDIA 驱动' }

# ============================================================
if (-not $SkipPy39) {
    Step 5 "Python $PY39_VER → runtime\py39（变声用）"
    Install-Python $PY39_VER $PY39_TARGET 'py39' | Out-Null
    $PY39 = Join-Path $PY39_TARGET 'python.exe'

    & $PY39 -m pip install --upgrade pip wheel --disable-pip-version-check | Out-Null
    Step 6 '安装 py39 的 torch 2.0.0'
    Pip $PY39 @('torch==2.0.0+cu118') @('-i', 'https://download.pytorch.org/whl/cu118')
    Pip $PY39 @('numpy<2', 'soundfile', 'pydub', 'ffmpeg-python')

    $req = Join-Path $ROOT 'gpt-sovits\api\requirements.txt'
    if (Test-Path $req) {
        Say '    按 gpt-sovits\api\requirements.txt 装依赖'
        & $PY39 -m pip install -r $req --disable-pip-version-check
        if ($LASTEXITCODE -ne 0) { Warn 'requirements.txt 有部分包失败，不影响纯推理时可以先不管' }
    } else {
        Warn '还没放 GPT-SoVITS 代码，先跳过它的依赖；放好代码后重跑本脚本'
    }
} else {
    Step 5 '跳过 py39（-SkipPy39）'
}

Step 7 '建 envs\sd_env（soundcard 音频库）'
$sd = Join-Path $ENVS 'sd_env'
New-Dir $sd
& $PY312 -m pip install --target $sd --upgrade --no-warn-script-location soundcard sounddevice | Out-Null
if (Test-Path (Join-Path $sd 'soundcard')) { Ok 'sd_env 就绪' } else { Die 'sd_env 建失败' }

Step 8 '建 envs\sv_env（funasr 1.1.18，隔离安装）'
$sv = Join-Path $ENVS 'sv_env'
New-Dir $sv
# --no-deps：funasr 会拖一堆训练用的重依赖，纯推理只要核心几个
& $PY39 -m pip install --target $sv --no-deps --no-warn-script-location funasr==1.1.18
if ($LASTEXITCODE -ne 0) { Warn 'funasr 装失败，语音识别不可用（译：只能打字聊天）' }
else { Ok 'sv_env 就绪' }

# ============================================================
Step 9 '汇总'
Write-Host ""
Say '运行时已就绪，接下来：'
Say '  1) 跑 scripts\setup_gpt_sovits.ps1 拉 GPT-SoVITS 代码（不用变声可跳过）'
Say '  2) 按 docs\安装与配置.md 第 4 节放模型'
Say '  3) 双击 启动.bat'
Write-Host ""
Say '自检命令：' -ForegroundColor Cyan
Say "  `"$PY312`" scripts\check.py"
