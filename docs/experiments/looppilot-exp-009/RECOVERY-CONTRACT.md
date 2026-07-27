# EXP-009 Fresh Recovery Contract

Status: `PREREGISTERED`

Mode: `Lightweight`

## Objective

Without changing EXP-008 state or the product tree, determine whether a fixed Evidence
Inventory can produce an accurate, reproducible, and independently reviewable recovery
conclusion for product HEAD `52173e08ae267700ef62e7e563ab6a50523981ad` and the archived
EXP-008 R2/Closure boundary.

## Before and After

Before: EXP-008 is `BLOCKED-WITH-VERIFIED-PARTIAL-DELIVERY`; TASK-010 is blocked with
revision `2 / 2` exhausted; STD-001 and EVID-001 are open historical Findings.

After: EXP-009 may become `RECOVERY-ACCEPTED`,
`RECOVERY-ACCEPTED-WITH-DISCLOSED-RESIDUALS`, or `RECOVERY-BLOCKED`. EXP-008 remains
blocked in every case. This Contract is not TASK-010 R3.

## Included Scope

- `docs/experiments/looppilot-exp-009/**`.
- Four to seven minimal Lightweight governance artifacts.
- Read-only Git-derived evidence from the frozen inventory.
- One Evidence Owner for inventory derivation, reconciliation, and results drafting.
- One new independent read-only Reviewer after candidate freeze.

## Excluded Scope

- Writes under `fantasy_agent/**`, `tests/**`, or `apps/**`.
- Frontend or runtime changes.
- Changes to EXP-008 commits, TASK-010 status/budget, main, or LoopPilot.
- Real external tools, full product tests, release, deployment, merge, PR, tag, or force push.
- Full Loop Ledgers, Finding machinery, Integration records, or Project Closure machinery.

`PRODUCT` inventory members are read-only historical evidence, not writable scope.

## Inventory Contract

`EVIDENCE-INVENTORY.tsv` is the only canonical member list. Every included row records
path, category, source commit/tree, SHA-256, physical lines, bytes, and purpose. Categories
are `PRODUCT`, `AUTHORITATIVE_GOVERNANCE`, `SUPPORTING_GOVERNANCE`, `REVIEW`,
`EVALUATION`, and `RECOVERY`; `EXCLUDED` denotes the scopes above and is never an
included evidence row.

Membership freezes in the preregistration commit. Any later need for a new member makes
the result `RECOVERY-BLOCKED`; membership must not be silently expanded. Numeric totals
never substitute for membership validation.

## Historical Invariants

- Product HEAD remains `52173e08ae267700ef62e7e563ab6a50523981ad`.
- EXP-008 archival base remains `8b6075aaee8e86a6c7905911487e537672a4125b`.
- Frozen R2 tree remains `4a874844744f92d60378d48aaa6787334942eb24`.
- Closure R2 remains Spec PASS, Standards FAIL, Evidence FAIL, `NOT-CLOSEABLE`.
- TASK-010 remains blocked at revision `2 / 2`.
- STD-001/EVID-001 remain open historical Findings.
- STD-002/EVID-002 remain R2 `VERIFIED-CORRECTED`.
- EXP-008 EII 1-49 are verified; group 50 is reported and not independently reviewed.

## Review and Correction

The candidate must receive independent `Spec`, `Standards`, and `Evidence/Factual
Accuracy` judgments. Each axis returns PASS, PASS-WITH-FINDINGS, FAIL, or BLOCKED.
Only all PASS may proceed to accepted closure. At most one scoped correction may address
explicit Findings, followed by the same Reviewer's reverification. No second correction,
Reviewer substitution, inventory expansion, product edit, or historical rewrite is allowed.

## Acceptance Evidence

- Clean, scoped Git boundary and unchanged product/test/frontend diff.
- Deterministic membership, SHA-256, physical-line, byte, count, and total validation.
- No stale present-tense claims or rewritten historical Findings.
- Four to seven governance artifacts and bounded evaluation artifacts.
- Three independent Review axes PASS.
- Honest EII, residual-risk, skipped-verification, and correction reporting.
