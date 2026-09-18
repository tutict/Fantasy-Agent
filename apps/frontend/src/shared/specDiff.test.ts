import { describe, expect, it } from "vitest";

import {
  SPEC_DIFF_SEPARATOR,
  changedRows,
  countOnly,
  diffSpecs,
  specDigest,
  specFields
} from "./specDiff";
import type { GameplaySpec } from "./types";

/**
 * The comparison rules behind the console's "regenerate & compare" panel.
 *
 * This file exists because the interesting part of that panel is not the DOM --
 * it is the four decisions `diffSpecs` makes, each of which an operator reads as
 * a factual claim about the backend:
 *
 *   1. **A field that vanished is drift.** It renders as `-`, not as a missing
 *      row. Silently dropping it would make "the backend stopped emitting this"
 *      indistinguishable from "nothing changed here".
 *   2. **A zero is a value.** `String(value ?? "")`, never `value || ""`.
 *      Otherwise a `duration_minutes: 0` reads as an empty field and the drift
 *      report claims the wrong thing.
 *   3. **The list index is part of the path.** `core_verbs[1]` changing is a
 *      different fact from the list growing by one.
 *   4. **Row order is stable.** Baseline order first, then regenerated-only
 *      fields sorted among themselves -- so the list does not reshuffle just
 *      because the backend appended a field.
 *
 * Every test below pins one of those. The DOM half is pinned separately in
 * `console/rendering.test.tsx`.
 */

function spec(overrides: Partial<GameplaySpec> = {}): GameplaySpec {
  return { title: "Neon Rooftops", ...overrides };
}

describe("specFields", () => {
  it("flattens scalar fields without inventing a value for missing ones", () => {
    const fields = specFields(spec());

    expect(fields.get("title")).toBe("Neon Rooftops");
    // Absent, not "undefined" or "null" -- the two would compare as real drift
    // against a spec that legitimately omits the field.
    expect(fields.get("logline")).toBe("");
    expect(fields.get("win_state")).toBe("");
  });

  it("keeps a zero rather than erasing it", () => {
    // The bug this guards: `value || ""` turns 0 into "". An operator then reads
    // "the backend stopped emitting target_session_minutes" when in fact it
    // emitted a legitimate 0.
    const fields = specFields(spec({ target_session_minutes: 0 }));

    expect(fields.get("target_session_minutes")).toBe("0");
  });

  it("keeps a nested zero for the same reason", () => {
    const fields = specFields(
      spec({ level_beats: [{ name: "intro", duration_minutes: 0 }] })
    );

    expect(fields.get("level_beats[0].duration_minutes")).toBe("0");
  });

  it("joins a list into one comparable string, dropping empty entries", () => {
    const fields = specFields(spec({ core_verbs: ["wall-run", "", "vault"] }));

    expect(fields.get("core_verbs")).toBe(`wall-run${SPEC_DIFF_SEPARATOR}vault`);
  });

  it("numbers list entries so a moved value is distinguishable from a grown list", () => {
    const fields = specFields(
      spec({
        core_loop: [
          { action: "wall-run", player_decision: "commit or drop" },
          { action: "vault", player_decision: "spend or save" }
        ]
      })
    );

    expect(fields.get("core_loop[0].action")).toBe("wall-run");
    expect(fields.get("core_loop[1].action")).toBe("vault");
    expect(fields.get("core_loop[1].player_decision")).toBe("spend or save");
  });

  it("covers every nested group the panel can show", () => {
    const fields = specFields(
      spec({
        systems: [{ name: "momentum", purpose: "reward uninterrupted routes" }],
        level_beats: [{ name: "intro", duration_minutes: 3 }],
        enemies: [{ name: "drone", behavior: "patrol", count: 4 }]
      })
    );

    expect(fields.get("systems[0].name")).toBe("momentum");
    expect(fields.get("systems[0].purpose")).toBe("reward uninterrupted routes");
    expect(fields.get("level_beats[0].name")).toBe("intro");
    expect(fields.get("enemies[0].behavior")).toBe("patrol");
    expect(fields.get("enemies[0].count")).toBe("4");
  });

  it("reads provenance off the i18n bundle, which is the only record of it", () => {
    // A rewritten prompt leaves no trace in the axis-shaped `notes_for_*`
    // fields; provenance is where it surfaces.
    const fields = specFields(
      spec({ i18n: { source_locale: "zh-CN", output_locales: ["zh-CN", "en"] } })
    );

    expect(fields.get("i18n.source_locale")).toBe("zh-CN");
    expect(fields.get("i18n.output_locales")).toBe(`zh-CN${SPEC_DIFF_SEPARATOR}en`);
  });

  it("returns nothing for a null spec instead of throwing", () => {
    expect(specFields(null).size).toBe(0);
    expect(specFields(undefined).size).toBe(0);
  });
});

describe("diffSpecs", () => {
  it("reports no drift for a spec compared against itself", () => {
    const one = spec({ core_verbs: ["wall-run"], win_state: "reach the drop zone" });
    const result = diffSpecs(one, { ...one });

    expect(result.changedCount).toBe(0);
    expect(result.mirrorStale).toBe(false);
    expect(result.rows.every((row) => !row.changed)).toBe(true);
  });

  it("flags a changed scalar and shows both sides", () => {
    const result = diffSpecs(spec({ win_state: "reach the drop zone" }), spec({ win_state: "survive 10 minutes" }));

    const row = result.rows.find((entry) => entry.field === "win_state");
    expect(row).toEqual({
      field: "win_state",
      baseline: "reach the drop zone",
      regenerated: "survive 10 minutes",
      changed: true
    });
    expect(result.changedCount).toBe(1);
    expect(result.mirrorStale).toBe(true);
  });

  it("renders a field the backend stopped emitting as a dash, not a dropped row", () => {
    const result = diffSpecs(spec({ player_fantasy: "become the courier" }), spec());

    const row = result.rows.find((entry) => entry.field === "player_fantasy");
    expect(row?.baseline).toBe("become the courier");
    expect(row?.regenerated).toBe("-");
    expect(row?.changed).toBe(true);
  });

  it("dashes a whole nested group the regenerated spec no longer carries", () => {
    // The stronger version of the case above: an absent scalar still gets a key
    // from `specFields`, so only a *nested* group genuinely disappears. The
    // rows for it must survive into the report.
    const result = diffSpecs(
      spec({
        enemies: [{ name: "drone", behavior: "patrol", count: 4 }],
        systems: [{ name: "momentum" }]
      }),
      spec()
    );

    const enemyRows = result.rows.filter((row) => row.field.startsWith("enemies[0]"));
    expect(enemyRows.map((row) => row.field)).toEqual([
      "enemies[0].name",
      "enemies[0].behavior",
      "enemies[0].count"
    ]);
    expect(enemyRows.every((row) => row.baseline !== "-" && row.regenerated === "-")).toBe(true);
    expect(result.changedCount).toBeGreaterThanOrEqual(4);
  });

  it("renders a field the backend newly emits the same way, on the other side", () => {
    const result = diffSpecs(spec(), spec({ qa_focus: ["frame time"] }));

    const row = result.rows.find((entry) => entry.field === "qa_focus");
    expect(row?.baseline).toBe("-");
    expect(row?.regenerated).toBe("frame time");
    expect(row?.changed).toBe(true);
  });

  it("treats an empty string and a missing field as the same thing", () => {
    // `specFields` emits a key for every scalar it knows about, so a spec that
    // omits `logline` and one that sends `logline: ""` reach `diffSpecs` in
    // different shapes. They must produce the same row, or the report would
    // invite a hunt for a distinction an operator cannot act on.
    //
    // Asserted against literal values rather than against each other: the two
    // inputs do map to the same string inside `specFields`, so comparing the
    // two results to *each other* compares a value with itself and passes
    // however the implementation changes. The expected row is written out so
    // that `String(value ?? "")` becoming `String(value)` (which would yield
    // the literal "undefined") or `|| "-"` (which would yield "-") fails here.
    const omitted = diffSpecs(spec({ title: "T" }), spec({ title: "T", logline: undefined }));
    const blank = diffSpecs(spec({ title: "T" }), spec({ title: "T", logline: "" }));

    const expected = {
      field: "logline",
      baseline: "-",
      regenerated: "-",
      changed: false
    };
    const pick = (result: typeof omitted) =>
      result.rows.find((entry) => entry.field === "logline");

    expect(pick(omitted)).toEqual(expected);
    expect(pick(blank)).toEqual(expected);
  });

  it("keeps a zero on both sides when only the zero changed", () => {
    const result = diffSpecs(
      spec({ target_session_minutes: 0 }),
      spec({ target_session_minutes: 10 })
    );

    const row = result.rows.find((entry) => entry.field === "target_session_minutes");
    expect(row?.baseline).toBe("0");
    expect(row?.regenerated).toBe("10");
    expect(row?.changed).toBe(true);
  });

  it("treats a list growing by one as a change to that list's row", () => {
    const result = diffSpecs(spec({ core_verbs: ["wall-run"] }), spec({ core_verbs: ["wall-run", "vault"] }));

    const row = result.rows.find((entry) => entry.field === "core_verbs");
    expect(row?.changed).toBe(true);
    expect(row?.regenerated).toBe(`wall-run${SPEC_DIFF_SEPARATOR}vault`);
  });

  it("keeps the row order identical no matter which side added a field", () => {
    // Stability matters: the panel re-renders on every regeneration, and a
    // reshuffling list makes an operator re-read the whole thing each time.
    // `specFields` emits every field it knows about, so both sides produce the
    // same key order here -- which is exactly the property worth pinning, since
    // it means a populated spec and an empty one cannot disagree on ordering.
    const sparse = spec();
    const rich = spec({ qa_focus: ["q"], asset_needs: ["a"], win_state: "w" });

    expect(diffSpecs(sparse, rich).rows.map((row) => row.field)).toEqual(
      diffSpecs(rich, sparse).rows.map((row) => row.field)
    );
    expect(diffSpecs(rich, sparse).rows.map((row) => row.field)).toEqual([
      ...specFields(sparse).keys()
    ]);
  });

  it("appends a nested list's extra entries after the baseline's, sorted", () => {
    // The one case where the two sides genuinely have different keys: baseline
    // knows `systems[0]` and the regenerated spec added `systems[1]`.
    const baseline = spec({ systems: [{ name: "momentum" }] });
    const regenerated = spec({
      systems: [{ name: "momentum" }, { name: "stamina", purpose: "cost sprinting" }]
    });

    const fields = diffSpecs(baseline, regenerated).rows.map((row) => row.field);
    const appended = fields.filter((field) => field.startsWith("systems[1]"));

    expect(fields.indexOf("systems[1].name")).toBeGreaterThan(fields.indexOf("systems[0].name"));
    // Sorted among themselves, so `name` precedes `purpose` deterministically.
    expect(appended).toEqual(["systems[1].name", "systems[1].purpose"]);
  });

  it("counts every drifted row once", () => {
    const result = diffSpecs(
      spec({ win_state: "a", logline: "b", core_verbs: ["c"] }),
      spec({ win_state: "x", logline: "b", core_verbs: ["z"] })
    );

    expect(result.changedCount).toBe(2);
    expect(changedRows(result).map((row) => row.field)).toEqual(["win_state", "core_verbs"]);
  });

  it("handles a cold start where there is no baseline at all", () => {
    const result = diffSpecs(null, spec({ title: "Neon Rooftops" }));

    // Every row is "new", which is correct: there is no snapshot to be stale.
    expect(result.changedCount).toBeGreaterThan(0);
    expect(result.rows.every((row) => row.baseline === "-")).toBe(true);
  });

  it("returns an empty result rather than throwing when both sides are null", () => {
    const result = diffSpecs(null, null);

    expect(result.rows).toEqual([]);
    expect(result.changedCount).toBe(0);
    expect(result.mirrorStale).toBe(false);
  });
});


describe("countOnly", () => {
  it("counts a list and reads an absent one as zero", () => {
    expect(countOnly(["a", "b"])).toBe(2);
    expect(countOnly([])).toBe(0);
    expect(countOnly(undefined)).toBe(0);
    expect(countOnly("wall-run")).toBe(0); // a bare string is not a list
  });
});

describe("specDigest", () => {
  it("summarizes the regenerated spec without dumping the diff", () => {
    const digest = specDigest(
      spec({
        title: "Neon Rooftops",
        target_session_minutes: 10,
        core_verbs: ["wall-run", "vault"],
        core_loop: [{ action: "wall-run" }],
        systems: [{ name: "momentum" }, { name: "stamina" }],
        level_beats: [{ name: "intro" }],
        enemies: [{ name: "drone" }, { name: "turret" }, { name: "sentry" }]
      })
    );

    expect(digest).toEqual({
      title: "Neon Rooftops",
      targetMinutes: "10",
      verbs: 2,
      loopSteps: 1,
      systems: 2,
      beats: 1,
      enemies: 3
    });
  });

  it("shows dashes rather than zeros for a spec that never arrived", () => {
    // A zero here would read as "the backend produced a 0-minute spec"; a dash
    // reads as "nothing to show", which is what actually happened.
    const digest = specDigest(null);

    expect(digest.title).toBe("-");
    expect(digest.targetMinutes).toBe("-");
    expect(digest.verbs).toBe(0);
  });
});
