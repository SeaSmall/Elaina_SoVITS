这个目录放 GPT-SoVITS 的推理代码（不随仓库分发）
=====================================================

仓库里**故意不含**这部分代码（它有 700 多 MB，而且应该跟着上游更新）。
你需要自己放进来，放置后结构是：

    gpt-sovits\
        api\
            api_v2.py
            GPT_SoVITS\
            tools\
            config.py
            LICENSE
        weights\
            （角色权重，见该目录下的说明）

最省事的做法 —— 二选一：

【做法 1】用脚本自动拉（推荐，需要装 git）
    在项目根目录打开 PowerShell，执行：

        powershell -NoProfile -ExecutionPolicy Bypass -File scripts\setup_gpt_sovits.ps1

    它会 clone 上游仓库，然后把需要的部分拷到 gpt-sovits\api\。

【做法 2】手动
    1) git clone https://github.com/RVC-Boss/GPT-SoVITS.git 到任意临时目录
    2) 把下面这些拷进 gpt-sovits\api\ ：
         api_v2.py
         config.py
         LICENSE
         requirements.txt
         GPT_SoVITS\        ← 但**排除** GPT_SoVITS\pretrained_models（那是几 GB 的基座权重）
         tools\i18n\        ← api_v2.py 只用到 tools 里的 i18n
    3) 从 release 页面下载基座预训练权重，放到
         gpt-sovits\api\GPT_SoVITS\pretrained_models\
       需要的子目录见 docs\安装与配置.md

为什么只拷 i18n：
    tools 目录下 asr(2.6GB) / uvr5(718MB) 是训练和预处理用的，
    纯推理只要 i18n 那 0.3MB。

⚠ GPT-SoVITS 是 MIT 许可，但那只覆盖**代码**。
   你自己训出来的角色音色权重能不能分发给别人，不属于这个许可的范围。
