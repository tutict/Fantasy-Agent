# Mode Selection

## Selected task

Reject credential-bearing ComfyUI endpoint URLs at MCP planning and capability-probe
interfaces without contacting the endpoint, writing a manifest, or echoing the
credential-bearing URL.

## Product Risk (0-2 each)

| Factor | Score | Evidence |
| --- | ---: | --- |
| execution side effects | 1 | Execution remains confirmation-gated, but an accepted endpoint can later be contacted. |
| file-system write risk | 1 | `write_files=true` can serialize the endpoint into a run manifest. |
| external tool risk | 1 | The endpoint controls ComfyUI HTTP traffic. |
| security boundary | 2 | URL credentials are secret-bearing input at a local-tool trust boundary. |
| data/artifact integrity | 1 | A manifest can retain an unsafe endpoint value. |
| approval integrity | 0 | Creative Review approval decisions are not changed. |
| backward compatibility | 1 | Credential-bearing endpoint URLs will be newly rejected. |
| failure recovery | 1 | Failure must be fail-closed and provide a sanitized diagnostic. |

Total: 8/16. Qualitative Product Risk: **high**, driven by the security boundary
and potential credential persistence rather than the sum alone.

## Coordination Necessity (0-2 each)

| Factor | Score | Evidence |
| --- | ---: | --- |
| multiple implementation owners | 0 | One implementation owner can edit one Python module. |
| independent Worker value | 0 | Parallel implementation would add coordination cost, not independent value. |
| separable file ownership | 0 | Production code and its tests form one vertical slice. |
| integration ordering | 0 | No dependent implementation stream exists. |
| multiple runtime boundaries | 0 | No frontend, engine, or external runtime implementation changes. |
| dedicated Integration Record need | 0 | Focused and full verification are sufficient. |
| active recovery need | 0 | No recovery is active. |
| structured Rework likelihood | 0 | The acceptance contract is deterministic and narrow. |

Total: 0/16. Qualitative Coordination Necessity: **low**.

## Decision

Mode: **Lightweight + Security Review**.

High Product Risk increases security review depth, no-secret assertions, full
regression, and evidence depth. It does not create a second implementation owner.
Full Loop is rejected because there is no parallel delivery, formal integration,
active checkpoint/recovery, multiple contract, or structured rework evidence.
No implementation justified is rejected because a public-interface characterization
demonstrated a real accepted unsafe input.

Fantasy-Agent's ComfyUI Worker and other product agents remain product-domain roles.
They are not LoopPilot Workers. This implementation uses no delegated LoopPilot
Worker and therefore does not trigger Full Loop by product architecture.

## Escalation gate

Re-evaluate before continuing if implementation requires schema changes, frontend
changes, a second runtime/owner, a Major/Blocker review finding, formal integration,
or repeated correction. None is currently observed.
