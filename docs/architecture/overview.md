# Architecture Overview

Fantasy Agent is organized around stable contracts and replaceable workers.

## Flow

```text
PromptRequest
  -> ChatGPT Workbench or Local API
  -> Director Agent
  -> Gameplay Agent
  -> GameplaySpec
  -> GDD Writer
  -> Unreal Builder
  -> Blender Worker
  -> ComfyUI Worker
  -> QA Agent
  -> MCP tools
  -> Playable prototype artifacts
```

## Shared Contracts

The `fantasy_agent/` package defines the first contract layer:

- `PromptRequest`
- `GameplaySpec`
- `GDDDocument`
- `UnrealProjectPlan`
- `BlenderAssetPlan`
- `ComfyUIVisualPlan`
- `QAPlan`
- `DirectorBuildPlan`
- `MCPToolContract`

These models are the boundary between agents. The implementation behind an agent can change from deterministic Python to LLM calls, LangGraph nodes, or MCP tools without rewriting downstream consumers.

## App Workers

Each app is a small FastAPI service:

- `director-agent`: orchestration boundary
- `chatgpt-workbench`: ChatGPT Apps MCP endpoint and interactive widget
- `gameplay-agent`: prompt to gameplay DSL
- `unreal-builder`: UE5 architecture plan
- `blender-worker`: procedural asset job plan
- `comfyui-worker`: gameplay-readable visual reference plan
- `qa-agent`: playability and packaging checks

## ChatGPT Apps Surface

The ChatGPT Workbench is an interactive MCP surface over the same contracts. It provides read-only tools for plan generation, GDD rendering, Unreal planning, Blender planning, ComfyUI planning, and QA planning. It does not execute production side effects in Phase 1.

ChatGPT 工作台复用同一套合约，提供计划生成、GDD 渲染、Unreal 计划、Blender 计划、ComfyUI 计划和 QA 计划等只读工具。第一阶段不执行生产副作用。

## Legacy Inputs

The previous repository contained useful architectural ideas:

- Skill interfaces
- Streamed agent events
- State-machine workflow discipline
- Operational runbooks
- Guardrail-oriented AI configuration

Those ideas are preserved for reference under `legacy/traffic-management-platform/`.
