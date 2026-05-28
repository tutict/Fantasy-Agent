# Fantasy Agent Orchestration Rules

Fantasy Agent agents are modular production workers. Each agent owns a narrow responsibility, receives structured input, returns structured output, and can later be backed by an LLM, LangGraph node, local script, or MCP tool.

Fantasy Agent 的智能体是模块化生产工人。每个智能体只负责清晰边界内的任务，接收结构化输入，返回结构化输出，未来可以由 LLM、LangGraph 节点、本地脚本或 MCP 工具驱动。

## Global Rules

- Gameplay comes before graphics.
- Every generated asset, mechanic, and automation step must support a playable loop.
- Target 5 to 15 minute vertical slices.
- Prefer one cohesive loop over many disconnected features.
- Do not create empty procedural spaces.
- Do not hide uncertainty. Mark assumptions and unresolved production risks.
- Tool side effects must be explicit before MCP execution.
- QA checks must run before packaging or visual expansion.
- English and Simplified Chinese outputs must stay synchronized through the `i18n` bundle.
- ComfyUI is a visual reference worker, not a gameplay authority.
- ChatGPT Apps tools are interactive planning surfaces; they must not execute production side effects without explicit confirmation.

- 玩法优先于图形。
- 每个生成资产、机制和自动化步骤都必须服务可玩循环。
- 目标是 5 到 15 分钟的垂直切片。
- 优先做一个内聚循环，而不是多个断开的功能。
- 不创建空洞的程序化空间。
- 不隐藏不确定性。必须标出假设和未解决的生产风险。
- MCP 工具副作用必须在执行前声明清楚。
- QA 检查必须先于打包和视觉扩展。
- 中英文输出必须通过 `i18n` 翻译包保持同步。
- ChatGPT Apps 工具是交互式计划入口；没有明确确认时不得执行生产副作用。

## Locale Rules

## 语言规则

- Canonical implementation identifiers stay in English: class names, Blueprint names, folder paths, MCP tool names, and metric keys.
- Human-facing design text supports `en` and `zh-CN`.
- The core DSL stores stable English fields and optional field-path translations under `i18n`.
- GDD output should include both languages when both locales are requested.

- 实现标识保持英文：类名、蓝图名、文件夹路径、MCP 工具名和指标名。
- 面向人的设计文本支持 `en` 与 `zh-CN`。
- 核心 DSL 保存稳定英文主字段，字段路径翻译放在可选的 `i18n` 下。
- 同时请求两种语言时，GDD 应输出中英双语版本。

## Agent Handoff Contract

Agents exchange Pydantic models from `fantasy_agent/contracts.py` and YAML or markdown artifacts in `generated/`.

Required handoff properties:

- `source`: producing agent or tool
- `schema_version`: version of the gameplay DSL or tool contract
- `inputs`: source prompt, spec, or manifest
- `outputs`: generated artifacts
- `risks`: blocking issues or assumptions
- `next_actions`: concrete next steps

## Director Agent

Responsibility:

- Own the full prompt-to-playable workflow.
- Route work to Gameplay Agent, GDD Writer, Unreal Builder, Blender Worker, QA Agent, and future MCP tools.
- Reject scope that cannot plausibly produce a playable vertical slice.

Input:

- `PromptRequest`

Output:

- `DirectorBuildPlan`

Workflow:

1. Normalize prompt and constraints.
2. Generate a gameplay-first spec.
3. Render GDD.
4. Prepare Unreal and Blender handoffs.
5. Prepare QA plan.
6. Return next actions and risks.

## Gameplay Agent

Responsibility:

- Transform raw prompts into coherent gameplay systems.
- Define core loop, verbs, pacing, progression, win state, and failure states.

Input:

- `PromptRequest`

Output:

- `GameplaySpec`

Rules:

- A mechanic is valid only if it changes a player decision.
- A loop is valid only if it can be tested in a greybox map.
- A failure state must teach the next attempt.

## GDD Writer

Responsibility:

- Convert the gameplay spec into a structured markdown design document.
- Preserve gameplay intent without adding unapproved features.

Input:

- `GameplaySpec`

Output:

- `GDDDocument`

Rules:

- Write for implementation.
- Separate confirmed design from assumptions.
- Keep art direction secondary to interaction readability.

## Level Director

Responsibility:

- Convert gameplay loops into level beats and greybox requirements.
- Keep spatial plans compact enough for rapid iteration.

Input:

- `GameplaySpec`

Output:

- Level beat plan, encounter plan, greybox asset needs.

Rules:

- The first minute must teach the loop.
- The midpoint must combine systems.
- The final beat must force the complete loop.

## Unreal Builder

Responsibility:

- Prepare UE5 project structure, plugins, maps, Blueprint classes, data assets, and automation steps.

Input:

- `GameplaySpec`

Output:

- `UnrealProjectPlan`

Future MCP compatibility:

- Unreal MCP should execute only allowlisted project creation, asset import, map validation, and packaging commands.

## Blender Worker

Responsibility:

- Prepare procedural asset jobs that support greybox playability and readable interactions.
- Generate Blender Python scripts from approved `BlenderAssetPlan` handoffs.

Input:

- `GameplaySpec`

Output:

- `BlenderAssetPlan`

Rules:

- Generate modular assets first.
- Use scale-correct exports.
- Name assets by gameplay role.
- Generate `UCX_` collision objects and Unreal import manifests with every export.
- Do not run Blender from planning surfaces without explicit side-effect confirmation.
- Blender MCP execution must keep scripts under `generated/blender/`, exports under `generated/assets/`, and logs under `generated/logs/blender/`.

## ComfyUI Worker

Responsibility:

- Prepare gameplay-readable visual reference jobs for ComfyUI.
- Generate concept, material, UI, texture-seed, or storyboard references after gameplay needs are known.

Input:

- `GameplaySpec`

Output:

- `ComfyUIVisualPlan`

Rules:

- Do not block greybox work on image generation.
- Every prompt must include a gameplay constraint.
- Generated images require review before becoming Unreal textures or UI assets.
- Avoid decorative images that do not clarify objectives, hazards, routes, materials, or feedback.
- ComfyUI MCP execution must keep templates under `templates/comfyui/`, outputs under `generated/comfyui/`, and logs under `generated/logs/comfyui/`.
- Do not submit prompts to ComfyUI without explicit side-effect confirmation.

## ChatGPT Workbench

Responsibility:

- Expose Fantasy Agent as a ChatGPT Apps-compatible interactive workbench.
- Route ChatGPT tool calls into the same structured planning contracts used by local agents.
- Render gameplay, GDD, Unreal, Blender, ComfyUI, and QA handoffs in a widget.

Input:

- `PromptRequest`

Output:

- `DirectorBuildPlan`
- Focused sub-plans such as `GDDDocument`, `UnrealProjectPlan`, `BlenderAssetPlan`, `ComfyUIVisualPlan`, or `QAPlan`

Rules:

- Tools must be read-only and idempotent until explicit side-effect gates are implemented.
- Widget state may summarize plans, but implementation identifiers remain English.
- ChatGPT interaction must preserve the gameplay-first hierarchy and i18n outputs.
- Do not launch Unreal, Blender, ComfyUI, package builds, write files, or push GitHub changes from this surface by default.

## QA Agent

Responsibility:

- Convert the gameplay spec into tests that validate playability, failure feedback, and package readiness.

Input:

- `GameplaySpec`

Output:

- `QAPlan`

Rules:

- Test the loop before polishing.
- Check completion time, restart flow, objective readability, and packaged build behavior.
