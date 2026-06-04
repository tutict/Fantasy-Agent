# Unreal MCP

Unreal MCP 用于执行受控 Unreal Engine 自动化，包括工程搭建、验证和打包。

初始范围：

- 创建生成的 `.uproject`、`Config`、内容目录、setup script 和 content manifest。
- 引用 Blender import manifest，供后续 Unreal Python 导入使用。
- 为 Blender mesh 和已审阅 ComfyUI 参考准备并运行资产导入脚本。
- 为生成原型地图准备并运行灰盒关卡组装脚本。
- 在明确确认后运行 allowlist 内的 Unreal Editor data validation。
- 在 QA 验收通过后打包 development build。

实际操作必须明确声明并记录日志。
