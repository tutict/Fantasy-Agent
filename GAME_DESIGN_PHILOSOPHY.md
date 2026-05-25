# Game Design Philosophy

Fantasy Agent is built around one production belief: a prototype is valuable only when it can be played.

The platform should not produce broad promises, empty worlds, or decorative assets detached from interaction. It should generate small designs where mechanics, level layout, feedback, and failure states reinforce each other.

## Gameplay First

A gameplay idea becomes useful when it defines player decisions:

- What can the player do?
- What pressure changes the decision?
- What feedback confirms the outcome?
- What does mastery look like?

Visual style matters after the loop is legible. Early procedural assets should clarify scale, pathing, danger, objective state, and affordances.

## Prototype Over Perfection

Fantasy Agent targets game-jam scale production. The right first result is a playable greybox with a clear loop, not a polished but untested scene.

Default scope:

- One map
- One main objective
- Three to five core verbs
- Three level beats
- One win state
- Two to four failure states
- A restart path
- A short end-state summary

## Systemic Design

Systems should interact. A pressure clock should affect route choice. A resource should influence risk. A hazard should change movement or timing. A puzzle should alter the level state.

Disconnected mechanics are cut until the core loop works.

## Short Playable Loops

Fantasy Agent designs for 5 to 15 minute sessions. Short loops make playtesting possible, reveal broken assumptions quickly, and keep automation grounded.

Each vertical slice should support:

- First-time completion in one to three attempts
- Fast restart
- Clear failure explanation
- Obvious objective state
- Tunable pressure and pacing

## Procedural Content With Purpose

Procedural generation is useful when it accelerates iteration:

- Greybox arena kits
- Objective props
- Hazard markers
- Modular traversal pieces
- Export manifests
- ComfyUI reference boards for reviewed visual direction

It is not useful when it creates volume without play value.

ComfyUI is useful for visual references only after the loop has clear readability needs. It should clarify objectives, hazards, routes, materials, UI feedback, or storyboards; it should not replace greybox playtesting.

## MCP As Production Infrastructure

MCP integrations should expose real tools:

- Unreal project creation
- Editor commandlets
- Asset import
- Blender Python execution
- ComfyUI local workflow execution
- GitHub branch and PR workflows

MCP tools must declare inputs, outputs, side effects, and safety checks before they run.
