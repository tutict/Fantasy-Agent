# Finding Ledger

Loop ID: `LOOP-001`
Status: blocked
Updated: 2026-07-27
Updated by: Integrator
Integrator: root

## Authority

- Finding status authority: `FINDING-LEDGER.md`
- Triage/disposition authority: Supervisor
- Recording authority: Integrator
- Integrator may accept risk or lower severity: no

## Finding Summary

| Finding ID | Category | Severity | Status | Reviewer | Affected Task | Rework Task | Decision | Verification | Duplicate Of |
|---|---|---|---|---|---|---|---|---|---|
| TASK001-SPEC-001 | Spec compatibility | major | closed | /root/exp008_task001_reviewer | TASK-001 | TASK-003 | corrected | VERIFIED-CORRECTED | none |
| LOOP001-STD-001 | Standards boundary | major | closed | /root/exp008_loop_standards_reviewer | LOOP-001 | TASK-004,TASK-005 | corrected | VERIFIED-CORRECTED | none |
| LOOP001-SEC-001 | Security containment | major | closed | /root/exp008_loop_specialist_reviewer | LOOP-001 | TASK-006,TASK-007 | corrected | VERIFIED-CORRECTED | none |
| EXP008-CLOSURE-SPEC-001 | Public FBX/GLB identity contract | major | closed | /root/exp008_closure_reviewer | LOOP-001 | TASK-008,TASK-009 | corrected | R1 VERIFIED-CORRECTED | none |
| EXP008-CLOSURE-STD-001 | Closure governance consistency | major | open | /root/exp008_closure_reviewer | LOOP-001 | TASK-010 | budget exhausted | R2 NOT VERIFIED-CORRECTED | none |
| EXP008-CLOSURE-STD-002 | Reviewer delegation discipline | major | closed | /root/exp008_closure_reviewer | LOOP-001 | TASK-010 | support excluded and disclosed | R2 VERIFIED-CORRECTED | none |
| EXP008-CLOSURE-EVID-001 | Governance physical-line count | minor | open | /root/exp008_closure_reviewer | LOOP-001 | TASK-010 | budget exhausted | R2 NOT VERIFIED-CORRECTED | none |
| EXP008-CLOSURE-EVID-002 | Closure EII accounting | minor | closed | /root/exp008_closure_reviewer | LOOP-001 | TASK-010 | recorded 49 | R2 VERIFIED-CORRECTED | none |
| TASK008-SPEC-001 | Target semantics and compatibility | major | closed | /root/exp008_task008_reviewer | TASK-008 | TASK-011 | corrected | VERIFIED-CORRECTED | none |
| LOOP001-COMP-001 | Studio target propagation | major | closed | /root/exp008_loop_specialist_r2 | LOOP-001 | TASK-012 | corrected | VERIFIED-CORRECTED | none |

## Severity Summary

- Blocker: 0
- Major: 8
- Minor: 2
- Suggestion: 0

## Open Blockers

- `EXP008-CLOSURE-STD-001` remains open and blocks acceptance.

## Accepted Risks

- None.

## Deferred Findings

- `EXP008-PATH-001` is an evaluation-level Test Harness Finding outside LOOP-001 scope.

## Duplicate Relationships

- None.

## Review Barrier Status

- Closure R2 passed Spec but failed Standards and Evidence/Factual Accuracy.
- STD-002 and EVID-002 are closed; STD-001 and EVID-001 remain open.

## Closure Barrier Relationship

- Closure ready: no; Closure R2 is `NOT-CLOSEABLE` and TASK-010 budget is exhausted.
- Unresolved Blocker must be zero; Major requires an explicit permitted disposition.

## Ledger Notes

- Reviewers preserve judgments; Integrator only records Supervisor-authorized transitions.
