import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { ConfirmDialog, JourneyHeader } from "./primitives";
import type { JourneySnapshot } from "../productionJourney";

const t = (key: string) => key;
const snapshot: JourneySnapshot = {
  projectTitle: "Rooftop",
  engineLabel: "Godot 4",
  targetMinutes: "10",
  currentStep: "orchestrate",
  blocker: "missing binary",
  nextActionKey: "journeyNextRework",
  steps: [
    { id: "idea", state: "complete", reasonKey: "idea" },
    { id: "plan", state: "complete", reasonKey: "plan" },
    { id: "orchestrate", state: "blocked", reasonKey: "journeyNextRework" },
    { id: "execute", state: "upcoming", reasonKey: "execute" },
    { id: "review", state: "upcoming", reasonKey: "review" },
    { id: "qa", state: "upcoming", reasonKey: "qa" }
  ]
};

describe("shared production UI", () => {
  afterEach(() => cleanup());
  it("shows the current project, blocker, and next action together", () => {
    render(<JourneyHeader snapshot={snapshot} t={t} />);
    expect(screen.getByRole("heading", { name: "Rooftop" })).toBeTruthy();
    expect(screen.getByRole("status").textContent).toContain("journeyNextRework");
    expect(screen.getByRole("status").textContent).toContain("missing binary");
    expect(screen.getByText("journeyStateBlocked")).toBeTruthy();
  });

  it("keeps confirmation closed until the caller opens it", () => {
    const { rerender } = render(<ConfirmDialog open={false} title="Run" body="Writes files" confirmLabel="Run" cancelLabel="Back" onConfirm={() => undefined} onCancel={() => undefined} />);
    expect(screen.queryByRole("dialog")).toBeNull();
    rerender(<ConfirmDialog open title="Run" body="Writes files" confirmLabel="Run" cancelLabel="Back" onConfirm={() => undefined} onCancel={() => undefined} />);
    expect(screen.getByRole("dialog").textContent).toContain("Writes files");
  });

  it("moves focus into the dialog and closes from the keyboard", () => {
    const onCancel = vi.fn();
    render(<ConfirmDialog open title="Generate" body="Writes the project" confirmLabel="Generate" cancelLabel="Back" onConfirm={() => undefined} onCancel={onCancel} />);
    expect(document.activeElement).toBe(screen.getByRole("button", { name: "Generate" }));
    fireEvent.keyDown(screen.getByRole("dialog"), { key: "Escape" });
    expect(onCancel).toHaveBeenCalledOnce();
  });
});