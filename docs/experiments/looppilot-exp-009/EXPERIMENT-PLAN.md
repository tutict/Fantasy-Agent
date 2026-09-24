# LoopPilot Phase 10 / EXP-009 Experiment Plan

Experiment: Evidence-Only Recovery From a Blocked Full Loop

Mode: `Lightweight`

## Research Question

Can a fresh Lightweight evidence contract recover trustworthy conclusions from an
archived blocked Full Loop without reopening the old Task, changing product bytes, or
rewriting the blocked experiment?

EXP-009 success is not EXP-008 success. `RECOVERY-ACCEPTED` is not EXP-008 Closure.

## Fixed Starting Boundary

- EXP-008 archival base: `8b6075aaee8e86a6c7905911487e537672a4125b`.
- EXP-008 archival tree: `aeb86d86782377d7fac7101f931e14cda9d1fb4a`.
- Product HEAD: `52173e08ae267700ef62e7e563ab6a50523981ad`.
- Frozen R2 tree: `4a874844744f92d60378d48aaa6787334942eb24`.
- LoopPilot frozen HEAD: `2275e747e73936ebb8f0b24e5fb901a619b6adf8`.
- EXP-008: `BLOCKED-WITH-VERIFIED-PARTIAL-DELIVERY`.
- TASK-010: blocked; revision `2 / 2` exhausted.

## Mode Decision

Product Risk and Coordination Necessity for the recovery work are low. Product, tests,
and frontend are read-only; one Evidence Owner can derive the evidence; one independent
Reviewer supplies the three required judgments. Full Loop Ledgers, Integration records,
and Closure machinery would add projections without adding implementation coordination.

## Preregistered Hypotheses

| ID | Hypothesis |
|---|---|
| H1 | A fixed Evidence Inventory reduces stale governance projections. |
| H2 | Artifact accounting needs numeric totals and the membership set together. |
| H3 | Evidence-only blocked recovery does not require Full Loop. |
| H4 | A fresh Contract can preserve EXP-008 as blocked while producing an independent recovery conclusion. |
| H5 | A fixed inventory plus executable consistency checks avoids the TASK-010 R1/R2 omission type. |
| H6 | A smaller governance surface reduces new stale-state risk. |

Final classifications are `supported`, `contradicted`, `inconclusive`, or
`not exercised`.

## Controls and Measurements

- Freeze inventory membership in the first EXP-009 commit, before reconciliation.
- Derive every inventory row from Git blob bytes.
- Validate path membership, SHA-256, physical lines, and bytes together.
- Keep exactly one Evidence Owner and no implementation Worker.
- Freeze one candidate and obtain independent Spec, Standards, and Evidence/Factual
  Accuracy review.
- Permit at most one scoped correction and require the same Reviewer's reverification.
- Treat any required inventory-member addition after freeze as `RECOVERY-BLOCKED`.
- Record EXP-009 EII separately from historical EXP-008 EII.

## Decision Rule

All acceptance invariants and all three Review axes must PASS for
`RECOVERY-ACCEPTED`. Disclosed non-blocking residuals may produce
`RECOVERY-ACCEPTED-WITH-DISCLOSED-RESIDUALS`. A membership change, exhausted correction,
unavailable required Reviewer, product change, or failed invariant produces
`RECOVERY-BLOCKED`.
