# Blender Generator Skill

Use this skill when preparing procedural assets through Blender Python or Blender MCP.

## Responsibility

Generate gameplay-readable greybox and modular assets.

## Inputs

- `GameplaySpec`
- `BlenderAssetPlan`

## Outputs

- Blender Python job manifest
- FBX or GLB exports
- Unreal import manifest

## Workflow

1. Generate scale-correct primitives.
2. Use naming based on gameplay role.
3. Apply simple collision-friendly shapes.
4. Export into `generated/assets/`.
5. Produce an import manifest for Unreal.

## Guardrails

- Do not spend procedural effort on decorative detail before the loop works.
- Do not export assets outside the generated asset directory.
- Keep meshes modular and easy to replace.
