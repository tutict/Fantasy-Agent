# ComfyUI Generator Skill

Use this skill when preparing ComfyUI visual reference jobs for a playable prototype.

## Responsibility

Generate reference imagery plans that support gameplay readability:

- Concept readability references
- Material and color language boards
- UI reference frames
- Texture seeds for reviewed use
- Storyboard frames for level beats

## Inputs

- `GameplaySpec`
- `ComfyUIVisualPlan`
- Approved gameplay constraints

## Outputs

- ComfyUI workflow job manifest
- Prepared workflow JSON files
- Generated reference image paths
- Run manifest and prompt IDs

## Guardrails

- Do not use ComfyUI output as proof that the prototype is playable.
- Do not block UE greybox work on image generation.
- Every image must support objective clarity, hazard readability, route planning, UI feedback, or material language.
- Generated images require review before becoming engine assets.
- Do not submit ComfyUI prompts without explicit side-effect confirmation.
- Keep workflow templates under `templates/comfyui/` and outputs under `generated/comfyui/`.
