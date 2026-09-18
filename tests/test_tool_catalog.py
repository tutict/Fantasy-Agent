"""``tool_catalog()`` is the UI's view of the permission gate.

The Agent panel renders this payload to tell an operator which tools a run may
reach and at which tier. Three things about it are load-bearing, and each fails
silently without a test:

- **The tiers must be the gate's own.** ``ToolRegistry.call`` decides whether a
  call is allowed from ``ToolSpec.permission``. If the catalog derived tiers any
  other way -- a hand-typed table, a second implementation of
  ``permission_from_annotations`` -- the panel would advertise a tier the gate
  does not enforce, which is worse than showing nothing.
- **The counts must partition the tools.** The panel prints
  ``permission_counts`` as a summary line. A tool whose permission is not one of
  ``PERMISSIONS`` would be counted by no bucket while still being listed,
  so the summary and the list would disagree with nothing to catch it.
- **The declared-without-implementation gap must be real.** It is the only
  visible signal for a contract that no bridge implements, and its whole value
  is that it is computed rather than remembered.

The catalog is also the reason ``/api/tool-contracts`` is still registered in
``KNOWN_WITHOUT_UI``: the two serve different things, and this test pins that
difference so a later change does not collapse them into one endpoint.
"""

from __future__ import annotations

import pytest

from fantasy_agent.tool_registry import (
    PERMISSIONS,
    READ_ONLY,
    combined_registry,
    default_registry,
    engine_registry,
    tool_catalog,
)


def _entries() -> list[dict]:
    return tool_catalog()["tools"]


def test_catalog_returns_the_three_key_payload_the_panel_reads() -> None:
    """Pin the payload's shape, not just its contents.

    The function used to be annotated ``-> list[dict[str, Any]]`` while
    returning a dict. Nothing caught it: ruff does not check annotations, the
    one route that calls it declares its own return type, and every test here
    subscripts the result. So the annotation stayed wrong while the tests stayed
    green -- and an annotation is what a maintainer reads before deciding how to
    consume the function.

    Asserting the exact key set does double duty: it catches an annotation that
    drifts from the return again, and it names the three keys the panel depends
    on, so dropping one fails here instead of rendering an empty section.
    """

    payload = tool_catalog()

    assert isinstance(payload, dict), (
        f"tool_catalog() returned {type(payload).__name__}; the annotation and the "
        "Studio route both say dict, and the Agent panel reads it by key"
    )
    assert set(payload) == {"tools", "permission_counts", "declared_without_implementation"}
    assert isinstance(payload["tools"], list)
    assert isinstance(payload["permission_counts"], dict)
    assert isinstance(payload["declared_without_implementation"], list)


def test_catalog_covers_every_registered_tool_exactly_once() -> None:
    """A tool missing from the catalog is invisible to an operator; a duplicate
    would double-count it in the summary."""

    names = [entry["name"] for entry in _entries()]
    assert len(names) == len(set(names)), f"duplicate catalog entries: {names}"

    registered = set(default_registry().names()) | set(engine_registry().names())
    assert set(names) == registered, (
        "tool_catalog() and the registries disagree about which tools exist"
    )


def test_catalog_reports_the_tier_the_gate_enforces() -> None:
    """The reported permission must be the very object ``call`` reads.

    Comparing against the spec rather than a re-derived value is the point: a
    catalog that ran its own permission logic could agree with the annotations
    and still disagree with the gate.
    """

    registries = {"planning": default_registry(), "engine": engine_registry()}
    for entry in _entries():
        spec = registries[entry["source"]].get(entry["name"])
        assert spec is not None, f"{entry['name']}: no spec behind a catalog entry"
        assert entry["permission"] == spec.permission, (
            f"{entry['name']}: catalog says {entry['permission']!r}, "
            f"the gate enforces {spec.permission!r}"
        )


def test_permission_counts_partition_the_tools() -> None:
    """Every tool lands in exactly one bucket, so the summary line is honest."""

    entries = _entries()
    counts = tool_catalog()["permission_counts"]

    assert set(counts) == set(PERMISSIONS), (
        "permission_counts must bucket every tier, including empty ones"
    )
    assert sum(counts.values()) == len(entries), (
        f"counts {counts} do not cover all {len(entries)} tools"
    )
    for tier in PERMISSIONS:
        actual = sum(1 for entry in entries if entry["permission"] == tier)
        assert counts[tier] == actual, f"{tier}: summary says {counts[tier]}, list has {actual}"


def test_planning_tools_stay_read_only() -> None:
    """The four planning tools must never claim a writing or executing tier.

    They compute a plan and return it. ``/api/tools/{name}`` has no approval
    flag precisely because of that, so a planning tool gaining ``write`` or
    ``execute`` would be a silent gate change: the workbench would keep calling
    it with no confirmation and the catalog would say that was fine.
    """

    planning = [entry for entry in _entries() if entry["source"] == "planning"]
    assert planning, "no planning tools in the catalog"
    offenders = [entry["name"] for entry in planning if entry["permission"] != READ_ONLY]
    assert not offenders, (
        f"planning tools must stay {READ_ONLY!r}; these do not: {offenders}"
    )


def test_declared_without_implementation_is_computed_not_remembered() -> None:
    """The gap must match what the contracts and the engine registry actually say."""

    from fantasy_agent.mcp import initial_mcp_contracts

    declared = {contract.name for contract in initial_mcp_contracts()}
    implemented = set(engine_registry().names())

    expected = sorted(declared - implemented)
    assert tool_catalog()["declared_without_implementation"] == expected
    # Both halves must be populated, or the assertion above is vacuous.
    assert declared, "no MCP contracts declared"
    assert implemented, "no engine tools registered"


def test_catalog_entries_carry_the_fields_the_panel_renders() -> None:
    """The panel reads these keys by name; a rename would render ``undefined``.

    Kept as a key-set assertion rather than a value check because the important
    part is the contract with the UI, not any particular tool's values.
    """

    required = {
        "name",
        "source",
        "server",
        "permission",
        "description",
        "confirm_field",
        "plan_key",
        "hidden_args",
        "executable_args",
        "contract",
    }
    for entry in _entries():
        missing = required - set(entry)
        assert not missing, f"{entry['name']}: catalog entry is missing {sorted(missing)}"


def test_catalog_is_json_serialisable() -> None:
    """Studio returns it straight from a route, so nothing may be a live object."""

    import json

    json.dumps(tool_catalog())


@pytest.mark.parametrize("tier", PERMISSIONS)
def test_engine_tiers_are_derived_from_bridge_annotations(tier: str) -> None:
    """At least one tier has to exist for the derivation to be exercised.

    This is a coverage floor, not a behavioural check: it fails if the engine
    registry ever collapses to a single tier, at which point the "permission
    comes from the MCP annotations" rule would no longer be tested by the
    registry's own contents.
    """

    tiers = {entry["permission"] for entry in _entries() if entry["source"] == "engine"}
    assert tiers, "no engine tools in the catalog"
    assert len(tiers) > 1, (
        f"engine tools all report one tier ({tiers}); the annotation-derived "
        "permission path is no longer exercised"
    )


def test_combined_registry_carries_both_groups_unchanged() -> None:
    """The catalog unions both registries, so the union must not reshape them.

    Identity is deliberately *not* asserted on the handlers: each
    ``default_registry()`` call builds fresh closures, so two calls never share
    a function object and pinning that would freeze an implementation detail. What
    matters is that the combined registry exposes the same tool under the same
    tier and schema, because that is what the catalog reports and what the gate
    enforces.
    """

    planning = default_registry()
    engine = engine_registry()
    combined = combined_registry()

    assert set(combined.names()) == set(planning.names()) | set(engine.names())
    for source in (planning, engine):
        for name in source.names():
            merged = combined.get(name)
            original = source.get(name)
            assert merged is not None, f"{name} missing from combined_registry"
            assert merged.permission == original.permission, f"{name}: tier changed by the union"
            assert merged.server == original.server, f"{name}: server changed by the union"
            assert merged.input_schema == original.input_schema, f"{name}: schema changed by the union"
