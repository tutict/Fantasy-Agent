# CONTEXT COMPACTION MANIFEST

## Identity

- Manifest ID: `CONTEXT-001`
- Checkpoint: `CHECKPOINT-001`
- Project / Loop: `PROJECT-EXP-008` / `LOOP-001`
- Created by: Integrator, 2026-07-26
- Manifest Status: ready

## Current Objective and Load Profile

- Objective: complete two-owner approval identity change and integration.
- Mode/profile: Full Loop / Full Loop profile.

## Must Load

| Artifact | Source | Reason | Revalidate |
|---|---|---|---|
| User request | attachment | authority/acceptance | yes |
| PROJECT, LOOP-MAP, LOOP-CONTRACT | `.looppilot` | scope/status/invariant | yes |
| Task/Finding Ledgers and active Task | LOOP-001 | ownership/next action | yes |
| CHECKPOINT | `.looppilot/CHECKPOINT.md` | exact resume | yes |

## Load On Demand

| Artifact | Trigger | Reason |
|---|---|---|
| Deliveries/Reviews/Integration | after creation | evidence and decisions |
| Baseline/audit/mode docs | evidence dispute | observed selection basis |

## Must Not Load by Default

- Full conversation, raw logs, unrelated files, superseded checkpoints, EXP-007 detail.

## Authoritative Sources

Project `PROJECT.md`; Loop `LOOP-MAP.md`; Task/Finding LOOP-001 Ledgers; recovery `CHECKPOINT.md`.

## Relevant Detailed Artifacts

- Task Contracts are must-load at dispatch; evaluation artifacts are on-demand until closure.

## Compacted Facts

- FACT-001: corrected baseline is 159 passed; source baseline document; revalidate at closure.
- FACT-002: Candidate A path-only stale approval reproduced; source candidate audit.
- FACT-003: two non-overlapping owner contracts approved; source LOOP-CONTRACT and Tasks.

## Discarded or Archived Context

- Large raw command output and intermediate candidate search notes.

## Uncertainty and Revalidation

- Real external tools remain unverified; do not infer them from mocked tests.

## Token and Context Rationale

- Context signal: no host token measurement; selection is minimal Full Loop recovery set.
- Risks: over-compaction could hide authority; under-compaction could import irrelevant logs.

## Authority Note

This manifest selects context only; it owns no status or permissions.
