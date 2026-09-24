import { render, screen, waitFor } from "@testing-library/react";
import { useEffect } from "react";
import { describe, expect, it } from "vitest";
import { JourneyProvider, useJourney } from "./journeyContext";

function Reporter() {
  const { snapshot, update } = useJourney();
  useEffect(() => {
    update({ plan: { gameplay_spec: { title: "Rooftop" }, production_pipeline: { stages: [{ id: "godot_quick_play" }] } }, session: { session_id: "sess", stages: [{ status: "done" }] }, executionStatus: "failed" });
  }, [update]);
  return <p>{snapshot.currentStep}:{snapshot.projectTitle}</p>;
}

describe("shared journey context", () => {
  it("lets one view update the snapshot every view reads", async () => {
    render(<JourneyProvider><Reporter /></JourneyProvider>);
    await waitFor(() => expect(screen.getByText("execute:Rooftop")).toBeTruthy());
  });
});
