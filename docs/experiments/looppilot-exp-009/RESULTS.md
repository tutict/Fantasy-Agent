# EXP-009 Final Results

Status: `RECOVERY-ACCEPTED-WITH-DISCLOSED-RESIDUALS`

1. **EXP-008 Product HEAD:** `52173e08ae267700ef62e7e563ab6a50523981ad`.
2. **EXP-008 R2 tree:** `4a874844744f92d60378d48aaa6787334942eb24`.
3. **EXP-008 Archive Commit A:** `ebf2a60266342cf90a76dd34c5dece732d54f2ed`.
4. **EXP-008 Archive Commit B:** `8b6075aaee8e86a6c7905911487e537672a4125b`.
5. **EXP-008 archival HEAD:** Archive Commit B.
6. **EXP-008 remote sync:** observed `0 0` before EXP-009 branch creation.
7. **EXP-008 state:** `BLOCKED-WITH-VERIFIED-PARTIAL-DELIVERY`, permanent.
8. **TASK-010:** blocked, revision `2 / 2` exhausted.
9. **STD-001:** open historical Major Finding; primary `TASK_CONTRACT`.
10. **EVID-001:** open historical incorrect governance claim; primary `EVIDENCE_GAP`.
11. **EXP-009 base:** Archive Commit B.
12. **EXP-009 branch:** `experiment/looppilot-fantasy-agent-exp-009`.
13. **LoopPilot frozen HEAD:** `2275e747e73936ebb8f0b24e5fb901a619b6adf8`.
14. **Mode:** `Lightweight`.
15. **Why not Full Loop:** one read-only owner and one Reviewer need no Task/Finding/Integration machinery.
16. **Fresh Contract:** `RECOVERY-CONTRACT.md`, distinct from EXP-008 Closure correction.
17. **Why not TASK-010 R3:** old budget is exhausted; this experiment has a new objective and one correction.
18. **Fixed inventory count:** 93.
19. **Categories:** 14 Product, 7 authoritative, 40 supporting, 24 Review, 7 Evaluation, 1 Recovery.
20. **Membership hash:** `8057eadae81aa4e87c921e4d7e0cdc01259798852a465b47941a6fa479902ecd`.
21. **EXP-009 governance files:** 5 at candidate boundary.
22. **Governance lines:** derived by validator at the current boundary; not duplicated as a fixed prose total.
23. **EXP-009 evaluation files:** 6 at candidate boundary.
24. **Evaluation lines:** derived by validator at the current boundary; not duplicated as a fixed prose total.
25. **Product changes:** 0.
26. **Test changes:** 0.
27. **Frontend changes:** 0.
28. **Product unchanged proof:** Git diff from Product HEAD under `fantasy_agent tests apps` is empty.
29. **TASK-010 unchanged proof:** Archive/current blob is `e00de12b4bd6e7f7e87bcda8e6df4f2bb2e8c80a`.
30. **Archive unchanged proof:** Git diff from Archive B under archived paths is empty.
31. **Numeric totals:** validator PASS for 71 governance, 8 evaluation/recovery, and 14 product members.
32. **Membership:** PASS for the exact commit/path set.
33. **SHA:** PASS; 12 Integration hashes use blobs and 2 declared TypeScript hashes use CRLF checkout bytes.
34. **Lines:** PASS from LF-byte physical-line calculation.
35. **Bytes:** PASS from source blob byte-array length.
36. **Stale-state scan:** R1 found F-001; the strengthened scan and same-Reviewer correction recheck PASS.
37. **Historical-claim scan:** EXP-008 blocked, R2 NOT-CLOSEABLE, and TASK-010 2/2 are preserved.
38. **Reviewer identity:** `/root/exp009_recovery_reviewer`.
39. **Spec Review:** original `FAIL`; same-Reviewer reverification `PASS`.
40. **Standards Review:** original `FAIL`; same-Reviewer reverification `PASS`.
41. **Evidence Review:** original `FAIL`; same-Reviewer reverification `PASS`.
42. **Review Findings:** F-001 Major `VERIFIED-CORRECTED`; no new Finding.
43. **Correction count:** `1 / 1`; no further correction is permitted.
44. **Same-Reviewer reverification:** PASS on tree `fda838393eaf7c3ff613ebbc17db14c0c33fa22e`.
45. **EXP-009 EII:** 9 recovered groups; post-Review group 9 is reported/not independently reviewed; EXP-008 EII is historical only.
46. **H1-H6:** H2/H3/H4 supported; H5 contradicted; H1/H6 inconclusive.
47. **Scorecard:** original `66 / 72` and FAIL; final `72 / 72` after same-Reviewer PASS.
48. **Fixed inventory helped:** yes for membership, but it did not cover lifecycle-value consistency.
49. **Membership validation helped:** yes; it checks the set and totals together.
50. **Lightweight sufficient:** yes for bounded recovery, with one correction and independent Review.
51. **Stale projections reappeared:** yes, once as F-001; the only correction was reverified.
52. **Artifact cost decreased:** governance is 5 files versus 71 archived EXP-008 files.
53. **EXP-008 comparison:** product Full Loop and evidence recovery answer different questions.
54. **Protocol tensions:** lifecycle-value coverage remains outside inventory membership; historical tensions are preserved.
55. **Supported Phase 9:** coordination gating, verifiable claims, role discipline, revision budget, recovery, honest block, independent Review.
56. **Contradicted mechanisms:** totals alone are insufficient; initial fixed-inventory checks did not prevent F-001.
57. **Inconclusive mechanisms:** H1/H6, Worker Failure Budget, and Ownership Collapse; correction sufficiency was supported.
58. **EXP-009 final status:** `RECOVERY-ACCEPTED-WITH-DISCLOSED-RESIDUALS`.
59. **Commits:** preregistration `5a0347a`; candidate reconciliation is the commit containing these Results with subject `docs: reconcile blocked Full Loop evidence inventory`.
60. **Final HEAD:** the commit containing these final Results; exact SHA is recorded by final delivery evidence.
61. **Push:** authorized only for the EXP-009 branch after this commit.
62. **Remote sync:** verified post-commit and reported by final delivery evidence.
63. **Final Git status:** verified post-commit and reported by final delivery evidence.
64. **Unverified:** historical real-tool/browser/TOCTOU risks; H1/H6 causal claims.
65. **Recommendation:** pair fixed membership with lifecycle-value checks and independent Review; inventory alone is insufficient.

EXP-009 recovery cannot close, accept, or deliver EXP-008. The accepted recovery result
preserves EXP-008 as blocked and does not authorize release, deployment, merge, or main.
