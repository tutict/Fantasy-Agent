# Fantasy Agent Roadmap

## Phase 1: Repository Foundation

Status: started.

- Preserve legacy Spring/Flutter project under `legacy/`.
- Create modular app, skill, MCP, template, generated, examples, and docs structure.
- Define Pydantic contracts for prompt, gameplay spec, GDD, Unreal plan, Blender plan, QA plan, and director plan.
- Define ComfyUI visual reference contracts and MCP handoff boundaries.
- Define `gameplay-schema.yaml`.
- Provide deterministic first-pass workflow functions.
- Document orchestration rules and game design philosophy.
- Add a ChatGPT Apps-compatible workbench with read-only MCP planning tools and an interactive widget.

## Phase 2: Gameplay And GDD Generation

- Replace deterministic prompt parsing with LLM-backed gameplay generation.
- Add schema validation for generated YAML.
- Add GDD rendering to `generated/gdd.md`.
- Add examples for stealth, survival, puzzle, combat, and traversal prototypes.
- Add tests for loop coherence, required fields, and target session length.
- Expand ChatGPT Workbench tools from deterministic planning to LLM-backed gameplay and GDD generation while preserving read-only side-effect boundaries.

## Phase 3: Blender MCP Integration

- Generate Blender Python scripts from `BlenderAssetPlan`.
- Support modular walls, doors, ramps, hazard markers, objective props, exit gates, and UI proxy meshes.
- Generate Unreal import manifests with material, collection, dimensions, and collision metadata.
- Implement Blender MCP server contract.
- Execute `bpy` procedural asset jobs from `BlenderAssetPlan`.
- Export FBX or GLB assets into `generated/assets/`.
- Generate import manifests for Unreal.
- Add asset scale and collision checks.

## Phase 4: ComfyUI MCP Integration

- Implement ComfyUI MCP server contract.
- Execute allowlisted ComfyUI workflow templates from `ComfyUIVisualPlan`.
- Write generated reference images into `generated/comfyui/`.
- Produce prompt IDs, run manifests, and review notes.
- Keep ComfyUI outputs downstream of gameplay readability requirements.

## Phase 5: Unreal MCP Integration

- Implement Unreal MCP server contract.
- Create UE project folders, maps, data assets, and Blueprint stubs.
- Import Blender-generated assets.
- Run editor validation commandlets.
- Produce build logs and failure summaries.

## Phase 6: Playable Prototype Automation

- Chain Director Agent through gameplay, GDD, Blender, Unreal, QA, and GitHub workflows.
- Include ComfyUI visual references only after greybox needs are reviewed.
- Package a Windows development build.
- Run smoke tests against the packaged prototype.
- Open a GitHub PR containing generated specs, manifests, and automation logs.
- Track iteration metrics across prototype runs.

## Phase 7: ChatGPT Production Workspace

- Add authenticated project sessions for ChatGPT-hosted production plans.
- Persist approved generated specs, GDDs, and handoff manifests.
- Add explicit confirmation gates for mutating Unreal, Blender, ComfyUI, GitHub, and packaging tools.
- Stream production events back into the ChatGPT widget.
- Prepare a submission-readiness review only after private Developer Mode workflows are stable.

## Non-Goals

- No fake production-ready AAA scope.
- No decorative procedural worlds without mechanics.
- No hidden tool side effects.
- No generated content that cannot be tested in a playable loop.
