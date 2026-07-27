# EXP-009 State

Status: `CANDIDATE-AWAITING-INDEPENDENT-REVIEW`

- Branch: `experiment/looppilot-fantasy-agent-exp-009`.
- Base: `8b6075aaee8e86a6c7905911487e537672a4125b`.
- Mode: `Lightweight`.
- Current phase: evidence candidate frozen by the commit containing this State; independent Review pending.
- Evidence Owner: root.
- Independent Reviewer: pending candidate freeze.
- Correction budget: `0 / 1` used.
- EXP-009 EII: 8 phase/cause groups observed; all recovered.
- Inventory membership: frozen by preregistration commit `5a0347a7bf7161ac992e1dfa1ea86f68b634dc85`.
- Recovery conclusion: not yet determined.

Historical authorities remain EXP-008 inputs and are not modified by this state file.
EXP-008 remains `BLOCKED-WITH-VERIFIED-PARTIAL-DELIVERY`; TASK-010 remains blocked at
revision `2 / 2`.

## EXP-009 EII

1. Local policy blocked direct execution of the unsigned experiment script.
2. The initial validator treated scalar Git output as an indexable string array.
3. Repeated identical sandbox-helper refresh failures blocked patch application; coalesced.
4. The local apply-patch entry was denied inside the sandbox.
5. The elevated batch wrapper rejected stdin instead of a UTF-8 patch argument.
6. The batch wrapper flattened the multiline patch terminator.
7. Direct engine invocation required Windows-safe escaping for embedded quotes.
8. Candidate artifact comparison returned null on equality under PowerShell strict mode.

These incidents changed no product, historical artifact, index, commit, or remote state.
The corrected validator completed successfully through a one-process execution-policy
override; no system execution policy was changed.
