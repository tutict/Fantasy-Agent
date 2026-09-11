import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import { ExecutionStageCard } from "./FlowConsole";
import type { ExecuteStage } from "../shared/types";

const t = (key: string) => key;

// Vitest is configured without `globals`, so testing-library's automatic
// cleanup never registers and renders would pile up in one document.
afterEach(() => cleanup());

function renderStage(stage: ExecuteStage) {
  return render(<ExecutionStageCard stage={stage} t={t} />);
}

describe("ExecutionStageCard", () => {
  it("renders the stage name, status and detail", () => {
    renderStage({ name: "import", status: "done", detail: "headless import ok" });
    expect(screen.getByText("import")).toBeTruthy();
    expect(screen.getByText("done")).toBeTruthy();
    expect(screen.getByText("headless import ok")).toBeTruthy();
  });

  /**
   * `ExecuteStage.logs` is populated by the backend (log paths, warnings,
   * skipped assets) but was never rendered -- the type promised data the UI
   * threw away.
   */
  it("renders stage logs when the backend reports them", () => {
    renderStage({
      name: "godot",
      status: "failed",
      logs: ["godot-import.log", "missing texture: hero_albedo"]
    });
    expect(screen.getByText("stageLogs")).toBeTruthy();
    expect(screen.getByText("godot-import.log")).toBeTruthy();
    expect(screen.getByText("missing texture: hero_albedo")).toBeTruthy();
  });

  it("omits the log block when there are no logs", () => {
    renderStage({ name: "godot", status: "done", logs: [] });
    expect(screen.queryByText("stageLogs")).toBeNull();
  });

  it("renders artifacts", () => {
    renderStage({ name: "create", status: "done", artifacts: ["project.godot"] });
    expect(screen.getByText("project.godot")).toBeTruthy();
  });
});
