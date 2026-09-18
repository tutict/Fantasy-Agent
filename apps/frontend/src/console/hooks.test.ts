import { describe, expect, it } from "vitest";

import { MOBILE_NEEDLE, promptRequestFromPlan } from "./hooks";
import type { DirectorBuildPlan } from "../shared/types";

/**
 * `promptRequestFromPlan` reconstructs the request the console sends when it
 * asks the backend to regenerate a plan's spec.
 *
 * Two parts of it are inferential rather than read straight off the plan, and
 * both are asserted here because both can be silently wrong in a way no
 * typecheck would catch:
 *
 *   1. **The prompt** is the plan's title plus logline, because the handoff
 *      stores no prompt. Asserted so the reconstruction cannot quietly become
 *      an empty string (which the endpoint rejects) or the raw title alone.
 *   2. **The platform** is guessed from `asset_needs`, the only field that hints
 *      at it. The guess drives the panel's "Scope" line, so a needle that
 *      matches the wrong thing makes the UI report a platform the plan never
 *      mentioned -- and the operator has no way to tell that from a real signal.
 */

const MOBILE_FALSE_POSITIVES = [
  // "ios" appears inside these; the old unanchored `/(ios)/` matched them all.
  "kiosk",
  "asset kiosk prop",
  "prioritization hud",
  "curious vendor" // "ios" in "curious"
];

const MOBILE_TRUE_POSITIVES = [
  "touch controls",
  "mobile hud",
  "android build",
  "iOS gamepad",
  "IOS gamepad",
  "handheld mode",
  "ios_controls",
  "ios-art",
  "touch_screen",
  "mobile-first"
];

function plan(assetNeeds: string[]): DirectorBuildPlan {
  return {
    gameplay_spec: {
      title: "Neon Rooftops",
      logline: "Deliver packages across a collapsing skyline.",
      target_session_minutes: 10,
      asset_needs: assetNeeds
    },
    // `usesGodotEngine` reads the pipeline's stage ids, not the plan's engine
    // block -- so the Godot version only resolves when this stage is present.
    production_pipeline: { stages: [{ id: "godot_quick_play" }] },
    godot_plan: { engine_version: "Godot 4.5" }
  } as unknown as DirectorBuildPlan;
}

describe("inferPlatform's mobile needle", () => {
  it("does not fire on words that merely contain a platform name", () => {
    // Each of these reached the Android branch before the needle was anchored.
    for (const text of MOBILE_FALSE_POSITIVES) {
      expect(MOBILE_NEEDLE.test(text), text).toBe(false);
    }
  });

  it("still fires on real platform mentions, including snake and kebab ids", () => {
    // `\b`-style anchoring would break `ios_controls` and `mobile-first`, which
    // is why the boundary is `[^a-z0-9]` rather than a word boundary.
    for (const text of MOBILE_TRUE_POSITIVES) {
      expect(MOBILE_NEEDLE.test(text), text).toBe(true);
    }
  });
});

describe("promptRequestFromPlan", () => {
  it("returns nothing at all without a spec", () => {
    expect(promptRequestFromPlan(null)).toBeNull();
  });

  it("reconstructs the prompt from the title and logline", () => {
    const request = promptRequestFromPlan(plan(["touch controls"]));

    expect(request?.prompt).toBe("Neon Rooftops. Deliver packages across a collapsing skyline.");
    expect(request?.target_minutes).toBe(10);
    expect(request?.engine_version).toBe("Godot 4.5");
    expect(request?.platforms).toEqual(["Android"]);
  });

  it("falls back to the player fantasy when the plan has no title or logline", () => {
    const bare = {
      gameplay_spec: { player_fantasy: "be the fastest courier", target_session_minutes: 5 },
      production_pipeline: { stages: [{ id: "godot_quick_play" }] },
      godot_plan: { engine_version: "Godot 4.5" }
    } as unknown as DirectorBuildPlan;

    expect(promptRequestFromPlan(bare)?.prompt).toBe("be the fastest courier");
  });

  it("names the engine the pipeline actually chose", () => {
    // An Unreal plan and a Godot plan must not report the same engine version:
    // the console shows this line as "Scope", and a wrong engine means the
    // regenerated spec is diffed against the wrong baseline's assumptions.
    const unreal = {
      gameplay_spec: { title: "T", logline: "L", target_session_minutes: 10, asset_needs: [] },
      production_pipeline: { stages: [{ id: "unreal_import" }] },
      unreal_plan: { engine_version: "UE5.4" }
    } as unknown as DirectorBuildPlan;

    expect(promptRequestFromPlan(unreal)?.engine_version).toBe("UE5.4");
    expect(promptRequestFromPlan(plan([]))?.engine_version).toBe("Godot 4.5");
  });

  it("reports the platform its assets actually imply, not a coincidental substring", () => {
    // The regression this pins: `asset kiosk prop` used to render as "Android".
    const request = promptRequestFromPlan(plan(["asset kiosk prop"]));

    expect(request?.platforms).toEqual(["Windows"]);
  });
});
