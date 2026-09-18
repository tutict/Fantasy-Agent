import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { BlenderScriptPanel } from "../shared/panels/BlenderScriptPanel";
import { BuildPanel } from "./rendering";
import { consoleI18n, makeTranslator } from "../shared/i18n";
import type { BlenderScriptArtifact, DirectorBuildPlan } from "../shared/types";

/**
 * The Blender script preview hangs off the shared `BuildPanel`, which both the
 * planning workbench and the flow console mount. Three things about it are worth
 * pinning:
 *
 *   1. **The not-executed marker.** The panel's whole risk is that an operator
 *      reads generated Python as Python that already ran. `side_effects` in
 *      particular describes what a later confirmed run *would* do -- with the
 *      scene deleted first -- so a panel that dropped the marker would be
 *      actively misleading.
 *   2. **Byte-identical script text.** The artifact is a formatted string and
 *      this panel is the only place it is ever read. React escapes interpolated
 *      text, so a `<script>`-shaped line must reach the DOM as text.
 *   3. **The empty case.** A plan with no Blender jobs must say so instead of
 *      offering a button that would fetch an empty job list.
 *
 * The fetch is mocked at the `../shared/api` boundary rather than from `react`:
 * `previewBlenderScript` writes nothing and launches nothing, so the transport
 * is not what these tests are about -- the rendering is.
 */

const t = makeTranslator("en", consoleI18n);

const { previewMock } = vi.hoisted(() => ({ previewMock: vi.fn() }));

vi.mock("../shared/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../shared/api")>();
  return { ...actual, previewBlenderScript: previewMock };
});

afterEach(() => {
  cleanup();
  previewMock.mockReset();
});

beforeEach(() => {
  previewMock.mockReset();
});

function plan(blender_plan?: DirectorBuildPlan["blender_plan"]): DirectorBuildPlan {
  return {
    production_pipeline: {
      project_name: "neon-rooftops",
      goal: "ship a 10 minute slice",
      current_stage: "godot_quick_play",
      next_stage: "creative_review",
      stages: []
    },
    blender_plan
  };
}

const JOBS = [{ asset_name: "Rooftop kit", purpose: "level art", export_path: "/out/rooftop.fbx" }];

const artifact: BlenderScriptArtifact = {
  plan_name: "neon-rooftops",
  script_path: "generated/blender/generate_assets.py",
  import_manifest_path: "generated/import-manifest.yaml",
  side_effects: [
    "Deletes the active Blender scene before generation.",
    "Writes .fbx files under generated/"
  ],
  execution_notes: ["Run headless: blender --background --python generate_assets.py"],
  import_manifest: {
    assets: [
      {
        asset_name: "Rooftop kit",
        // `source_file`, the name `UnrealImportAsset` actually uses. This
        // fixture said `source_path` until a review caught the mismatch, which
        // is exactly why the test could not notice the panel reading a key the
        // backend never sends.
        source_file: "generated/blender/rooftop.fbx",
        destination_path: "Content/Rooftops/rooftop.fbx"
      }
    ]
  },
  script: "import bpy\n\nbpy.ops.wm.read_factory_settings(use_empty=True)\n"
};

/** Render the panel directly, which is where every interesting branch lives. */
function renderPanel(overrides: { plan?: DirectorBuildPlan["blender_plan"] } = {}) {
  return render(<BlenderScriptPanel plan={overrides.plan ?? { jobs: JOBS }} t={t} />);
}

describe("Blender script preview", () => {
  it("offers the preview button when the plan declares Blender jobs", () => {
    const { container } = renderPanel();

    expect(screen.getByText("Blender script preview")).toBeTruthy();
    expect(screen.getByText("Preview script")).toBeTruthy();
    expect(screen.getByText("1 asset jobs")).toBeTruthy();
    expect(container.querySelector("#blender-script-button")).toBeTruthy();
  });

  it("says so and offers no button when the plan declares no Blender jobs", () => {
    // A button here would fetch an empty job list and render an empty script,
    // which reads as "the generator produced nothing" rather than "there was
    // nothing to generate".
    const { container } = renderPanel({ plan: { jobs: [] } });

    expect(screen.getByText("This plan declares no Blender asset jobs.")).toBeTruthy();
    expect(container.querySelector("#blender-script-button")).toBeNull();
    expect(screen.queryByText("Not executed")).toBeNull();
  });

  it("renders the artifact with the not-executed marker and the side effects first", async () => {
    previewMock.mockResolvedValue(artifact);

    const { container } = renderPanel();
    container.querySelector<HTMLButtonElement>("#blender-script-button")?.click();

    await waitFor(() => expect(screen.getByText("Not executed")).toBeTruthy());

    // The destructive effect is the one an operator has to weigh, so it must be
    // present in full -- not summarized.
    expect(screen.getByText("Side effects of a real run")).toBeTruthy();
    expect(screen.getByText("Deletes the active Blender scene before generation.")).toBeTruthy();

    // Metadata, manifest assets and notes all arrive.
    expect(screen.getByText("Plan")).toBeTruthy();
    expect(screen.getByText("neon-rooftops")).toBeTruthy();
    expect(screen.getByText("generated/blender/generate_assets.py")).toBeTruthy();
    expect(screen.getByText("generated/import-manifest.yaml")).toBeTruthy();
    expect(screen.getByText("Manifest assets")).toBeTruthy();
    expect(screen.getByText("Rooftop kit")).toBeTruthy();
    expect(screen.getByText("Execution notes")).toBeTruthy();
  });

  it("renders the manifest's source path, not a blank cell", async () => {
    // The panel read `asset.source_path` while the backend sends `source_file`.
    // React renders an undefined child as nothing at all, so the column was
    // silently empty and the row looked like a backend that omitted the path.
    // Asserting the value -- not merely that the row exists -- is what makes
    // the wrong key fail.
    previewMock.mockResolvedValue(artifact);

    const { container } = renderPanel();
    container.querySelector<HTMLButtonElement>("#blender-script-button")?.click();

    await waitFor(() => expect(screen.getByText("Manifest assets")).toBeTruthy());

    const row = container.querySelector(".wb-script-asset");
    expect(row).toBeTruthy();
    expect(row?.textContent).toContain("generated/blender/rooftop.fbx");
    expect(row?.textContent).toContain("Content/Rooftops/rooftop.fbx");
  });

  it("keeps the generated Python as text, not as markup", async () => {
    // If the panel ever reached for `dangerouslySetInnerHTML`, a line like this
    // would become a live element instead of a listing.
    const hostile = "import bpy\n# <script>alert(1)</script>\nbpy.ops.wm.save_mainfile()\n";
    previewMock.mockResolvedValue({ ...artifact, script: hostile });

    const { container } = renderPanel();
    container.querySelector<HTMLButtonElement>("#blender-script-button")?.click();

    const code = await waitFor(() => {
      const found = container.querySelector("#blender-script-code");
      if (!found) throw new Error("script listing not rendered");
      return found;
    });

    expect(code.textContent).toBe(hostile);
    expect(container.querySelector("#blender-script-code script")).toBeNull();
  });

  it("posts the plan unchanged and never sends a confirmation flag", async () => {
    // Read-only means read-only: there is no `confirmed` field to send, and
    // adding one here would suggest the backend gates on it.
    //
    // The key set is asserted exhaustively rather than by scanning the payload
    // for the substring "confirm" -- a search would pass vacuously whenever the
    // plan happens to contain no such word (it never does today) and would turn
    // red for an asset *named* "confirm-button kit", which is not a regression.
    previewMock.mockResolvedValue(artifact);

    const { container } = renderPanel();
    container.querySelector<HTMLButtonElement>("#blender-script-button")?.click();

    await waitFor(() => expect(previewMock).toHaveBeenCalledTimes(1));
    expect(previewMock.mock.calls[0][0]).toEqual({ jobs: JOBS });
    expect(Object.keys(previewMock.mock.calls[0][0])).toEqual(["jobs"]);
  });

  it("shows the backend's own failure text instead of an empty script", async () => {
    // An empty <pre> would read as "Blender produced a script with nothing in
    // it", which is a different claim from "the request failed".
    previewMock.mockRejectedValue(new Error("blender plan 缺少 jobs"));

    const { container } = renderPanel();
    container.querySelector<HTMLButtonElement>("#blender-script-button")?.click();

    await waitFor(() => expect(container.querySelector("#blender-script-error")).toBeTruthy());
    expect(screen.getByText(/blender plan 缺少 jobs/)).toBeTruthy();
    expect(container.querySelector("#blender-script-code")).toBeNull();
  });

  it("offers a clear control only once there is an artifact", async () => {
    previewMock.mockResolvedValue(artifact);

    const { container } = renderPanel();
    expect(container.querySelector("#blender-script-clear")).toBeNull();

    container.querySelector<HTMLButtonElement>("#blender-script-button")?.click();
    await waitFor(() => expect(container.querySelector("#blender-script-clear")).toBeTruthy());

    container.querySelector<HTMLButtonElement>("#blender-script-clear")?.click();
    await waitFor(() => expect(container.querySelector("#blender-script-code")).toBeNull());
    expect(container.querySelector("#blender-script-clear")).toBeNull();
  });
});

describe("Blender script preview inside the shared build panel", () => {
  it("mounts under the engine blocks so both routes reach it", () => {
    // `BuildPanel` is mounted by the planning workbench and the flow console
    // alike; the panel has to hang off it rather than off either call site.
    const { container } = render(<BuildPanel t={t} plan={plan({ jobs: JOBS })} />);

    expect(container.querySelector("#build-output")).toBeTruthy();
    expect(container.querySelector("#blender-script")).toBeTruthy();
  });

  it("stays hidden from the engine blocks when no Blender plan arrived", () => {
    const { container } = render(<BuildPanel t={t} plan={plan()} />);

    expect(container.querySelector("#build-output")).toBeTruthy();
    expect(container.querySelector("#blender-script")).toBeTruthy();
    expect(screen.getByText("This plan declares no Blender asset jobs.")).toBeTruthy();
  });
});
