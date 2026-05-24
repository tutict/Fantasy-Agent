# Fantasy Agent Roadmap

## Phase 1: Repository Foundation

Status: started.

- Preserve legacy Spring/Flutter project under `legacy/`.
- Create modular app, skill, MCP, template, generated, examples, and docs structure.
- Define Pydantic contracts for prompt, gameplay spec, GDD, Unreal plan, Blender plan, QA plan, and director plan.
- Define `gameplay-schema.yaml`.
- Provide deterministic first-pass workflow functions.
- Document orchestration rules and game design philosophy.

## Phase 2: Gameplay And GDD Generation

- Replace deterministic prompt parsing with LLM-backed gameplay generation.
- Add schema validation for generated YAML.
- Add GDD rendering to `generated/gdd.md`.
- Add examples for stealth, survival, puzzle, combat, and traversal prototypes.
- Add tests for loop coherence, required fields, and target session length.

## Phase 3: Blender MCP Integration

- Implement Blender MCP server contract.
- Execute `bpy` procedural asset jobs from `BlenderAssetPlan`.
- Export FBX or GLB assets into `generated/assets/`.
- Generate import manifests for Unreal.
- Add asset scale and collision checks.

## Phase 4: Unreal MCP Integration

- Implement Unreal MCP server contract.
- Create UE project folders, maps, data assets, and Blueprint stubs.
- Import Blender-generated assets.
- Run editor validation commandlets.
- Produce build logs and failure summaries.

## Phase 5: Playable Prototype Automation

- Chain Director Agent through gameplay, GDD, Blender, Unreal, QA, and GitHub workflows.
- Package a Windows development build.
- Run smoke tests against the packaged prototype.
- Open a GitHub PR containing generated specs, manifests, and automation logs.
- Track iteration metrics across prototype runs.

## Non-Goals

- No fake production-ready AAA scope.
- No decorative procedural worlds without mechanics.
- No hidden tool side effects.
- No generated content that cannot be tested in a playable loop.
