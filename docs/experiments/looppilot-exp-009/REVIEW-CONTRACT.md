# EXP-009 Independent Review Task Contract

Task ID: `EXP009-REVIEW-001`

Status: `APPROVED-FOR-DISPATCH-AFTER-CANDIDATE-COMMIT`

Supervisor: root

Assignee: one new independent Reviewer, bound in the dispatch message

## Objective

Review the commit with subject `docs: reconcile blocked Full Loop evidence inventory`
whose parent is preregistration commit `5a0347a7bf7161ac992e1dfa1ea86f68b634dc85`.
The Supervisor will supply the exact candidate commit and tree at dispatch.

Return independent judgments for:

1. Spec against `RECOVERY-CONTRACT.md`.
2. Standards against repository rules, scope, Lightweight proportionality, and stale-state discipline.
3. Evidence/Factual Accuracy against the frozen inventory and Git-derived facts.

## Allowed Scope

- Read candidate and historical repository files.
- Run read-only Git, text, hash, line, byte, and PowerShell validation commands.
- Run `validate-inventory.ps1` with a one-process execution-policy override if required.
- Report findings and a structured verdict to the Supervisor.

## Forbidden Scope

- Modify any file, index, commit, branch, worktree, tag, or remote.
- Run product tests, real external tools, release, deployment, merge, PR, or push.
- Delegate, spawn support Agents, substitute another Reviewer, or install a Skill.
- Change inventory membership, historical EXP-008 state, TASK-010, product, or review criteria.
- Announce parent completion.

## Required Evidence

- Recompute inventory count, membership hash, SHA-256, physical lines, and bytes.
- Verify Product HEAD, Archive A tree, Archive B/base ancestry, frozen inventory, and unchanged product/archive paths.
- Inspect all EXP-009 governance/evaluation artifacts for stale or rewritten historical claims.
- Assess the disclosed 12 Git-blob plus 2 CRLF-worktree Integration hash reconciliation.
- Confirm the governance/evaluation artifact sets and correction count.

## Deliverable

Return Reviewer identity, candidate commit/tree, commands actually run, each axis as
PASS, PASS-WITH-FINDINGS, FAIL, or BLOCKED, explicit Findings, evidence limits, and a
read-only statement. All three axes must PASS to permit accepted closure.

External research is not required: current external information cannot change the
fixed local Git evidence or Contract. No additional Skill is assigned.
