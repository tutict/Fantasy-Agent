# EXP-008 Mode Selection

Decision: FULL LOOP SELECTED

Selected candidate: Candidate A — Approval Identity / Stale Artifact Gate

Decision date: 2026-07-26

## Product Risk

Product Risk is high for this bounded trust decision: bytes at an approved path can change
while the path-only approval remains valid. This sets Security and Compatibility review and
negative-path evidence depth. Product Risk alone does not select Full Loop.

## Coordination Necessity

Coordination Necessity is high.

| Question | Evidence |
| --- | --- |
| Multiple implementation owners required | Approval authority produces identity; ingest enforcement consumes it at a separate trust boundary. |
| Independent Worker value | One binds reviewed bytes; one rejects ingest-time substitution. |
| File ownership separation | Contract/workflow/Studio producer paths versus manifest/executor consumer paths |
| Independently verified Deliveries | Producer schema/serialization tests and consumer mismatch tests |
| Non-trivial ordering | Consumer depends on producer's canonical algorithm, representation, and compatibility policy. |
| Dedicated Integration Record | Only a combined test proves creation, unchanged acceptance, replacement, and rejection. |
| Active recovery | Two Task states, failure budget, fallback ownership, reviews, and frozen boundaries must survive handoff. |
| Formal Rework | Not predicted as fact; integration RED must return to the owning Worker. |
| Single-owner insufficiency | One owner could make producer and consumer agree by construction without independent contract pressure. |
| Cost | Two contracts/Deliveries, integration, four review axes, and checkpoints |
| Benefit | Traceable authority/enforcement ownership and executable invariant evidence |

## Independent Deliveries

- Worker A: canonical artifact-identity contract and manifest creation from reviewed bytes,
  with producer-focused tests.
- Worker B: ingest-time identity verification and stale/substituted artifact rejection,
  with consumer-focused tests.

Primary writes do not overlap. Worker B may read Worker A's published API and depends on
that boundary, but may not edit Worker A-owned files.

## Integration-Only Proof

Formal integration must: write an artifact, build its approval manifest, accept unchanged
bytes, replace bytes at the same path, and reject the stale approval. Only this proves:

`reviewed artifact identity = manifest identity = ingest-time artifact identity`.

Worker-local tests cannot close that invariant.

## Why Full Loop, Not Lightweight

Lightweight can add specialist review but does not provide authoritative per-Task ownership
and Delivery state, a formal integration boundary, or failed-delegation/fallback history for
two implementation owners. Those controls, not a security keyword or file count, justify
Full Loop.

## Contract Barrier Entry Conditions

Before implementation: create two non-overlapping Task Contracts; define the invariant and
DAG; pre-register reciprocal fallback after formal reassignment; limit unchanged unsuccessful
delegation to two attempts; keep Supervisor/Integrator non-implementing and Reviewers
read-only; select Spec, Standards, Security, and Compatibility review; then record the first
Checkpoint.

Mode Selection is recorded. The Full Loop tree may now be initialized; the Contract Barrier
has not yet been claimed as passed.
