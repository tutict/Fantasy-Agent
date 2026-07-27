# LoopPilot Phase 10 / EXP-008 Results

Status: Closure R1 NOT-CLOSEABLE; TASK-010 revision 2 under review

Date: 2026-07-27

These conclusions apply only to the selected Fantasy-Agent change and observed
environment. They do not generally validate Full Loop.

## Required Results 1-25

1. **EXP-007 closure:** HEAD `796b69e06b382d1e2ae03c58cb6a3e35fa9605fd`;
   historical independent verdict `CLOSEABLE-WITH-DISCLOSED-RESIDUAL-FINDINGS`.
2. **EXP-008 base:** `4355dd6d70a58477673f2a6e29c923219d3e8801`, equal to the
   observed frozen `origin/main`; a later refresh failed on `FETCH_HEAD` ACL and is unverified.
3. **LoopPilot frozen SHA:** `2275e747e73936ebb8f0b24e5fb901a619b6adf8`, observed clean/read-only.
4. **Branch/worktree:** `experiment/looppilot-fantasy-agent-exp-008` in
   `C:\tmp\Fantasy-Agent-exp-008`.
5. **Original main:** observed at the base with the same ten modified paths before/after;
   no experiment write targeted it. Byte equality was not independently hash-proven.
6. **Repository baseline:** 159 collected; three displayed failures before a Windows temp
   finalization timeout. This incomplete run is EII evidence, not authoritative Product failure.
7. **Environment-corrected baseline:** CPython 3.12.13; 159/159 passed in 13.32 s and
   full-scope Ruff passed without dependency changes.
8. **Scope baseline:** approval selection 7 passed/45 deselected; planning CLI and frontend
   typecheck/build passed.
9. **Verification surface:** pytest `tests`, Ruff `fantasy_agent tests apps`, planning-only
   CLI, frontend checks, and generated/temp behavior; real tools excluded.
10. **Candidate A:** reproduced path-only approval surviving changed bytes; passed Full Loop gate.
11. **Candidate B:** real version mismatch but migration/diff/approval design was too broad.
12. **Candidate C:** no deterministic cross-owner inconsistency was proven.
13. **Candidate D:** real confirmation/operation identity gap but broader public redesign.
14. **Candidate E:** external runtime validation would dominate the experiment.
15. **Selected candidate:** A, Approval Identity / Stale Artifact Gate.
16. **Rejected reasons:** B breadth; C no proven gap; D public-semantics breadth; E real-tool dominance.
17. **Product Risk:** high due stale authorization and producer local-read trust boundary.
18. **Coordination Necessity:** high due separate producer and consumer authority.
19. **Why Full Loop:** real owners, DAG, integration, independent review, Rework, and recovery.
20. **Why not Lightweight:** authoritative Task ownership, formal integration, and delegated
   failure/fallback history were required.
21. **Task DAG:** 001/002 initial owners; 003-007 prior Rework; Closure R0 drove 008,
   target-aware producer correction 011, public-flow proof 009, then governance-only 010.
22. **Workers:** 2 real owners; no decorative third Worker.
23. **Ownership:** Worker A producer surfaces; Worker B consumer/integration surfaces;
   primary cross-Worker product-file overlap remained zero.
24. **Worker assignments:** 11 scoped assignment turns.
25. **Deliveries:** 11 valid Deliveries; 10 independently approved outcomes. TASK-008 was
   reviewable but failed Spec/Standards and was superseded by approved TASK-011.

## Required Results 26-50

26. **Unsuccessful unchanged attempts:** 0; Findings, REDs, dependencies, and EII remain separate.
27. **Zero-output Worker attempts:** 0.
28. **EII:** 49 phase/cause groups through R2 freeze; final pending R2.
   All recovered except the optional fresh origin refresh; none invalidated a Delivery.
29. **Failure Budget:** maximum two unsuccessful unchanged attempts, preregistered.
30. **Budget trigger:** not exercised; no third retry occurred.
31. **Fallback:** reciprocal implementation reassignment preregistered; Reviewer/Integrator forbidden.
32. **Fallback trigger:** not exercised.
33. **Ownership collapse:** preregistered after budget exhaustion without role collapse.
34. **Collapse trigger:** not exercised.
35. **Ownership history:** two owners throughout; four Finding-driven Rework waves returned
   work to the owning Worker with no ownership transfer.
36. **Worker claims:** eleven Deliveries map claims to files, commands, tests, hashes, or boundaries.
37. **Unsupported claims:** none integrated; process authorship, external callers/tools,
   atomic copy, release, and deployment remain unverified.
38. **Integration:** `INTEGRATION-003` freezes fourteen paths/hashes; eight tracked
   rework paths plus one new Node test differ from product HEAD `068f25b`.
39. **Cross-owner invariant:** unchanged public `.fbx` review item maps to concrete Godot
   `.glb` bytes; reviewed = manifest = ingest identity; replacement rejects before copy.
40. **Findings:** EXP008-CLOSURE-SPEC-001 is R1 VERIFIED-CORRECTED; STD-001, new
   STD-002, EVID-001, and EVID-002 remain open. No Blocker is recorded.
41. **Spec:** INTEGRATION-003 R4 PASS, no Finding; 14 hashes and 86 Python/Node evidence.
42. **Standards:** INTEGRATION-003 R4 PASS; target/default, EOL, diff, hashes, Ruff passed.
43. **Specialists:** original R3 Security PASS, Compatibility PASS;
   `LOOP001-COMP-001` VERIFIED-CORRECTED, no new Finding.
44. **Rework:** caller bytes, EOL, containment, target-aware resolution, public-flow proof,
   and governance/accounting reconciliation are preserved as formal history.
45. **Original Reviewer return:** TASK-011 and Specialist corrections returned to their
   original Reviewers; Closure R1 returned NOT-CLOSEABLE and the same Reviewer owns R2.
46. **Checkpoint:** current recovery authority is `CHECKPOINT-028` after Closure R1.
47. **Recovery:** conversation compaction resumed from rechecked authorities, hashes, tests,
   Git state, and current permission scope.
48. **Focused tests:** producer 12, adjacent 8, TASK-009 2, and fixed integration 86 passed
   in their recorded boundaries; focused Ruff/diff checks passed.
49. **Integration tests:** public-flow Python file 2 passed; fixed Python boundary 86 passed
   in 9.86 s; Node request-body test passed; typecheck/build/static checks passed.
50. **Fresh full pytest:** 177 passed in 14.18 s, no failures/errors/skips summary.

## Required Results 51-75

51. **Fresh Ruff:** full `fantasy_agent tests apps` PASS with cache disabled.
52. **Frontend/build:** target propagation changed frontend; final typecheck PASS and Vite
   built 23 modules in 104 ms through the exact temporary dependency junction.
53. **External tools:** no real Blender, ComfyUI GPU, Godot/Unreal Editor, remote MCP,
   packaged playtest, release, or deployment was executed.
54. **Harness effects:** full pytest recreated ignored `s2,s3,s4`; `EXP008-PATH-001`
   reproduced. Exact sessions, build, junction, timestamp, and pycache cleanup passed.
55. **Product artifacts:** fourteen files, cumulative 813 insertions/24 deletions from
   `cec04ed`; rework commit `52173e08ae267700ef62e7e563ab6a50523981ad`.
56. **Governance artifacts:** pre-R1 68 files; pre-R2 70 files; final pending R2 artifact.
57. **Evaluation artifacts:** seven files: plan, baseline, candidate audit, mode selection,
   coordination observations, scorecard, and Results.
58. **Governance physical lines:** pre-R1 4,498; pre-R2 4,559 / 208,197 bytes; final pending
   R1/Finding/R2 artifacts. R0 independently established 42 files / 3,146 lines.
59. **H1-H8:** H1/H2/H3/H6/H7/H8 supported; H4/H5 not exercised.
60. **EXP-006 comparison:** about 8 attempts/4 zero-output/9 reported EII versus current
   EXP-008 11 valid/0 zero-output/49 grouped-through-R2-freeze; conventions/tasks differ.
61. **Phase 9 resilience:** supported only for observed mode gating, ownership, Rework,
   reviewer return, EII separation, recovery, and integration; budget recovery unexercised.
62. **Did Full Loop deliver?** Product rework, integration, reviews, commit, and validation
   yes; Closure R2 and governance commit/push remain pending.
63. **Governance value:** preserved ownership, exposed multiple Major correction paths, forced
   executable integration, and enabled recovery; final cost remains material and pending.
64. **Artifacts used:** Project/Contract/Mode, Ledgers, Task Contracts, Deliveries, Reviews,
   Integration, Findings, Checkpoint, Closure, and experiment reports.
65. **Low-value artifacts:** Checklist had the lowest marginal value; Handoff/Compaction
   were useful but duplicative. No claim says every line was necessary.
66. **Closure Review:** R0 failed all axes; R1 passed Spec but failed Standards/Evidence; R2 pending.
67. **Final state:** no terminal state; four Closure Findings remain open after R1.
68. **Recommendation:** preserve Phase 9; gather more real Full Loop cases with natural
   unsuccessful attempts before tuning retry/collapse.
69. **Protocol change:** not justified by this single case.
70. **Unverified:** post-hash TOCTOU, real GLB parsing/import, external/installed callers,
   Unreal manifest ingest, real tools, packaging/release/deploy, original-main byte equality,
   and fresh remote-main state after the ACL-blocked fetch.
71. **Commits:** `cec04ed` baseline, `068f25b` initial product, `52173e0` rework;
   governance/final pending.
72. **Current product HEAD:** `52173e08ae267700ef62e7e563ab6a50523981ad`; final pending.
73. **Push:** pending; only the experiment branch is authorized.
74. **Local/remote sync:** pending authorized push and verification.
75. **Final Git status:** expected rework/governance changes remain uncommitted; clean pending.

## Current Closure Boundary

INTEGRATION-003, all Loop axes, validation, product commits, and Closure R1 are observed.
TASK-010 revision 2, Closure R2, governance commit, push/sync, and final clean status
remain intentionally unclaimed.
