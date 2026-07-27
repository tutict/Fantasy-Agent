# Project Engineering Context

Status: active

Project ID: `PROJECT-EXP-008`

## Problem

Path-only Creative Review approval survives replacement of the approved artifact's bytes.

## Users and Actors

Creative reviewer, manifest producer, Godot ingest executor, experiment Supervisor,
Workers, Reviewers, and Integrator.

## Core Use Cases

Approve reviewed bytes; ingest unchanged approved bytes; reject same-path replacement.

## Included Scope

Canonical SHA-256 artifact identity, manifest production, Godot ingest enforcement,
deterministic tests, governance, review, and evaluation.

## Excluded Scope

Real engines/editors, Blender, ComfyUI, remote MCP, Unreal manifest ingest, migration,
release, deployment, main changes, and `EXP008-PATH-001` repair.

## Domain Model

### Entities

Approval manifest and asset approval decision.

### Value Objects

Artifact identity: algorithm plus lowercase hexadecimal digest.

### Aggregates

The manifest owns its approval decisions; each decision binds one reviewed artifact identity.

### Domain Events

Review decision recorded; ingest accepted; stale approval rejected.

### Business Invariants

Reviewed identity equals manifest identity equals ingest-time identity; missing or mismatched
identity cannot authorize ingest.

## Data

### Sources

Local artifact bytes, Creative Review bundle, and JSON approval manifest.

### Ownership

Producer owns recorded identity; consumer owns ingest-time enforcement.

### Lifecycle

Identity is calculated at manifest creation and re-calculated immediately before ingest.

### Consistency

Canonical SHA-256 representation must be identical across owners.

### Retention

Existing manifest-file retention only; no new persistence service.

### Migration

Legacy path-only manifests fail closed at the approval-required ingest boundary.

## Concurrency

### Shared Resources

Artifact paths and manifest files.

### Race Conditions

Replacement after verification is outside this bounded local-copy model and remains disclosed.

### Idempotency

Hashing and validation are deterministic for stable bytes.

### Ordering

Review bytes, create manifest, then verify current bytes before copy.

### Locking or Optimistic Concurrency

No locking added; the identity comparison is the bounded optimistic check.

## Identity and Permissions

### Authentication

Not applicable to local files.

### Roles

Reviewer authorizes; producer records; executor enforces.

### Resource Ownership

The approval decision names the asset and binds its content identity.

### Authorization Rules

Approval decision, allowed path, and matching content identity are all required.

### Audit Requirements

Tests and Delivery claims identify command, file, evidence, and Git boundary.

## Security

### Trust Boundaries

Creative Review output to manifest; manifest plus current filesystem to engine ingest.

### Sensitive Data

None expected; digests are not secrets.

### Input Risks

Path substitution, malformed digest, missing file, stale or legacy manifest.

### Secret Handling

No credentials or secrets are introduced.

### Abuse Cases

Replace approved bytes at the same path and attempt ingest with an old manifest.

## Observability

### Logs

Existing execution error/evidence output only.

### Metrics

Test counts and experiment coordination counts.

### Traces

Manifest identity and focused test evidence; no sensitive byte content.

### Audit Events

Approval creation and mismatch rejection are represented in deterministic evidence.

### Alerts

Not applicable.

## Delivery and Operations

### Deployment

Excluded.

### Configuration

No new environment configuration.

### Health Checks

Focused, integration, full pytest, and Ruff selections.

### Rollback

Revert the bounded experiment commits; no data migration.

### Gray Release

Not applicable.

### Data Rollback Limitations

No production data mutation.

## Evolution

### API Compatibility

Manifest schema changes require explicit Compatibility Review; path-only legacy behavior
must not silently authorize content.

### Schema Migration

No migration layer; fail-closed behavior is intentional and tested.

### Version Strategy

No package or release version change.

### Deprecation

Path-only approval authority becomes invalid for ingest.

### Extension Points

Canonical identity helper can be reused by future adapters after separate contracts.

## Team Boundaries

### Module Ownership

Worker A owns producer contract/workflow; Worker B owns approval filter/executor.

### Review Ownership

Independent Spec, Standards, Security, and Compatibility Reviewers are read-only.

### Integration Ownership

Root Integrator records and verifies boundaries but writes no product code.

### Release Responsibility

No release is authorized or required.

## Architecture Profile

### Domain Modeling

Small immutable value contract; no broader DDD structure.

### Backend Architecture

Shared pure hashing/validation API with producer and consumer adapters.

### Frontend Architecture

Frontend change is limited to Studio Hook target propagation and its request-body test; no visual redesign is included.

### Dependency Injection

Not added; filesystem inputs are explicit paths.

### Performance Strategy

Streaming SHA-256 avoids loading large artifacts into memory.

### Explicitly Rejected Patterns

Path-only trust, duplicate hashing algorithms, permissive legacy fallback, and framework additions.

## Engineering Concern Matrix

| Concern | Impact | Required Work | Reviewer |
|---|---|---|---|
| Business Rules | stale approval | identity invariant | Spec |
| Data | digest representation | canonical SHA-256 | Standards |
| Permissions | approval authority | fail closed | Security |
| Security | same-path substitution | negative-path integration | Security |
| Version Evolution | legacy manifest | explicit compatibility decision | Compatibility |
| Team Collaboration | cross-owner API | contracts and Integration Record | Spec/Standards |

## Project Acceptance Criteria

### Project Functional Acceptance

Unchanged reviewed bytes ingest; missing/malformed/mismatched identity rejects.

### Project Engineering Acceptance

Non-overlapping Deliveries, integration proof, permanent and selected specialist reviews.

### Project Delivery Acceptance

Four coherent commits (baseline, initial product, rework, governance/final), experiment-branch push, truthful RESULTS, clean worktree, no release.

## Baseline Evidence

- Repository/Environment/Scope: `docs/experiments/looppilot-exp-008/BASELINE-AND-VERIFICATION-SURFACE.md`.
- Pre-existing product failures: none in corrected baseline.
- Incidents: GraalPy bootstrap, pytest temp finalization, and Ruff cache ACL EII.

## Verification Surface

- Default/focused/full coverage: baseline document and Loop Contract.
- Unreached behavior: real external engines and remote services.

## Mode Selection

- Mode: Full Loop.
- Evidence: `docs/experiments/looppilot-exp-008/MODE-SELECTION.md`.
- Product Risk / Coordination Necessity: high / high.
- Decision by Supervisor and recorded by Integrator: 2026-07-26.

## Delivery Mode

- Release required: no.
- Deployment required: no.

## Project Closure Relationships

### Mandatory Loops

`LOOP-001` only.

### Cross-Loop Validation

- Not required for this one-Loop bounded Project; Loop integration is still mandatory.

### Release Requirement

- Not applicable; authority and execution evidence: none.

### Final Checkpoint

- `.looppilot/CHECKPOINT.md`; terminal condition is final closure or explicit block.

### Final Delivery Report

- `docs/experiments/looppilot-exp-008/RESULTS.md`, required status final.

### Project Status Authority

`PROJECT.md` is the only authority for Project status.

### Project Closure Gate

Loop closed, all mandatory review axes resolved, validation complete, closure review delivered,
commits/push observed, and residuals disclosed.

## Full Loop Relationships

### Project Identifier

`PROJECT-EXP-008`.

### Loop Map

`.looppilot/LOOP-MAP.md`.

### Current Authoritative Files

Project: this file; Loop: `LOOP-MAP.md`; Task/Finding: LOOP-001 Ledgers; recovery: `CHECKPOINT.md`.

### Project Closure

Closure R0 found a blocking public FBX-to-GLB identity-contract gap and governance/evidence
inaccuracies. TASK-008/011/009/012 rework is integrated in INTEGRATION-003; TASK-010
governance revision 2/2 is under review after R1 NOT-CLOSEABLE; full validation passed.
Project Closure is not reached.
