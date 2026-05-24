# UE Architect Skill

Use this skill when preparing Unreal Engine project architecture from a gameplay spec.

## Responsibility

Define UE5 project structure and automation handoffs.

## Inputs

- `GameplaySpec`
- `UnrealProjectPlan`
- Generated asset import manifest

## Outputs

- UE folder plan
- Required plugins
- Map list
- Blueprint class list
- Data asset plan
- Unreal Python or MCP execution steps

## Guardrails

- Blueprint-first unless performance requires C++.
- Keep mechanics in independent actors or components.
- Expose tunables for playtesting.
- Run validation commandlets before packaging.
