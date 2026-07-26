# LoopPilot EXP-007 Experiment Plan

## Objective and boundaries

EXP-007 tests whether the Phase 9 separation of Product Risk from Coordination
Necessity transfers to Fantasy-Agent's Python/FastAPI/Pydantic/PyYAML stack. The
experiment will make at most one independently acceptable bounded product change.
LoopPilot remains frozen and read-only at
`2275e747e73936ebb8f0b24e5fb901a619b6adf8`.

The original Fantasy-Agent `main` worktree has pre-existing changes in ten files.
They are excluded. Work runs in the isolated
`C:\tmp\Fantasy-Agent-exp-007` worktree on
`experiment/looppilot-fantasy-agent-exp-007`, based on observed `origin/main`
`4355dd6d70a58477673f2a6e29c923219d3e8801`.

No real Blender, ComfyUI, Unreal, Godot, GPU generation, remote MCP, deployment,
release, merge, or pull request is authorized. External execution may be represented
only by deterministic fakes or mocks in temporary filesystems.

## Pre-registered hypotheses

- **H1 - Cross-stack Mode Transfer.** Phase 9 mode selection applies to this
  Python/FastAPI/Pydantic/MCP repository.
- **H2 - Product Risk != Full Loop.** High Product Risk increases review,
  validation, and evidence depth but does not alone require Full Loop.
- **H3 - Coordination Necessity.** Multiple implementation owners, formal
  integration, active recovery, structured rework, or non-trivial ownership
  boundaries primarily drive Full Loop.
- **H4 - Specialist-reviewed Lightweight.** High Product Risk plus one owner, a
  bounded change, and deterministic verification can legitimately use Lightweight
  with the matching specialist review.
- **H5 - Verification Surface Transfer.** The verification surface can honestly
  distinguish pytest, ruff, CLI characterization, integration-like tests, optional
  dependencies, and external-tool validation.
- **H6 - Product-Agent / Governance-Agent Separation.** Fantasy-Agent product
  agents do not become LoopPilot governance roles.
- **H7 - Worker Claim Reliability.** A governance Worker claim enters authoritative
  state only after code, test, or command evidence verifies it.
- **H8 - Artifact Accounting.** Product, governance, and evaluation artifacts can
  be counted separately in this third project.

Each hypothesis will be classified exactly once as `supported`, `contradicted`,
`inconclusive`, or `not exercised`. Counterevidence has equal priority.

## Method

1. Record repository, raw, environment-corrected, and scope-focused baselines.
2. Audit Candidates A-E and search explicitly for counterexamples.
3. Score Product Risk and Coordination Necessity independently; choose only among
   Lightweight, Full Loop, and No implementation justified.
4. If a real gap is selected, use characterization -> one real RED -> minimal GREEN
   -> focused regression through a public interface.
5. Run Spec, Standards, one matching specialist, and Evidence/Factual Accuracy
   reviews. Review statements must cite reproducible evidence.
6. Run the reachable full verification surface and disclose all unreachable real
   external-tool paths.

## Stop and escalation conditions

Lightweight stops for a Major or Blocker finding, a required second implementation
owner, formal integration, multiple-runtime implementation, active recovery,
repeated same-class correction, or contract drift. Any escalation will preserve the
original mode decision and evidence. No artificial Worker failure will be induced.

## Pre-implementation status

The audit selected Candidate E: a credential-bearing local ComfyUI endpoint is
accepted by the planning interface and can flow into a writable run manifest. The
bounded change will reject URL credentials without echoing them. Candidate C also
has a real path-identity weakness, but complete artifact binding would require a
broader review-to-execution contract and is excluded from this one-change experiment.
