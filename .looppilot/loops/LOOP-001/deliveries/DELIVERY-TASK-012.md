# Delivery - TASK-012

- Worker: `/root/exp008_worker_a_task012`
- Task: `TASK-012`
- Status: submitted for independent Spec and Standards review
- Parent, Loop, Finding, Closure, Project, commit, push, release, and deployment status are not claimed.

## Delivered Change

- `writeApprovalManifest` now accepts `godot | unreal` as its fourth argument,
  defaults omitted legacy calls to `unreal`, and always serializes `target`.
- `useApprovalManifest` derives the explicit target with the existing
  `usesGodotEngine(currentPlan)` helper.
- A dependency-free Node 24 test intercepts `fetch` and checks complete request
  bodies for both `godot` and `unreal`.

## Observed Evidence

1. Pre-fix RED:
   `node --test tests\\frontend_approval_manifest_api.test.mjs` exited 1 with
   `1 failed`; both actual request bodies lacked the expected `target` fields.
   Duration reported by Node was `117.055ms`.
2. Final focused GREEN:
   `node --test tests\\frontend_approval_manifest_api.test.mjs` exited 0 with
   `1 passed`, `0 failed`, duration `122.8616ms`.
3. `git diff --check -- apps/frontend/src/shared/api.ts
   apps/frontend/src/console/hooks.ts
   tests/frontend_approval_manifest_api.test.mjs` exited 0 with no output.
4. EOL check observed:
   - `apps/frontend/src/shared/api.ts`: index LF, worktree CRLF.
   - `apps/frontend/src/console/hooks.ts`: index LF, worktree CRLF.
   - `tests/frontend_approval_manifest_api.test.mjs`: worktree LF.
5. Focused semantic diff contains only target serialization, defaulting, and
   Hook propagation; the API default preserves practical three-argument caller
   compatibility.
6. No files were staged. Focused status showed exactly the three delivered
   product/test paths as two modified files and one untracked test.

## Exact Paths and SHA-256

- `apps/frontend/src/shared/api.ts`:
  `3E46846822D168B9DE51F3FD04ED0ED4404F279225250846D62DD156D8148BB8`
- `apps/frontend/src/console/hooks.ts`:
  `3B29CC84D04934053AC0ACDD098EB6AF583325BEB8425929FAC532D173D40437`
- `tests/frontend_approval_manifest_api.test.mjs`:
  `186DFE7107892B397DF746092DAB1EDA7D07D08AFD9BED6D9DA2A6F997DB3265`

## Unverified Evidence

- `npm.cmd run frontend:typecheck` did not execute TypeScript because the
  isolated worktree has no `node_modules`; npm reported `tsc is not recognized`.
- Direct read-only TypeScript execution from the main worktree dependency install
  reached the compiler but exited with TS2688 because isolated module resolution
  could not find `vite/client`.
- `npm.cmd run frontend:build` did not execute Vite because npm reported
  `vite is not recognized`.
- Direct read-only Vite execution from the main worktree dependency install did
  not build: isolated config resolution could not resolve
  `@vitejs/plugin-react` or `vite`, and sandbox denied its timestamp-file open.
- Typecheck and production build therefore remain unverified for the Integrator
  to rerun with scoped dependency resolution.

## EII and Residuals

- The built-in `apply_patch` helper failed once while updating files under the
  isolated `C:\\tmp` worktree. The authorized apply-patch entry point succeeded.
- That Windows argument transport stripped double quotes from the first patch;
  focused diff inspection caught it before validation, and a scoped follow-up
  patch corrected the TypeScript literals.
- First sandboxed EOL normalization was denied; the identical authorized scoped
  normalization succeeded. A temporary exact staging round-trip was fully
  unstaged after an `index.lock` permission retry; cached diff is empty.
- Git emitted the pre-existing inaccessible global-ignore warning during status
  and EOL inspection.
- No `apps/frontend/dist` directory or `vite.config.ts.timestamp-*.mjs` file was
  observed after the failed build attempts; there is no generated ignored output
  from this Worker for cleanup.
- Residual verification is limited to typecheck and production build. No real
  Godot, Unreal, Blender, ComfyUI, external API, release, or deployment action ran.
