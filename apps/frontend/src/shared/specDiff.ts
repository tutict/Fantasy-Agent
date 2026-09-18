/**
 * Compare the gameplay spec a plan was built from against a freshly generated
 * one.
 *
 * **Why this exists.** The console's spec tab shows the spec that arrived inside
 * the planning handoff. That snapshot is frozen at the moment the workbench
 * published it, so after the prompt, the LLM settings, or the generator itself
 * change, the panel keeps rendering a spec the backend would no longer produce --
 * with no visible difference. `GET /api/design` answers what the backend returns
 * *now*; this module turns the pair into the rows an operator reads.
 *
 * **Scope: display only.** Nothing here writes a file or mutates the plan. The
 * regenerated spec is a second opinion to look at, and adopting it is a separate
 * action with its own gate.
 *
 * The whole module is pure -- no fetch, no React -- because the interesting part
 * is the comparison rules, and those are worth testing without a DOM.
 */

import type { GameplaySpec } from "./types";

/** One field of the spec, reduced to something an operator can compare at a glance. */
export interface SpecDiffRow {
  /** Spec field path, e.g. `title` or `core_verbs[1]`. Matches the i18n bundle's path vocabulary. */
  field: string;
  baseline: string;
  regenerated: string;
  changed: boolean;
}

/** How the two specs' provenance differs. Both entries are empty for a cold start. */
export interface SpecDiffResult {
  rows: SpecDiffRow[];
  changedCount: number;
  /** True when at least one field differs -- i.e. the snapshot is no longer what the backend produces. */
  mirrorStale: boolean;
}

const SEPARATOR = " | ";

function joined(values: unknown): string {
  if (!Array.isArray(values)) return "";
  return values.map((value) => String(value ?? "")).filter(Boolean).join(SEPARATOR);
}

/**
 * Flatten a spec into `field -> value` pairs.
 *
 * Two rules, and both are load-bearing:
 *
 *   - **Falsy is not empty.** A spec field may legitimately be `0` (a zero
 *     `duration_minutes`, an `hp` of zero), and `String(value ?? "")` keeps it
 *     while `value || ""` would erase it. An erased zero reads as "the backend
 *     stopped emitting this", which is the opposite of what happened.
 *   - **The list index is part of the path.** `core_verbs[1]` changing from
 *     "vault" to "slide" is a different fact from the list growing by one, and
 *     an operator wants to see which entry moved. That is the same path shape
 *     `build_i18n_bundle` uses for its `field_translations` keys.
 */
export function specFields(spec: GameplaySpec | null | undefined): Map<string, string> {
  const fields = new Map<string, string>();
  if (!spec) return fields;

  const scalar = (field: string, value: unknown) => fields.set(field, String(value ?? ""));
  const list = (field: string, value: unknown) => fields.set(field, joined(value));

  scalar("title", spec.title);
  scalar("logline", spec.logline);
  scalar("target_session_minutes", spec.target_session_minutes);
  scalar("player_fantasy", spec.player_fantasy);
  scalar("win_state", spec.win_state);

  list("design_pillars", spec.design_pillars);
  list("core_verbs", spec.core_verbs);
  list("failure_states", spec.failure_states);
  list("asset_needs", spec.asset_needs);
  list("qa_focus", spec.qa_focus);

  spec.core_loop?.forEach((step, index) => {
    scalar(`core_loop[${index}].action`, step.action);
    scalar(`core_loop[${index}].player_decision`, step.player_decision);
    scalar(`core_loop[${index}].feedback`, step.feedback);
  });

  spec.systems?.forEach((system, index) => {
    scalar(`systems[${index}].name`, system.name);
    scalar(`systems[${index}].purpose`, system.purpose);
  });

  spec.level_beats?.forEach((beat, index) => {
    scalar(`level_beats[${index}].name`, beat.name);
    scalar(`level_beats[${index}].duration_minutes`, beat.duration_minutes);
  });

  spec.enemies?.forEach((enemy, index) => {
    // Behavior and count are the two fields the console's enemy tuning acts on,
    // so a regenerated roster that moved them is a tuning change, not a rename.
    scalar(`enemies[${index}].name`, enemy.name);
    scalar(`enemies[${index}].behavior`, enemy.behavior);
    scalar(`enemies[${index}].count`, enemy.count);
  });

  // Provenance. Both come straight off the i18n bundle, which is the only record
  // of what the spec was derived from -- a rewritten prompt shows up here and
  // nowhere else, because the `notes_for_*` fields are axis-shaped, not
  // prompt-shaped.
  scalar("i18n.source_locale", spec.i18n?.source_locale);
  list("i18n.output_locales", spec.i18n?.output_locales);

  return fields;
}

/** Number of entries in a list field that may be absent. */
export function countOnly(items: unknown): number {
  return Array.isArray(items) ? items.length : 0;
}

/**
 * Pair a frozen snapshot with a freshly generated spec.
 *
 * **Absent and empty are the same row, on purpose.** `specFields` emits a key
 * for every field it knows about, so a scalar the backend omitted arrives here
 * as `""` while a nested entry that never existed simply has no key at all.
 * `flat()` collapses those two into one rendering: an operator cannot act on the
 * difference between "the backend sent an empty string" and "the backend sent
 * nothing", and a report that drew them differently would invite a hunt for a
 * distinction that does not exist.
 *
 * **A field only one side knows about still gets a row.** Dashing the side that
 * lacks it is the point of the view: a field the backend stopped emitting is
 * exactly the drift an operator needs to see, and dropping the row would hide
 * it. This is the case `flat()` does not cover -- `specFields` always emits the
 * fixed scalar and list fields, so a key missing from one map means the *other*
 * spec is the one that has it (a cold start, or a nested list that grew).
 */
export function diffSpecs(
  baseline: GameplaySpec | null | undefined,
  regenerated: GameplaySpec | null | undefined
): SpecDiffResult {
  const baselineFields = specFields(baseline);
  const regeneratedFields = specFields(regenerated);

  // Baseline order first, then whatever only the regenerated spec added, sorted
  // among themselves. Stable across regenerations, so the list does not
  // reshuffle every time the backend appends a field.
  const baselineOrder = [...baselineFields.keys()];
  const appended = [...regeneratedFields.keys()]
    .filter((field) => !baselineFields.has(field))
    .sort((left, right) => left.localeCompare(right));

  const rows: SpecDiffRow[] = [...baselineOrder, ...appended].map((field) => {
    const before = flat(baselineFields, field);
    const after = flat(regeneratedFields, field);
    return { field, baseline: before, regenerated: after, changed: before !== after };
  });

  const changedCount = rows.filter((row) => row.changed).length;
  return { rows, changedCount, mirrorStale: changedCount > 0 };
}

/** One side of a row: a missing field and an empty one both render as `-`. */
function flat(fields: Map<string, string>, field: string): string {
  return fields.get(field) || "-";
}

/**
 * Spec fields the console renders as headline numbers, so the regenerated spec
 * can be summarized without dumping the whole diff.
 */
export function specDigest(spec: GameplaySpec | null | undefined): {
  title: string;
  targetMinutes: string;
  verbs: number;
  loopSteps: number;
  systems: number;
  beats: number;
  enemies: number;
} {
  return {
    title: spec?.title || "-",
    targetMinutes: String(spec?.target_session_minutes ?? "-"),
    verbs: countOnly(spec?.core_verbs),
    loopSteps: countOnly(spec?.core_loop),
    systems: countOnly(spec?.systems),
    beats: countOnly(spec?.level_beats),
    enemies: countOnly(spec?.enemies)
  };
}

/** Numbered rows for one list field, so a panel can render "3 / 5 entries moved". */
export function changedRows(result: SpecDiffResult): SpecDiffRow[] {
  return result.rows.filter((row) => row.changed);
}

export const SPEC_DIFF_SEPARATOR = SEPARATOR;
