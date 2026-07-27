# Finding Ledger

Loop ID: `LOOP-001`
Status: active
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
| EXP008-CLOSURE-STD-001 | Closure governance consistency | major | open | /root/exp008_closure_reviewer | LOOP-001 | TASK-010 | revision 2 required | R1 NOT VERIFIED; R2 pending | none |
| EXP008-CLOSURE-STD-002 | Reviewer delegation discipline | major | open | /root/exp008_closure_reviewer | LOOP-001 | TASK-010 | exclude support output and disclose | R2 pending | none |
| EXP008-CLOSURE-EVID-001 | Governance physical-line count | minor | open | /root/exp008_closure_reviewer | LOOP-001 | TASK-010 | final post-R1 accounting | pre-R1 VERIFIED; R2 pending | none |
| EXP008-CLOSURE-EVID-002 | Closure EII accounting | minor | open | /root/exp008_closure_reviewer | LOOP-001 | TASK-010 | record 49 and later incidents | pre-R1 VERIFIED; R2 pending | none |
| TASK008-SPEC-001 | Target semantics and compatibility | major | closed | /root/exp008_task008_reviewer | TASK-008 | TASK-011 | corrected | VERIFIED-CORRECTED | none |
| LOOP001-COMP-001 | Studio target propagation | major | closed | /root/exp008_loop_specialist_r2 | LOOP-001 | TASK-012 | corrected | VERIFIED-CORRECTED | none |

## Severity Summary

- Blocker: 0
- Major: 8
- Minor: 2
- Suggestion: 0

## Open Blockers

- `EXP008-CLOSURE-STD-001` and `EXP008-CLOSURE-STD-002` block acceptance.

## Accepted Risks

- None.

## Deferred Findings

- `EXP008-PATH-001` is an evaluation-level Test Harness Finding outside LOOP-001 scope.

## Duplicate Relationships

- None.

## Review Barrier Status

- Closure R1 passed Spec but failed Standards and Evidence/Factual Accuracy. The R0
  Spec Finding is closed; governance/evidence Findings require TASK-010 revision 2 and R2.

## Closure Barrier Relationship

- Closure ready: no; Closure R1 is `NOT-CLOSEABLE` pending TASK-010 revision 2 and R2.
- Unresolved Blocker must be zero; Major requires an explicit permitted disposition.

## Ledger Notes

- Reviewers preserve judgments; Integrator only records Supervisor-authorized transitions.
