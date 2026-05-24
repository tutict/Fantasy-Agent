# Gameplay Designer Skill

Use this skill when converting a raw game idea into a scoped gameplay spec.

## Responsibility

Generate the playable loop:

- Player fantasy
- Core verbs
- Player decisions
- Systems and feedback
- Pacing and progression
- Win and failure states

## Inputs

- Prompt text
- Target session length
- Engine/platform constraints
- Jam-scope constraints

## Outputs

- `GameplaySpec`
- YAML matching `gameplay-schema.yaml`
- Risks and assumptions

## Workflow

1. Identify the smallest playable fantasy.
2. Select three to five core verbs.
3. Build a loop where each verb changes a decision.
4. Add pressure that creates meaningful failure.
5. Define three level beats.
6. List only assets required to test the loop.

## Guardrails

- Cut mechanics that do not interact.
- Cut content that cannot be tested in a greybox.
- Keep the first prototype finishable in 5 to 15 minutes.
