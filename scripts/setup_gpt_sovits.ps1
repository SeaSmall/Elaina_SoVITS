<#
    setup_gpt_sovits.ps1 —— 拉取 GPT-SoVITS 推理代码到 gpt-sovits\api
    ------------------------------------------------------------------
    只需要跑一次。已有 Release 完整包时不需要跑（代码已在包里）。

    做的事：
      1. git clone 上游 GPT-SoVITS（浅克隆，约 300 MB）
      2. 把推理需要的部分拷到 gpt-sovits\api\：
           api_v2.py / config.py / LICENSE / requirements.txt / extra-req.txt
           GPT_SoVITS\   ← 排除 pretrained_models（几 GB 基座权重，要单独下）
           tools\i18n\   ← api_v2.py 唯一用到的 tools 子目录（0.3 MB）
      3. 提示你下一步去下哪些基座权重

    用法：
        powershell -NoProfile -ExecutionPolicy Bypass -File scripts\setup_gpt_sovits.ps1

    可选参数：
        -RepoUrl <url>   换镜像/换 fork
        -Force           目标已存在也覆盖
#>
[CmdletBinding()]
param(
    [string]$RepoUrl = 'https://github.com/RVC-Boss/GPT-SoVITS.git',
    [switch]$Force
)

$ErrorActionPreference = 'Stop'
$ProgressPreference    = 'SilentlyContinue'

$ROOT   = Split-Path -Parent $PSScriptRoot
$DST    = Join-Path $ROOT 'gpt-sovits\api'
$TMP    = Join-Path $env:TEMP 'elaina_gptsovits'
$CLONE  = Join-Path $TMP 'GPT-SoVITS'

function Say($m, $c = 'Gray') { Write-Host $m -ForegroundColor $c }
function Ok($m)   { Write-Host "    OK   $m" -ForegroundColor Green }
function Warn($m) { Write-Host "    WARN $m" -ForegroundColor Yellow }
function Die($m)  { Write-Host "    FAIL $m" -ForegroundColor Red; exit 1 }

# ---------- 前置 ----------
if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    Die '没找到 git。先装 Git for Windows：https://git-scm.com/download/win'
}

$apiPy = Join-Path $DST 'api_v2.py'
if ((Test-Path $apiPy) -and (-not $Force)) {
    Ok "gpt-sovits\api\api_v2.py 已存在，跳过（要重拉加 -Force）"
    exit 0
}

# ---------- clone ----------
Write-Host ''
Say '[1/3] 克隆上游仓库（浅克隆，只取最新一次提交）' 'Cyan'
if (Test-Path $CLONE) { Remove-Item $CLONE -Recurse -Force -EA 0 }
New-Item -ItemType Directory -Path $TMP -Force | Out-Null
Say "    $RepoUrl"
git clone --depth 1 $RepoUrl $CLONE
if ($LASTEXITCODE -ne 0) {
    Warn 'clone 失败。国内网络可以试镜像：'
    Warn '    -RepoUrl https://ghfast.top/https://github.com/RVC-Boss/GPT-SoVITS.git'
    Die '请改用上面地址重跑'
}
Ok '克隆完成'

# ---------- 拷贝 ----------
Write-Host ''
Say '[2/3] 拷贝推理所需文件到 gpt-sovits\api' 'Cyan'
New-Item -ItemType Directory -Path $DST -Force | Out-Null

$files = @('api_v2.py', 'config.py', 'LICENSE', 'requirements.txt', 'extra-req.txt', 'README.md')
foreach ($f in $files) {
    $src = Join-Path $CLONE $f
    if (Test-Path $src) {
        Copy-Item $src -Destination $DST -Force
        Ok $f
    } else {
        Warn "$f 在上游不存在，跳过"
    }
}

# GPT_SoVITS/ 排除 pretrained_models（4 GB 以上）和 __pycache__
$srcG = Join-Path $CLONE 'GPT_SoVITS'
$dstG = Join-Path $DST 'GPT_SoVITS'
if (Test-Path $srcG) {
    Say '    GPT_SoVITS\ （排除 pretrained_models / __pycache__，约 725 MB）'
    robocopy $srcG $dstG /E /XD pretrained_models __pycache__ /NFL /NDL /NJH /NJS /NP | Out-Null
    if ($LASTEXITCODE -ge 8) { Die "robocopy GPT_SoVITS 失败（exit $LASTEXITCODE）" }
    Ok 'GPT_SoVITS\ 完成'
} else {
    Die '上游没有 GPT_SoVITS\ 目录，仓库结构可能变了，请手动拷'
}

# tools/i18n 是 api_v2.py 唯一需要的 tools 子目录
$srcI = Join-Path $CLONE 'tools\i18n'
$dstI = Join-Path $DST 'tools\i18n'
if (Test-Path $srcI) {
    New-Item -ItemType Directory -Path (Split-Path $dstI -Parent) -Force | Out-Null
    Copy-Item $srcI -Destination (Split-Path $dstI -Parent) -Recurse -Force
    Ok 'tools\i18n\ （0.3 MB，api_v2.py 只需要这个）'
} else {
    Warn '找不到 tools\i18n，api_v2.py 可能 import 失败'
}

# pretrained_models 目录先建空壳，给用户一个明确落点
$pm = Join-Path $dstG 'pretrained_models'
New-Item -ItemType Directory -Path $pm -Force | Out-Null
Ok "预留 pretrained_models\ 空目录"

# ---------- 下一步提示 ----------
Write-Host ''
Say '[3/3] 还需要你手动下基座权重' 'Cyan'
Say ''
Say '  放进：' -ForegroundColor White
Say "    $pm"
Say ''
Say '  需要这几个（共约 4.2 GB，GPT-SoVITS 的 release 页有打包版）：' -ForegroundColor White
Say '    chinese-roberta-wwm-ext-large\pytorch_model.bin          651 MB'
Say '    chinese-hubert-base\pytorch_model.bin                    189 MB'
Say '    s1bert25hz-2kh-longer-epoch=68e-step=50232.ckpt          155 MB'
Say '    v2Pro\s2Gv2ProPlus.pth                                   200 MB   ← v2ProPlus 用这个'
Say '    sv\pretrained_eres2netv2w24s4ep4.ckpt                    108 MB'
Say '    fast_langdetect\lid.176.bin                              131 MB'
Say ''
Say '  然后放角色音色权重（要成对，GPT 管语气/SoVITS 管音色）：' -ForegroundColor White
Say '    gpt-sovits\weights\GPT_weights_v2ProPlus\*.ckpt'
Say '    gpt-sovits\weights\SoVITS_weights_v2ProPlus\*.pth'
Say ''
Say '  最后跑自检：runtime\py312\python.exe scripts\check.py'
Write-Host ''
