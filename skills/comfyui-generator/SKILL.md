# ComfyUI Generator Skill

当需要为可玩原型准备 ComfyUI 视觉参考任务时使用此 skill。

## 职责

生成支持玩法可读性的参考图计划：

- 概念可读性参考
- 材质和色彩语言板
- UI 参考帧
- 经审阅可用的 texture seed
- 关卡节奏 storyboard

## 输入

- `GameplaySpec`
- `ComfyUIVisualPlan`
- 已批准的玩法约束

## 输出

- ComfyUI workflow job manifest
- 已准备的 workflow JSON 文件
- 生成参考图路径
- Run manifest 和 prompt ID

## 护栏

- 不把 ComfyUI 输出当作原型可玩的证据。
- 不因图像生成阻塞 UE/Godot 灰盒工作。
- 每张图都必须支持目标清晰度、危险可读性、路线规划、UI 反馈或材质语言。
- 生成图片成为引擎资产前必须经过审阅。
- 没有明确副作用确认时，不提交 ComfyUI prompt。
- Workflow 模板保持在 `templates/comfyui/`，输出保持在 `generated/comfyui/`。
