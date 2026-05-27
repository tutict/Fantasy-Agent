# Prompt To Playable Workflow

Fantasy Agent uses a staged workflow so every output can be inspected before side-effecting tools run.

## Stage 1: Prompt Intake

Input:

- Raw gameplay idea
- Session target
- Platform and engine constraints
- Production constraints

Output:

- `PromptRequest`

Entry points:

- Local Web Console
- ChatGPT Workbench MCP tool call
- Director Agent API

## Stage 2: Gameplay DSL

The Gameplay Agent generates a `GameplaySpec` with:

- Player fantasy
- Design pillars
- Core verbs
- Core loop
- Systems
- Progression
- Win state
- Failure states
- Level beats
- Asset needs
- QA focus

## Stage 3: GDD

The GDD Writer renders the gameplay spec into markdown. It does not add new scope. It clarifies implementation intent.

## Stage 4: Asset, Visual, And Engine Handoff

The Blender Worker prepares procedural asset jobs. The ComfyUI Worker prepares visual reference jobs for readability, material language, UI references, and reviewed texture seeds. The Unreal Builder prepares project structure, maps, Blueprint classes, and automation steps.

## Stage 5: MCP Execution

Future MCP servers execute controlled operations:

- ChatGPT Apps MCP exposes read-only planning tools and widget state.
- Blender MCP runs `bpy` jobs and exports assets.
- ComfyUI MCP runs allowlisted visual reference workflows.
- Unreal MCP creates/imports/validates project content.
- GitHub MCP publishes review branches and pull requests.

## Stage 6: QA And Packaging

The QA Agent checks:

- Objective readability
- Loop completion
- Failure feedback
- Restart flow
- Packaged build behavior

Packaging happens after the loop is playable.
