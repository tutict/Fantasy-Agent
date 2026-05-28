# Fantasy Agent

Fantasy Agent is **an AI-native multi-agent game production platform**.

Fantasy Agent 是一个 **AI 原生的多智能体游戏生产平台**。

It transforms gameplay ideas into playable Unreal Engine prototype plans through agent orchestration, structured design output, procedural workflows, and MCP-integrated tooling.

它通过智能体编排、结构化设计输出、程序化工作流和 MCP 工具集成，把玩法想法转化为可运行的 Unreal Engine 原型计划。

Fantasy Agent is built for game-jam scale vertical slices: small playable loops, fast iteration, explicit handoffs, and automation that serves design. The platform starts with a gameplay DSL, then coordinates specialist agents for GDD writing, Unreal project setup, Blender asset generation, QA, and packaging.

Fantasy Agent 面向 game jam 规模的垂直切片：短小可玩的循环、快速迭代、明确交接，以及服务设计目标的自动化。平台以 Gameplay DSL 为源头，随后协调 GDD 写作、Unreal 项目搭建、Blender 资产生成、QA 和打包等专职智能体。

## Core Direction

## 核心方向

Fantasy Agent focuses on:

- Gameplay orchestration before visual polish
- Prompt-to-playable prototype pipelines
- Structured GDD and gameplay DSL output
- UE5 project architecture and Unreal Python automation
- Blender `bpy` procedural asset workflows
- ComfyUI visual reference workflows
- ChatGPT Apps workbench for interactive MCP tool calls
- MCP contracts for Unreal, Blender, ComfyUI, and GitHub tooling
- Multi-agent workflows that can evolve into LangGraph execution

The system is not meant to replace design judgment. It creates scoped, inspectable production steps so a small team can move from idea to a playable prototype quickly.

Fantasy Agent 关注：

- 视觉打磨之前的玩法编排
- Prompt 到可玩原型的生产管线
- 结构化 GDD 和 Gameplay DSL 输出
- UE5 项目架构与 Unreal Python 自动化
- Blender `bpy` 程序化资产工作流
- Unreal、Blender 和 GitHub 的 MCP 工具契约
- 可演进到 LangGraph 的多智能体工作流

系统不是为了替代设计判断，而是把生产步骤缩小、结构化、可检查，让小团队更快从想法走到可玩原型。

## i18n / 国际化

Fantasy Agent supports English and Simplified Chinese together.

Fantasy Agent 支持英文与简体中文并行输出。

- `PromptRequest.source_locale` records the input language.
- `PromptRequest.output_locales` defaults to `["en", "zh-CN"]`.
- `GameplaySpec.i18n` stores field-path translations without breaking the core DSL.
- `GDDDocument.markdown_by_locale` stores per-language documents.
- `GDDDocument.markdown` returns a combined bilingual document when both locales are requested.

- `PromptRequest.source_locale` 记录输入语言。
- `PromptRequest.output_locales` 默认输出 `["en", "zh-CN"]`。
- `GameplaySpec.i18n` 使用字段路径保存翻译，不破坏核心 DSL。
- `GDDDocument.markdown_by_locale` 保存各语言版本文档。
- 同时请求中英双语时，`GDDDocument.markdown` 会返回合并后的双语文档。

## ChatGPT Workbench / ChatGPT 工作台

Fantasy Agent now includes a ChatGPT Apps-compatible workbench under `apps/chatgpt-workbench`. It exposes read-only MCP tools for generating and inspecting gameplay-first production plans inside ChatGPT.

Fantasy Agent 现在包含 `apps/chatgpt-workbench`，可作为 ChatGPT Apps 兼容的工作台运行。它通过只读 MCP 工具在 ChatGPT 内生成并检查玩法优先的生产计划。

The first version does not execute Unreal, Blender, ComfyUI, packaging, or GitHub side effects. It prepares structured handoffs first, then future MCP tools can execute allowlisted production steps with explicit approval.

第一版不会执行 Unreal、Blender、ComfyUI、打包或 GitHub 副作用。它先准备结构化交接结果，后续 MCP 工具再在明确确认后执行 allowlist 内的生产步骤。

## Repository Layout

## 仓库结构

```text
Fantasy-Agent/
|-- apps/
|   |-- web-console/        # Local browser UI for prompt-to-playable planning
|   |-- chatgpt-workbench/  # ChatGPT Apps MCP endpoint and interactive widget
|   |-- director-agent/     # Orchestrates prompt-to-playable planning
|   |-- gameplay-agent/     # Converts prompts into gameplay DSL specs
|   |-- unreal-builder/     # Prepares UE5 project architecture
|   |-- blender-worker/     # Prepares Blender procedural asset jobs
|   |-- comfyui-worker/     # Prepares ComfyUI visual reference jobs
|   `-- qa-agent/           # Creates smoke, playability, and packaging checks
|-- fantasy_agent/          # Shared Pydantic contracts and workflow primitives
|-- skills/
|   |-- gameplay-designer/
|   |-- gdd-writer/
|   |-- level-director/
|   |-- ue-architect/
|   |-- blender-generator/
|   `-- comfyui-generator/
|-- mcp/
|   |-- chatgpt-apps-mcp/
|   |-- blender-mcp/
|   |-- unreal-mcp/
|   |-- comfyui-mcp/
|   `-- github-mcp/
|-- templates/
|-- generated/
|-- examples/
|-- docs/
|   |-- architecture/
|   |-- workflow/
|   |-- gameplay-dsl/
|   `-- research/
|-- legacy/                 # Previous Spring/Flutter traffic app preserved here
`-- gameplay-schema.yaml
```

## Initial Architecture

## 初始架构

The first implementation pass defines stable contracts before deep automation:

- `PromptRequest`: raw gameplay idea plus prototype constraints.
- `GameplaySpec`: YAML-ready design DSL with core loop, systems, pacing, progression, win/failure states, asset needs, UE notes, Blender notes, and QA focus.
- `GDDDocument`: markdown design document generated from the gameplay spec.
- `UnrealProjectPlan`: project folders, plugins, maps, Blueprint classes, and automation steps.
- `BlenderAssetPlan`: procedural asset jobs and export handoff paths.
- `BlenderScriptArtifact`: generated Blender Python script plus Unreal import manifest.
- `ComfyUIVisualPlan`: visual reference jobs for readability, material language, UI references, and reviewed texture seeds.
- `ComfyUIRunManifest`: prepared workflow files, prompt IDs, expected outputs, and execution logs for reviewed visual references.
- `QAPlan`: smoke tests, playability checks, packaging checks, and metrics.
- `DirectorBuildPlan`: combined orchestration output for the full first-pass pipeline.

第一阶段先定义稳定契约，再接入深度自动化：

- `PromptRequest`：原始玩法想法和原型约束。
- `GameplaySpec`：可写入 YAML 的设计 DSL，包含核心循环、系统、节奏、进程、胜负状态、资产需求、UE 说明、Blender 说明和 QA 重点。
- `GDDDocument`：由 GameplaySpec 生成的中英双语 markdown 设计文档。
- `UnrealProjectPlan`：项目目录、插件、地图、蓝图类和自动化步骤。
- `BlenderAssetPlan`：程序化资产任务和导出交接路径。
- `QAPlan`：冒烟测试、可玩性检查、打包检查和指标。
- `DirectorBuildPlan`：第一版完整管线的编排输出。

## Local Development

## 本地开发

Install the Python package in editable mode:

```bash
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e .
```

Run the Director Agent:

```bash
uvicorn app.main:app --reload --app-dir apps/director-agent
```

Run the Web Console:

```bash
uvicorn app.main:app --reload --app-dir apps/web-console --host 127.0.0.1 --port 7860
```

Open:

```text
http://127.0.0.1:7860
```

Run the ChatGPT Workbench MCP server:

```bash
uvicorn app.main:app --reload --app-dir apps/chatgpt-workbench --host 127.0.0.1 --port 8787
```

Local preview:

```text
http://127.0.0.1:8787
```

ChatGPT Developer Mode should connect to an HTTPS-tunneled URL ending in:

```text
/mcp
```

Example request:

```bash
curl -X POST http://127.0.0.1:8000/plan ^
  -H "Content-Type: application/json" ^
  -d "{\"prompt\":\"a stealth game where a courier escapes a haunted train station\",\"target_minutes\":10}"
```

The deterministic workflow is intentionally simple in Phase 1. LLM calls, LangGraph routing, MCP tool execution, and Unreal/Blender automation should attach behind the same contracts.

Phase 1 的确定性工作流故意保持简单。后续 LLM 调用、LangGraph 路由、MCP 工具执行以及 Unreal/Blender 自动化，都应该接在同一套契约之后。

## Legacy Code

## 旧代码

The previous Spring Boot and Flutter traffic-management project has been moved to:

```text
legacy/traffic-management-platform/
```

Useful ideas to preserve from that codebase include skill interfaces, streaming agent events, workflow/state-machine rigor, guardrail flags, and operational runbooks. Domain-specific traffic logic should not be carried into the game-production platform.

之前的 Spring Boot 和 Flutter 交通管理项目已移动到：

```text
legacy/traffic-management-platform/
```

值得保留的思路包括 skill 接口、流式 agent 事件、工作流/状态机约束、AI guardrail 配置和运维 runbook。交通业务逻辑不应进入新的游戏生产平台。

## Guiding Principle

## 指导原则

Every system should support the long-term vision:

> From imagination to playable worlds.

每个系统都应该服务长期愿景：

> 从想象到可玩的世界。
