# Creative Reviewer

当 ComfyUI 图片或 Blender mesh 需要在 Unreal/Godot 导入前由用户审阅时使用此 skill。

## 职责

- 将生成结果与玩法可读性、艺术方向和技术导入准备度进行对比。
- 让用户作出批准、修改或拒绝决定。
- 产出可返回 ComfyUI 或 Blender 的具体修改 prompt。

## 输入

- `GameplaySpec`
- `BlenderAssetPlan`
- `ComfyUIVisualPlan`
- 可选生成图片、mesh 预览或 manifest

## 输出

- `CreativeReviewReport`
- `AssetApprovalManifest`
- 修改 prompt 和被拒绝资产列表

## 规则

- 用户审美和艺术方向优先于生成资产。
- 不批准会削弱路线、危险、目标、反馈或动词可读性的资产。
- 没有记录审批决定时，不允许 Unreal/Godot 导入。
- 反馈必须具体：说明资产、问题和请求的修改。
- 不符合用户艺术表达的结果应进入修改或拒绝列表。
