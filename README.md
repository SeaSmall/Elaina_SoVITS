# Elaina_SoVITS

一个**开箱即用**的本地 AI 语音陪玩助手：说话 → 识别 → 云端大模型 → （可选）日文翻译 → GPT-SoVITS 变声 → 播放，屏幕上的内容它还能自己看。

整个项目自带 Python 运行时，**接收方不需要装 Python、不需要配环境**，解压双击 `启动.bat` 即可。

> 完整的安装步骤（要下哪些模型、装哪些软件、音频怎么配、怎么排错）见
> **[docs/安装与配置.md](docs/安装与配置.md)**（要手工搭环境、或想知道每个包的精确版本，看 **[docs/环境部署.md](docs/环境部署.md)**）。下面只讲最短路。

---

## 怎么装

仓库里**只有代码和文档**，没有运行时。因为 Python + torch 光这两样就 9.3 GB
（其中 CUDA 库占绝大部分），不适合放进仓库或 Release。运行时用脚本现装：

```powershell
git clone https://github.com/SeaSmall/Elaina_SoVITS.git
cd Elaina_SoVITS
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\setup_runtime.ps1
```

它会装好：Python 3.12 + py39、torch（CUDA 11.8 版）、soundcard、funasr，
全部落在项目内的 `runtime\` 和 `envs\`，**不污染系统环境**，删项目即卸载。
约 12 GB 下载，视网速 20 分钟到 2 小时。

然后放模型（`docs/安装与配置.md` 第 4 节），双击 `启动.bat`。

> 仓库不含、Release 也不含：任何模型权重、角色音色、参考音频、声纹、API Key。

---

## 当前进度（先看这个）

这个项目正在从零重建，**目前只有文字对话能跑通**：

| 模块 | 状态 |
|---|---|
| 大模型直连（OpenAI 兼容 / Anthropic 两种协议） | ✅ 完成，协议已用假服务逐条验过 |
| 配置向导 / 自检 / 一键启动 | ✅ 完成 |
| 免环境运行时（内置 py39 + py312 + torch + CUDA） | ✅ 完成，实测 `cuda.is_available()=True` |
| 报错信息与许可证声明 | ✅ 完成 |
| 语音识别（SenseVoice） | ⏳ 未接线 |
| 变声（GPT-SoVITS） | ⏳ 未接线 |
| 桌面消息浮窗 | ⏳ 未接线 |
| 声纹校验 / 录声纹 | ⏳ 未接线 |
| 识图（云端 / 本地 / Laya 判断要不要看） | ⏳ 未接线 |
| QQ 通话自动接听 | ⏳ 未接线 |

也就是说：**现在能打字聊、能验证你的 Key 和模型服务通不通，但还不能说话。**
模型可以先按下面第 4 节下好放着，接上就能用。

---

## 直接开跑（三步）

1. **双击 `启动.bat`**
   第一次会自动进向导，只问你缺的东西（模型、Key、参考音频）。
2. **按提示填完**，向导会保存到 `config\config.json`（这个文件含你的 Key，**不要发给别人**）。
3. 再双击 `启动.bat` —— 自检通过会**直接进对话**，不再问任何问题。

要改配置：双击 `配置.bat`（逐项重问），或直接编辑 `config\config.json`。
想看当前配置（Key 已打码）：`runtime\py312\python.exe src\main.py --print-config`

---

## 目录说明

```
Elaina_SoVITS\
├─ 启动.bat                  ← 一键启动（自检 → 只补缺的 → 直接开跑）
├─ 配置.bat                  ← 重新配置
├─ config\
│   ├─ config.example.json   公开模板（Key 全空，随包分发）
│   ├─ config.json           你的实际配置（含 Key，别外发）
│   └─ ready.json            自检结果（自动生成）
├─ src\                      主程序代码
│   ├─ main.py               入口
│   ├─ config.py             配置读写与校验
│   ├─ util\paths.py         ★ 唯一的绝对路径出口
│   ├─ util\log.py           日志
│   └─ llm\                  大模型直连（OpenAI 兼容 + Anthropic 两种协议）
├─ scripts\
│   ├─ check.py              启动前自检
│   ├─ wizard.py             配置向导
│   ├─ setup_runtime.ps1     ★ 装运行时（装进项目内，不污染系统）
│   ├─ setup_gpt_sovits.ps1  拉取 GPT-SoVITS 推理代码
│   └─ gen_licenses.py       收集第三方许可
├─ docs\
│   ├─ 安装与配置.md         完整安装 / 配置 / 排错文档
│   └─ 环境部署.md           手工搭环境：精确版本、冲突原因、验证命令
├─ runtime\
│   ├─ py39\                 GPT-SoVITS 用的 Python 3.9 + torch 2.0（已内置）
│   └─ py312\                主程序用的 Python 3.12 + torch 2.7（已内置）
├─ envs\
│   ├─ sd_env\               soundcard / sounddevice（运行时注入 sys.path）
│   └─ sv_env\               funasr 1.1.18（ASR 用，与 runtime 自带的不兼容）
├─ gpt-sovits\
│   ├─ api\                  GPT-SoVITS 推理代码
│   └─ weights\              ★ 角色权重放这里（不随包分发）
├─ model\
│   ├─ asr\                  SenseVoice-Small
│   ├─ campplus\             CAM++ 声纹
│   ├─ laya\                 Laya 微调版（判断"要不要看屏幕"）
│   ├─ tts\                  预留
│   └─ vlm\                  本地识图模型（可选）
├─ data\
│   ├─ memory\               对话历史
│   ├─ captures\             通话截图（排查用）
│   └─ voiceprint\           你的声纹（不随包分发）
├─ vendor\                   虚拟声卡安装包
├─ licenses\                 全部第三方许可声明
└─ logs\                     运行日志
```

---

## 模型放哪（包内默认都留空）

| 目录 | 放什么 | 必需? | 从哪来 |
|---|---|---|---|
| `model\asr\` | SenseVoice-Small | 语音识别必需 | ModelScope `iic/SenseVoiceSmall` |
| `model\campplus\` | CAM++ 声纹模型 | 声纹校验才需要 | ModelScope `iic/speech_campplus_sv_zh-cn_16k-common` |
| `model\laya\` | Laya 微调版 | 自动判断识图才需要 | 训练产物 / 作者提供 |
| `gpt-sovits\weights\` | 角色 GPT + SoVITS 权重 | 变声必需 | 自己训练 |
| `model\vlm\` | Qwen3-VL 等本地视觉模型 | 只用本地识图才需要 | 可选，体积大 |

> 角色权重和参考音频**故意不打包**：它们是特定角色/声优的声音，不属于可自由再分发的内容。请自备。

---

## 大模型怎么配

向导支持三种：

| 选项 | 默认地址 | 默认模型 |
|---|---|---|
| DeepSeek | `https://api.deepseek.com/v1` | `deepseek-chat` |
| 小米 MiMo | `https://token-plan-cn.xiaomimimo.com/v1` | `mimo-v2.6-flash` |
| 其他 | 自己填（任何 OpenAI 兼容服务：ollama / vLLM / one-api / 官方） | 自己填 |

MiMo 还有一个 Anthropic 协议入口 `https://token-plan-cn.xiaomimimo.com/anthropic`，把 provider 填 `mimo-anthropic` 即可。

填完可以用这条命令验证通不通：

```
runtime\py312\python.exe src\main.py --selftest
```

成功会打印耗时和一句回复；失败会打印 HTTP 状态码和接口原始报错。

---

## 编码相关（改代码前必看）

- `.bat` 文件必须是 **UTF-8 无 BOM + CRLF**，配合 `chcp 65001`。加 BOM 会让第一行命令失效。
- Python 里**只对 stdout/stderr 设 `errors="replace"`，绝不设 `encoding="utf-8"`** —— Windows 控制台是 GBK，硬设会把中文全糊掉。
- 项目内部**不允许出现任何绝对路径**，一律走 `src\util\paths.py`。换盘符/换电脑只改那一个文件（其实连它都不用改，它按自身位置推算根目录）。

---

## 许可

本项目代码：见仓库 LICENSE。
随包分发的第三方组件、模型、安装包的许可与限制，全部列在 `licenses\` 下：

- `licenses\THIRD_PARTY_LICENSES.md` —— 所有 Python 包的许可
- `licenses\VB-AUDIO-NOTICE.txt` —— VB-Audio 虚拟声卡的来源与 donationware 声明
- `licenses\MODIFICATIONS.md` —— 哪些模型是修改版（Apache-2.0 要求声明）

**不随包分发**：角色音色权重、参考音频、任何 API Key、任何人的声纹。

---

## 已知限制

- **只跑在 Windows**（用到 WASAPI 音频、窗口自动化、DPI 相关 API）。
- **QQ 自动接听是窗口像素自动化，不是 QQ 官方 API**：依赖本机登录的 QQ NT 客户端、来电弹窗外观、100% 缩放。换 QQ 版本/皮肤/缩放比例可能失效。个人号做自动化有封号风险，请自行判断。
- 本地模型（ASR / Laya / TTS）建议有 NVIDIA 显卡；没有 GPU 也能跑，但 TTS 会很慢。
- 识图默认走云端（省显存）；本地识图模型体积大、默认不打包。
