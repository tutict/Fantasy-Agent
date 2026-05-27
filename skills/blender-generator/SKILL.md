# Blender Generator Skill

Use this skill when preparing procedural assets through Blender Python or Blender MCP.

## Responsibility

Generate gameplay-readable greybox and modular assets.

## Inputs

- `GameplaySpec`
- `BlenderAssetPlan`

## Outputs

- Blender Python job manifest
- Generated `.py` script for Blender execution
- FBX or GLB exports
- Unreal import manifest

## Workflow

1. Generate scale-correct primitives.
2. Use naming based on gameplay role.
3. Generate modular walls, doors, ramps, hazard markers, objective props, exit gates, and UI proxy meshes.
4. Assign collections, material color keys, origins, and `UCX_` collision names.
5. Export into `generated/assets/`.
6. Produce an import manifest for Unreal.
7. Hand the generated script to Blender MCP only after side effects are confirmed.

## Guardrails

- Do not spend procedural effort on decorative detail before the loop works.
- Do not export assets outside the generated asset directory.
- Keep meshes modular and easy to replace.
- Do not launch Blender automatically from planning tools.
