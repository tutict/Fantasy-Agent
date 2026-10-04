import { act, renderHook } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { MOBILE_NEEDLE, promptRequestFromPlan, useExecutionJobPolling } from "./hooks";
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

/**
 * `useExecutionJobPolling` used to receive `jobId` / `setJobId` / `setResult`
 * from outside, so every consumer declared three `useState` for a mechanism it
 * did not own -- and `FlowConsole` ended up with 28 across three concurrent
 * jobs. It now owns them and hands back `start(jobId)` and `reset()`.
 *
 * That change moved two behaviors across a boundary nobody tests, so they are
 * pinned here. Both are things an operator sees immediately when broken: a stale
 * result from the previous run, or a poll timer that outlives the panel.
 */
describe("useExecutionJobPolling's self-owned job lifecycle", () => {
  const labels = {
    setStatus: () => {},
    addActivity: () => {},
    doneLabel: "done",
    failedLabel: "failed",
    cancelledLabel: "cancelled"
  };

  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("start() drops the previous run's result before adopting the new job id", async () => {
    // Without `setResult(null)` in `start`, submitting a second run leaves the
    // first run's stage cards on screen next to the new ones -- and the console
    // has no other place to clear them, because the state moved inside the hook.
    //
    // The first run has to actually *finish* here. A stub that keeps returning
    // "running" never sets a result, so the assertion would pass with
    // `setResult(null)` deleted -- which is exactly what happened when this test
    // was first written.
    let status = "running";
    const fetchJob = vi.fn().mockImplementation(async () => ({
      status,
      result: { project_dir: "generated/first" }
    }));
    const api = renderHook(() => useExecutionJobPolling({ ...labels, fetchJob }));

    act(() => api.result.current.start("job-1"));
    await act(async () => {
      await vi.advanceTimersByTimeAsync(1500);
    });
    expect(api.result.current.result).toEqual({ project_dir: "generated/first" });

    // Second run: the stale result must be gone the moment it starts, before
    // the first poll of the new job has had a chance to produce anything.
    status = "running";
    act(() => api.result.current.start("job-2"));

    expect(api.result.current.jobId).toBe("job-2");
    expect(api.result.current.result).toBeNull();

    await act(async () => {
      await vi.advanceTimersByTimeAsync(1500);
    });
    expect(fetchJob).toHaveBeenLastCalledWith("job-2");
  });

  it("reset() clears the job id so the panel stops asking about a finished run", async () => {
    const fetchJob = vi.fn().mockResolvedValue({ status: "running" });
    const api = renderHook(() => useExecutionJobPolling({ ...labels, fetchJob }));

    act(() => api.result.current.start("job-1"));
    expect(api.result.current.jobId).toBe("job-1");

    act(() => api.result.current.reset());

    expect(api.result.current.jobId).toBeNull();
    // The interval must not come back: nothing else in the hook can stop it.
    const callsAfterReset = fetchJob.mock.calls.length;
    await act(async () => {
      await vi.advanceTimersByTimeAsync(4500);
    });
    expect(fetchJob).toHaveBeenCalledTimes(callsAfterReset);
  });

  it("keeps polling through 'cancelling' and settles only on 'done'", async () => {
    // `cancelling` is transient -- the worker is still unwinding and its result
    // is still worth collecting. Stopping there would drop the very outcome the
    // operator cancelled for.
    //
    // The stub answers "running", then "cancelling", then "done", keyed on its
    // own call count rather than on a queue the implementation could satisfy a
    // different way. The assertion that matters is the call count: only an
    // implementation that keeps the interval alive across `cancelling` reaches
    // the third poll at all.
    const seen: string[] = [];
    const fetchJob = vi.fn().mockImplementation(async () => {
      const status = ["running", "cancelling", "done"][seen.length] ?? "done";
      seen.push(status);
      return { status, result: { project_dir: "generated/x" } };
    });
    const setStatus = vi.fn();
    const addActivity = vi.fn();
    const api = renderHook(() =>
      useExecutionJobPolling({
        setStatus,
        addActivity,
        doneLabel: "done",
        failedLabel: "failed",
        cancelledLabel: "cancelled",
        projectDirOnDone: true,
        fetchJob
      })
    );

    act(() => api.result.current.start("job-1"));
    await act(async () => {
      await vi.advanceTimersByTimeAsync(1500 * 3 + 10);
    });

    expect(seen).toEqual(["running", "cancelling", "done"]);
    expect(setStatus).toHaveBeenCalledWith("ready");
    expect(addActivity).toHaveBeenCalledWith("done", "generated/x");
    expect(api.result.current.jobId).toBeNull();
  });

  it("settles on a status it does not recognise instead of polling forever", async () => {
    // The mirror image, and the one that catches the real regression: narrowing
    // the "keep polling" condition to `status !== "done"` looks like a tidy
    // simplification and silently turns every `cancelled` run into an interval
    // that never stops. A queue-driven stub cannot see this -- it hands out
    // `done` after a fixed number of polls however the caller branched.
    let answered = 0;
    const fetchJob = vi.fn().mockImplementation(async () => {
      answered += 1;
      return answered === 1
        ? { status: "cancelling" }
        : { status: "cancelled", error: "operator stopped it" };
    });
    const setStatus = vi.fn();
    const addActivity = vi.fn();
    const api = renderHook(() =>
      useExecutionJobPolling({
        setStatus,
        addActivity,
        doneLabel: "done",
        failedLabel: "failed",
        cancelledLabel: "cancelled",
        fetchJob
      })
    );

    act(() => api.result.current.start("job-1"));
    await act(async () => {
      await vi.advanceTimersByTimeAsync(1500 * 4 + 10);
    });

    expect(fetchJob).toHaveBeenCalledTimes(2);
    expect(setStatus).toHaveBeenCalledWith("idle");
    expect(addActivity).toHaveBeenCalledWith("cancelled", "operator stopped it");
    expect(api.result.current.jobId).toBeNull();
  });

  it("stops the timer when the panel unmounts", async () => {
    // The console is never unmounted while a job runs (views stay mounted by
    // design), but the hook must not depend on that: an interval left running
    // after unmount keeps calling a fetch for a job nobody is watching.
    const fetchJob = vi.fn().mockResolvedValue({ status: "running" });
    const api = renderHook(() => useExecutionJobPolling({ ...labels, fetchJob }));

    act(() => api.result.current.start("job-1"));
    await act(async () => {
      await vi.advanceTimersByTimeAsync(1500);
    });
    const callsBeforeUnmount = fetchJob.mock.calls.length;
    expect(callsBeforeUnmount).toBeGreaterThan(0);

    api.unmount();
    await act(async () => {
      await vi.advanceTimersByTimeAsync(4500);
    });

    expect(fetchJob).toHaveBeenCalledTimes(callsBeforeUnmount);
  });
});
