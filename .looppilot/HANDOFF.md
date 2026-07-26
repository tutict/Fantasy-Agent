# EXP-007 Handoff

Current objective: implement the frozen endpoint-credential Change Contract using
two vertical TDD cycles.

Completed: isolated worktree/branch, three-layer baseline, Candidate A-E audit,
high-risk/low-coordination Lightweight decision, and Security review selection.

Observed evidence: 159 corrected baseline tests pass; ruff/typecheck/build pass;
public planning characterization accepts a credential-bearing localhost URL.

Blockers: none. EII: default pytest temp directory ACL; corrected only with explicit
`--basetemp`.

Unresolved risks: same-path asset replacement remains outside the selected Candidate
C scope; real external tools are prohibited and unverified.

Resume point: add only the Cycle 1 public-interface test in
`tests/test_comfyui_mcp.py`, run it to observe RED, then implement the minimum
sanitized rejection in `fantasy_agent/comfyui_mcp.py`.
