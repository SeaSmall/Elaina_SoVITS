# 第三方许可汇总

本目录汇总随包分发的所有第三方组件的许可与来源。

| 文件 | 内容 |
|---|---|
| `THIRD_PARTY_LICENSES.md` | 所有 Python 包（runtime\py312、envs\*、gpt-sovits）的许可原文摘要 |
| `VB-AUDIO-NOTICE.txt` | VB-Audio 虚拟声卡的来源、donationware 声明与分发限制 |
| `MODIFICATIONS.md` | 修改过的模型/代码声明（Apache-2.0 §4(b) 要求） |

## 随包分发的组件归组

**A. 保留声明即可分发**（Apache-2.0 / MIT / BSD / PSF）
Python、PyTorch、soundcard、sounddevice、dxcam、funasr、laya、GPT-SoVITS 代码。
→ 保留各自的 LICENSE 文件与版权声明即可。

**B. 需要额外署名**
SenseVoice-Small（ModelScope 标 Apache-2.0，但 FunASR 官方协议要求注明出处、
作者信息并保留模型名称）。
→ 署名文本见下方。

**C. 需要购买授权，本包不含**
Voicemeeter Potato、VB-CABLE A+B / C+D。

**D. 有条件分发**
Voicemeeter Banana / 标准版、VB-CABLE —— 需注明来源 + 说明 donationware，
详见 `VB-AUDIO-NOTICE.txt`。

**E. 不随包分发**
角色音色权重（GPT + SoVITS）、参考音频、GPT-SoVITS 基座预训练权重、
任何 API Key、任何人的声纹文件。

---

## 署名文本（SenseVoice）

> 本软件包含由阿里巴巴通义实验室（Alibaba Group / Tongyi SpeechTeam）发布的
> **SenseVoice-Small** 模型的未修改副本。
> 模型名称：SenseVoice-Small
> 来源：ModelScope `iic/SenseVoiceSmall` / GitHub `FunAudioLLM/SenseVoice`
> 许可：Apache License 2.0（ModelScope 标注）/ FunASR Model Open Source
> License Agreement v1.1（FunASR 官方标注）。本软件按两者中较严格的要求分发。

> 本项目包含 **CAM++ 说话人识别** 模型的未修改副本，
> 来源：ModelScope `iic/speech_campplus_sv_zh-cn_16k-common`，Apache License 2.0。

> 本项目包含 **GPT-SoVITS** 的未修改代码副本，MIT License，
> 来源：https://github.com/RVC-Boss/GPT-SoVITS

---

## 如何重新生成 THIRD_PARTY_LICENSES.md

```
runtime\py312\python.exe scripts\gen_licenses.py
```

它会扫描 `runtime\py312`、`envs\sv_env`、`envs\sd_env`、`gpt-sovits\api` 里
所有 `*.dist-info` 与 `*.egg-info`，把每个包的名称、版本、许可字段与 LICENSE
文件原文摘要拼成上面的文件。**打包前请重跑一次**，避免装了新包却漏了许可。
