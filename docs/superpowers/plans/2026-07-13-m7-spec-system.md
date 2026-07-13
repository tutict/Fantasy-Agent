# M7 Agent-Executable Production Spec System Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `ProductionSpecBundle` a loadable, deeply validated, approval-aware source of truth that compiles deterministic Godot and Unreal artifacts and exposes traceable QA in Studio.

**Architecture:** Add `fantasy_agent.production_spec_runtime` as the deep module at the production-spec seam. It loads YAML/JSON, applies semantic validation, synchronizes approval state, and compiles target-specific artifacts plus field-level trace records. Existing executors remain orchestration modules and delegate spec interpretation to Godot and Unreal adapters.

**Tech Stack:** Python 3.11+, Pydantic, PyYAML, FastAPI, React, TypeScript, Vite, pytest.

---

### Task 1: Bundle loading and execution gate

**Files:**
- Create: `fantasy_agent/production_spec_runtime.py`
- Modify: `fantasy_agent/contracts.py`
- Modify: `fantasy_agent/spec_validation.py`
- Modify: `fantasy_agent/__main__.py`
- Modify: `fantasy_agent/executor.py`
- Test: `tests/test_production_spec_runtime.py`
- Test: `tests/test_executor.py`

- [x] Write failing tests for YAML/JSON loading, cross-spec references, duration coverage, duplicate config keys, `--spec-file`, and failed-validation execution blocking.
- [x] Implement `load_production_spec_bundle(path, workspace_root) -> ProductionSpecBundle` with workspace path validation and schema-version checks.
- [x] Extend semantic validation to cover cross-spec references, level duration, config uniqueness, tuning bounds, asset approval consistency, and artifact path safety.
- [x] Add `--spec-file` so CLI planning and execution can use an existing bundle without prompt regeneration.
- [x] Add a `spec_validation` execution stage and stop before side effects when validation fails.

### Task 2: Godot production-spec adapter

**Files:**
- Create: `fantasy_agent/godot_spec_adapter.py`
- Modify: `fantasy_agent/godot_mcp.py`
- Modify: `fantasy_agent/gameplay_codegen.py`
- Modify: `fantasy_agent/executor.py`
- Test: `tests/test_godot_spec_adapter.py`
- Test: `tests/test_godot_mcp.py`

- [x] Write failing tests proving Combat/Level/Numeric/Narrative fields change generated Godot handoff and scripts without changing `GameplaySpec`.
- [x] Compile level segments, encounter roster, damage/tuning values, objective copy, failure feedback, and HUD text into a `GodotSpecHandoff`.
- [x] Make `main.gd`, player, enemy, and game-manager generation prefer compiled production specs, retaining `GameplaySpec` only as a compatibility fallback.
- [x] Record trace entries from every consumed spec field to the generated Godot artifact.

### Task 3: Config tables and approval synchronization

**Files:**
- Create: `fantasy_agent/config_table_compiler.py`
- Modify: `fantasy_agent/production_spec_runtime.py`
- Modify: `fantasy_agent/executor.py`
- Modify: `apps/studio/app/main.py`
- Test: `tests/test_config_table_compiler.py`
- Test: `tests/test_studio_app.py`

- [x] Write failing tests for YAML/JSON/CSV-ready output, deterministic ordering, primary-key uniqueness, safe export paths, and approval synchronization.
- [x] Implement one compiler interface returning artifacts and trace records for all table formats.
- [x] Replace Godot's hard-coded YAML loop with the compiler.
- [x] Synchronize `ResourcePipelineSpec` whenever an approval manifest is written or loaded, and export the synchronized bundle.

### Task 4: Studio Spec Bundle panel

**Files:**
- Modify: `apps/studio/app/main.py`
- Modify: `apps/frontend/src/shared/types.ts`
- Modify: `apps/frontend/src/shared/api.ts`
- Modify: `apps/frontend/src/console/FlowConsole.tsx`
- Modify: `apps/frontend/src/console/rendering.tsx`
- Modify: `apps/frontend/src/shared/i18n.ts`
- Modify: `apps/frontend/src/styles/console.css`
- Test: `tests/test_studio_app.py`

- [x] Write failing API tests for bundle validation/compile preview and trace responses.
- [x] Add read-only Studio endpoints for validation and compile preview.
- [x] Add a `Spec Bundle` tab showing six specs, validation issues, execution coverage, artifact paths, and field-to-artifact traces.
- [x] Keep rendering derived from the loaded planning handoff and avoid duplicate network requests.

### Task 5: Unreal adapter and executable QA

**Files:**
- Create: `fantasy_agent/unreal_spec_adapter.py`
- Modify: `fantasy_agent/contracts.py`
- Modify: `fantasy_agent/unreal_mcp.py`
- Modify: `fantasy_agent/executor.py`
- Test: `tests/test_unreal_spec_adapter.py`
- Test: `tests/test_unreal_mcp.py`
- Test: `tests/test_executor.py`

- [x] Write failing tests for Unreal DataTable JSON, DataAsset manifests, spec traceability, and machine-readable QA assertions.
- [x] Compile enemies, encounters, tuning, level segments, narrative text, and approved resources into Unreal importable data artifacts.
- [x] Add `ExecutableQAAssertion` and `ExecutableQAReport` contracts with deterministic static evaluation.
- [x] Add `spec_compile` and `spec_qa` execution stages and expose their artifacts in Studio.

### Task 6: Verification and documentation

**Files:**
- Modify: `gameplay-schema.yaml`
- Modify: `docs/gameplay-dsl/specification.md`
- Modify: `README.md`
- Modify: `ROADMAP.md`
- Modify: `AGENTS.md`

- [x] Update schema and human documentation for bundle loading, compilation, traceability, approval synchronization, and executable QA.
- [x] Run targeted pytest files, full pytest, `ruff check fantasy_agent tests apps`, frontend typecheck/build, and browser QA of the Spec Bundle panel.
