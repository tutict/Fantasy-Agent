# ComfyUI Integration

ComfyUI is integrated as a visual reference worker, not as the source of gameplay truth.

## Role

ComfyUI can help with:

- Concept readability references
- Material and palette boards
- UI reference frames
- Reviewed texture seeds
- Storyboard frames for level beats

ComfyUI should not decide mechanics, pacing, win states, failure states, or level layout. Those come from the Gameplay DSL.

## Flow

```text
GameplaySpec
  -> ComfyUI Worker
  -> ComfyUIVisualPlan
  -> comfyui-mcp
  -> generated/comfyui/*
  -> reviewed visual references
```

## Safety

- Default endpoint is `http://127.0.0.1:8188`.
- Output stays under `generated/comfyui/`.
- Workflow templates come from `templates/comfyui/`.
- Each job must include a gameplay constraint.
- Generated images are reviewed before they become engine assets.

## 中文说明

ComfyUI 在 Fantasy Agent 中负责视觉参考，不负责玩法决策。

它适合生成：

- 玩法可读性概念参考
- 材质和色彩板
- UI 参考图
- 经评审后可用的贴图种子
- 关卡节奏 storyboard

机制、节奏、胜负状态和关卡布局仍然由 Gameplay DSL 决定。
