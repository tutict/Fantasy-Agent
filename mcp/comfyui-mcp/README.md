# ComfyUI MCP

ComfyUI MCP will execute controlled local ComfyUI workflows for visual reference generation.

Initial scope:

- Load allowlisted workflow templates from `templates/comfyui/`.
- Inject prompt and negative prompt text from `ComfyUIVisualPlan`.
- Submit jobs to a local ComfyUI endpoint.
- Write output images and run manifests under `generated/comfyui/`.

ComfyUI outputs are references. They must not block the gameplay greybox, and they require review before becoming Unreal textures, UI assets, or concept source material.
