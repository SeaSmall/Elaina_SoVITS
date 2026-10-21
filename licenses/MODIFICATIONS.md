修改声明（Apache License 2.0 §4(b)）
================================================================

Apache-2.0 要求：当你分发基于 Apache-2.0 作品的修改版本时，必须显著地说明
你修改了原文件 / 原作品。

## model\laya\ —— Laya 屏幕意图判断模型

  * 上游作品：`convaiinnovations/laya-multilingual`
  * 上游许可：Apache License 2.0
  * 修改内容：**本包内该模型是在上述上游模型基础上进行微调（fine-tune）
    得到的派生模型**，用于判断"用户这句话是否需要看屏幕"这一单一二分类任务。
    编码器结构未改动；分类头与部分参数已针对该任务重新训练。
  * 修改方：本软件的使用者 / 打包者（非 ConvAI Innovations）
  * 上游模型卡：https://huggingface.co/convaiinnovations/laya-multilingual

  ⚠ 上游项目与本修改版本之间**没有任何隶属或背书关系**。上游作者不对本修改
    版本的输出、准确性与适用性作任何担保。

## 其它

  * 本项目**未修改** SoundCard、sounddevice、funasr、dxcam、PyTorch 等第三方
    依赖的源代码，只是随包分发未修改的二进制/源码副本。
  * 本项目**不包含** GPT-SoVITS 的角色权音权重，也不包含任何参考音频。
