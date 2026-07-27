# LOOP-001 Specialist Review R0

- Reviewer: `/root/exp008_loop_specialist_reviewer`
- Boundary: stable ten hashes in INTEGRATION-001
- Security: FAIL; `LOOP001-SEC-001` Major, blocking
- Compatibility: PASS; Findings: None

Security evidence: `build_asset_approval_manifest` opens request-supplied paths directly;
Studio forwards review unchanged. An isolated probe hashed an accessible absolute sibling
file outside the logical workspace, creating a digest/existence oracle. Required correction:
explicit workspace root, containment/symlink checks before open, Studio `REPO_ROOT`, and
absolute/traversal/symlink-escape tests. Other consumer fail-closed behavior passed; the
disclosed post-hash/pre-copy TOCTOU interval remains excluded residual.

Compatibility evidence: legacy path-only manifests deserialize but cannot authorize ingest;
serialization, FBX/GLB identity behavior, Studio/ProductionSpec/Godot selections passed.
Fixed-boundary pytest: 75 passed after known ACL EII workaround. Reviewer remained read-only.
