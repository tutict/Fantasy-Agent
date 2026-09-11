import { afterEach, describe, expect, it, vi } from "vitest";

import {
  errorMessageFromPayload,
  getSessionState,
  openManualCorrectionTarget,
  previewExecute,
  startExecute
} from "./api";
import type { DirectorBuildPlan } from "./types";

const PLAN = { project_name: "demo" } as unknown as DirectorBuildPlan;
const TUNING = { enemy_count: 2 } as never;

/**
 * A Response body can only be read once, so a mock has to build a fresh one
 * per call rather than resolving the same instance every time.
 */
function jsonFetch(body: unknown, status = 200) {
  return vi.fn().mockImplementation(() =>
    Promise.resolve(
      new Response(JSON.stringify(body), {
        status,
        headers: { "Content-Type": "application/json" }
      })
    )
  );
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("errorMessageFromPayload", () => {
  it("surfaces a string detail so the user sees the backend's own message", () => {
    expect(
      errorMessageFromPayload({ detail: "resume_from 需要同时提供 session_id" }, 400)
    ).toBe("resume_from 需要同时提供 session_id");
  });

  it("unwraps FastAPI 422 validation errors into readable text", () => {
    const payload = {
      detail: [{ loc: ["body", "engine"], msg: "field required", type: "missing" }]
    };
    expect(errorMessageFromPayload(payload, 422)).toBe("body.engine: field required");
  });

  it("falls back to the status code when there is no usable body", () => {
    expect(errorMessageFromPayload(null, 500)).toBe("HTTP 500");
    expect(errorMessageFromPayload({ detail: "" }, 404)).toBe("HTTP 404");
    expect(errorMessageFromPayload({ detail: [{ msg: "" }] }, 422)).toBe("HTTP 422");
  });
});

describe("jsonRequest error propagation", () => {
  it("rejects with the backend detail instead of a bare status code", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ detail: "session 不存在" }), {
          status: 400,
          headers: { "Content-Type": "application/json" }
        })
      )
    );
    await expect(getSessionState("nope")).rejects.toThrow("session 不存在");
  });
});

describe("manual correction approval gate", () => {
  it("forwards the caller's decision instead of hardcoding approval", async () => {
    const fetchMock = jsonFetch({ status: "started" });
    vi.stubGlobal("fetch", fetchMock);

    await openManualCorrectionTarget("godot", "Godot 4", false);
    const denied = JSON.parse(fetchMock.mock.calls[0][1].body as string);
    expect(denied.confirmed_side_effects).toBe(false);

    await openManualCorrectionTarget("godot", "Godot 4", true);
    const allowed = JSON.parse(fetchMock.mock.calls[1][1].body as string);
    expect(allowed.confirmed_side_effects).toBe(true);
  });

  it("never sends an approved request unless the caller says so", async () => {
    const fetchMock = jsonFetch({ status: "blocked" });
    vi.stubGlobal("fetch", fetchMock);

    await openManualCorrectionTarget("blender", "UE5", false);
    const bodies = fetchMock.mock.calls.map((call) => JSON.parse(call[1].body as string));
    expect(bodies.every((body) => body.confirmed_side_effects === false)).toBe(true);
  });
});

describe("execute requests", () => {
  it("marks the preview as unconfirmed and the real run as confirmed", async () => {
    const fetchMock = jsonFetch({ status: "ok" });
    vi.stubGlobal("fetch", fetchMock);

    await previewExecute(PLAN, "godot", false, false, false, TUNING);
    expect(JSON.parse(fetchMock.mock.calls[0][1].body as string).confirmed).toBe(false);

    await startExecute(PLAN, "godot", false, false, false, TUNING);
    expect(JSON.parse(fetchMock.mock.calls[1][1].body as string).confirmed).toBe(true);
  });

  it("forwards resume options so a re-run can skip finished stages", async () => {
    const fetchMock = jsonFetch({ status: "ok" });
    vi.stubGlobal("fetch", fetchMock);

    await startExecute(PLAN, "godot", false, false, false, TUNING, undefined, {
      sessionId: "abc123",
      resumeFrom: "blender"
    });
    const body = JSON.parse(fetchMock.mock.calls[0][1].body as string);
    expect(body.session_id).toBe("abc123");
    expect(body.resume_from).toBe("blender");
  });
});

describe("session state lookups", () => {
  it("encodes the session id so it cannot break out of the path", async () => {
    const fetchMock = jsonFetch({ stages: [] });
    vi.stubGlobal("fetch", fetchMock);

    await getSessionState("session/../evil");
    expect(fetchMock.mock.calls[0][0]).toBe("/api/sessions/session%2F..%2Fevil/state?engine=godot");
  });
});
