# GDD Writer Skill

Use this skill when turning a validated gameplay spec into a structured markdown game design document.

## Responsibility

Write a build-facing GDD that preserves the gameplay contract.

## Inputs

- `GameplaySpec`
- Known assumptions or constraints

## Outputs

- `GDDDocument`
- `generated/gdd.md`

## Sections

- Summary
- Player fantasy
- Design pillars
- Core verbs
- Core loop
- Systems
- Progression
- Win and failure states
- Level beats
- Asset needs
- Unreal notes
- Blender notes
- QA focus

## Guardrails

- Do not add unsupported mechanics.
- Do not treat art direction as proof of gameplay.
- Keep requirements implementable by a small prototype team.
