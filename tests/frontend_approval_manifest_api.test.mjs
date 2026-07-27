import assert from "node:assert/strict";
import test from "node:test";

import { writeApprovalManifest } from "../apps/frontend/src/shared/api.ts";

test("writeApprovalManifest serializes the selected engine target", async () => {
  const requests = [];
  const originalFetch = globalThis.fetch;
  globalThis.fetch = async (url, init) => {
    requests.push({ url, init });
    return new Response(JSON.stringify({ manifest_path: "generated/asset-approval-manifest.yaml" }), {
      headers: { "Content-Type": "application/json" },
      status: 200
    });
  };

  try {
    await writeApprovalManifest({}, {}, undefined, "godot");
    await writeApprovalManifest({}, {}, undefined, "unreal");
  } finally {
    globalThis.fetch = originalFetch;
  }

  assert.deepEqual(
    requests.map(({ url, init }) => ({
      body: JSON.parse(init.body),
      method: init.method,
      url
    })),
    ["godot", "unreal"].map((target) => ({
      body: { decisions: {}, review: {}, target },
      method: "POST",
      url: "/api/creative-review/approval-manifest"
    }))
  );
});
