import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { consoleI18n, makeTranslator } from "../shared/i18n";
import type { PlaytestReport } from "../shared/types";
import { CorrectionReportCard, PlaytestConfirmBlock, PlaytestReportCard } from "./FlowConsole";

/**
 * A playtest really launches an engine, so the two-step gate is the whole
 * safety story: the backend refuses unless the request carries a confirmation
 * the human produced, and the repo rule is explicit that a view may never
 * manufacture that flag itself. These tests mount the real components so that
 * hardcoding `confirmed: true` at the call site -- which would make the gate
 * decorative -- fails the suite.
 *
 * The report card is a separate target because a verdict nobody can read is
 * not a verdict. The numbers on screen have to be the ones the backend
 * measured, each finding has to name the target the backend picked, and the
 * "resume from here" button has to carry the stage the backend translated
 * rather than one the panel made up.
 */
const t = makeTranslator("en", consoleI18n);

afterEach(() => cleanup());

/** One blocking finding, shaped like the backend's own. */
const REPORT: PlaytestReport = {
  status: "warning",
  project_dir: "generated/godot/rooftop",
  runs_requested: 3,
  aggregate: {
    runs: 3,
    playable_runs: 3,
    wins: 0,
    failures: 3,
    timeouts: 0,
    session_seconds_p50: 3,
    session_seconds_p95: 3.01
  },
  findings: [
    {
      code: "no_win_path",
      severity: "warning",
      message: "Every attempt failed before the extraction gate opened.",
      rework_target: "spec",
      resume_stage: "comfyui"
    }
  ],
  goal_notes: ["A scripted bot proves the loop is reachable, not that the slice is fun."],
  artifact_paths: ["generated/playtest/20261004_120000/playtest-report.json"]
};

describe("playtest confirmation gate", () => {
  const EFFECTS = ["Launch Godot headless", "Write generated/playtest/"];

  it("starts nothing the moment the block appears", () => {
    const onProceed = vi.fn();
    render(<PlaytestConfirmBlock effects={EFFECTS} t={t} onProceed={onProceed} onCancel={vi.fn()} />);
    expect(onProceed).not.toHaveBeenCalled();
  });

  it("lists the effects the backend reported, so the prompt is not vague", () => {
    render(<PlaytestConfirmBlock effects={EFFECTS} t={t} onProceed={vi.fn()} onCancel={vi.fn()} />);
    for (const effect of EFFECTS) {
      expect(screen.getByText(effect)).toBeTruthy();
    }
  });

  it("runs the playtest only after the human accepts", () => {
    const onProceed = vi.fn();
    const onCancel = vi.fn();
    render(<PlaytestConfirmBlock effects={EFFECTS} t={t} onProceed={onProceed} onCancel={onCancel} />);
    fireEvent.click(screen.getByRole("button", { name: t("generateConfirmProceed") }));
    expect(onProceed).toHaveBeenCalledTimes(1);
    expect(onCancel).not.toHaveBeenCalled();
  });

  it("cancels without running anything", () => {
    const onProceed = vi.fn();
    const onCancel = vi.fn();
    render(<PlaytestConfirmBlock effects={EFFECTS} t={t} onProceed={onProceed} onCancel={onCancel} />);
    fireEvent.click(screen.getByRole("button", { name: t("generateConfirmCancel") }));
    expect(onCancel).toHaveBeenCalledTimes(1);
    expect(onProceed).not.toHaveBeenCalled();
  });

  it("warns that an engine actually launches", () => {
    render(<PlaytestConfirmBlock effects={EFFECTS} t={t} onProceed={vi.fn()} onCancel={vi.fn()} />);
    // A confirmation the reader could mistake for a dry run is a broken gate.
    expect(screen.getByText(/launches Godot headless/i)).toBeTruthy();
  });
});

describe("playtest report card", () => {
  function renderCard(onResume?: (stage: string) => void) {
    return render(<PlaytestReportCard report={REPORT} t={t} onResume={onResume} />);
  }

  it("shows the measured numbers, not a placeholder", () => {
    const view = renderCard();
    expect(view.container.querySelector("#playtest-run-count")?.textContent).toContain("3");
    expect(view.container.querySelector("#playtest-playable-count")?.textContent).toBe("3/3");
    expect(view.container.querySelector("#playtest-outcomes")?.textContent).toBe("0 / 3 / 0");
    expect(view.container.querySelector("#playtest-seconds")?.textContent).toContain("3.0s p50");
  });

  it("names the finding and the target the backend picked", () => {
    renderCard();
    expect(screen.getByText("no_win_path")).toBeTruthy();
    expect(screen.getByText(/extraction gate/)).toBeTruthy();
    // `spec` is the rework target; the panel must not invent another.
    expect(screen.getByText(`${t("playtestReworkTarget")}: spec`)).toBeTruthy();
  });

  it("resumes from the stage the backend translated, not one the panel made up", async () => {
    const onResume = vi.fn();
    const view = renderCard(onResume);
    const button = view.container.querySelector<HTMLButtonElement>(".playtest-finding button");
    expect(button).toBeTruthy();
    fireEvent.click(button!);
    await waitFor(() => expect(onResume).toHaveBeenCalledWith("comfyui"));
  });

  it("prints the lower-bound caveat instead of hiding it", () => {
    renderCard();
    // The report admits a bot cannot judge fun; the UI may not quietly drop it.
    expect(screen.getByText(/not that the slice is fun/)).toBeTruthy();
  });

  it("omits the resume button when the backend sent no stage", () => {
    const view = render(
      <PlaytestReportCard
        report={{ ...REPORT, findings: [{ code: "x", severity: "warning", message: "m", rework_target: "spec" }] }}
        t={t}
        onResume={vi.fn()}
      />
    );
    expect(view.container.querySelector(".playtest-finding button")).toBeNull();
  });
});

describe("correction report card", () => {
  const REPORT = {
    manifest_found: true,
    drifted: [{ path: "generated/godot/demo/scripts/player_controller.gd", kind: "script" }],
    recoverable: [
      {
        anchor: "MOVE_SPEED",
        variable: "move_speed",
        value: 11.5,
        generated_value: 8,
        spec_field: "numeric.player_move_speed"
      }
    ],
    engine_only: [
      { anchor: "JUMP_VELOCITY", variable: "jump_velocity", value: 9.25, generated_value: 6, spec_field: "" }
    ],
    notes: ["The next generation overwrites every file listed above."]
  };

  function renderCard(report: unknown = REPORT) {
    return render(<CorrectionReportCard report={report as never} t={t} />);
  }

  it("names the changed file so it can be found before it is lost", () => {
    const view = renderCard();
    expect(view.getByText("generated/godot/demo/scripts/player_controller.gd")).toBeTruthy();
  });

  it("shows the old and new value, not just the new one", () => {
    renderCard();
    // Without the before-value the operator cannot tell a hand edit from the
    // number the pipeline generated.
    expect(screen.getByText(/11\.5/)).toBeTruthy();
    expect(screen.getByText(/8/)).toBeTruthy();
  });

  it("separates what can be saved from what cannot", () => {
    renderCard();
    expect(screen.getByText(t("correctionRecoverable"))).toBeTruthy();
    expect(screen.getByText(t("correctionEngineOnly"))).toBeTruthy();
    // The gap has to be stated, or an engine-only edit reads as safe.
    expect(screen.getByText(t("correctionEngineOnlyHint"))).toBeTruthy();
  });

  it("says so when the project was not produced by this pipeline", () => {
    renderCard({ manifest_found: false, notes: [] });
    expect(screen.getByText(t("correctionNoManifest"))).toBeTruthy();
  });

  it("marks a file with no recorded hash as unverified rather than unchanged", () => {
    const view = renderCard({
      ...REPORT,
      drifted: [{ path: "generated/godot/old/scripts/main.gd", kind: "script", hash_unknown: true }]
    });
    expect(view.getByText(t("correctionHashUnknown"))).toBeTruthy();
  });
});
