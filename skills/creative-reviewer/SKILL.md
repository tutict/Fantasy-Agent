# Creative Reviewer

Use this skill when ComfyUI images or Blender meshes need user review before Unreal ingest.

## Responsibility

- Compare generated outputs with gameplay readability, art direction, and technical import readiness.
- Ask the user for approve, revise, or reject decisions.
- Produce revision prompts that can return work to ComfyUI or Blender.

## Inputs

- `GameplaySpec`
- `BlenderAssetPlan`
- `ComfyUIVisualPlan`
- Optional generated images, mesh previews, or manifests

## Outputs

- `CreativeReviewReport`
- `AssetApprovalManifest`
- Revision prompts and rejected asset list

## Rules

- User taste and art direction override generated assets.
- Do not approve assets that weaken route, hazard, objective, feedback, or verb readability.
- Do not allow Unreal ingest without recorded approval decisions.
- Keep feedback concrete: name the asset, the issue, and the requested revision.

## 中文规则

- 生成结果必须先经过用户审阅，再进入 Unreal 导入。
- 审阅重点是玩法可读性、风格匹配、轮廓清晰度和技术可用性。
- 不符合用户艺术表达的结果应进入修改或拒绝列表。
