import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { consoleI18n, makeTranslator } from "../shared/i18n";
import { AssetList, Metric, Panel, SegmentedControl, formatSavedAt, manualStatusLabel } from "./FlowConsole.parts";

/**
 * The console's own small pieces.
 *
 * These are the four components and two functions that used to sit inline at the
 * bottom of a 1200-line `FlowConsole.tsx`. They moved out for reading, not for
 * reuse -- nothing outside that file imports them -- so the tests here are not
 * about coverage. They are about the three places where "obvious" code is
 * actually a decision someone can get wrong:
 *
 *   1. `formatSavedAt` is locale-dependent and has to survive a junk value. A
 *      date that fails to parse is shown verbatim rather than as "Invalid Date",
 *      because the string came from a session log and the operator may need to
 *      read it exactly.
 *   2. `manualStatusLabel` maps three states onto three dictionary keys, and
 *      the third is a default: anything unknown reads as unavailable rather
 *      than as ready.
 *   3. `SegmentedControl` is the only producer of `.locale-option.active` on the
 *      console side, and `active` is a class defined in three stylesheets. If
 *      the selected-state class stops being applied, the control still works
 *      and just stops looking selected -- which is exactly the kind of thing
 *      that ships.
 */

const t = makeTranslator("en", consoleI18n);

afterEach(() => cleanup());

describe("formatSavedAt", () => {
  it("shows a dash when there is nothing to format", () => {
    expect(formatSavedAt(null, "en")).toBe("-");
    expect(formatSavedAt(undefined, "en")).toBe("-");
    expect(formatSavedAt("", "en")).toBe("-");
  });

  it("passes an unparseable value through instead of showing Invalid Date", () => {
    // The value comes from a session log on disk. If it is junk, the operator
    // needs to see the junk -- "Invalid Date" would hide the evidence.
    expect(formatSavedAt("not-a-date", "en")).toBe("not-a-date");
  });

  it("formats a real timestamp, and differently per locale", () => {
    const stamp = "2026-10-04T08:30:00Z";
    const english = formatSavedAt(stamp, "en");
    expect(english).not.toBe("-");
    expect(english).toContain("Oct");
    // Same instant, different locale: if these came out equal the `locale`
    // argument would be decorative and a Chinese operator would read a
    // US-formatted date with no way to notice.
    expect(formatSavedAt(stamp, "zh-CN")).not.toBe(english);
  });
});

describe("manualStatusLabel", () => {
  it("names the two real states", () => {
    expect(manualStatusLabel("ready", t)).toBe(t("manualStatusReady"));
    expect(manualStatusLabel("degraded", t)).toBe(t("manualStatusDegraded"));
  });

  it("reads anything unknown as unavailable, never as ready", () => {
    // The default matters more than it looks: a tool that reports a state this
    // build does not know about should look like it needs attention, not like
    // it is working.
    expect(manualStatusLabel(undefined, t)).toBe(t("manualStatusUnavailable"));
    expect(manualStatusLabel("something-new", t)).toBe(t("manualStatusUnavailable"));
  });
});

describe("SegmentedControl", () => {
  const OPTIONS: Array<[string, string]> = [
    ["en", "English"],
    ["zh-CN", "简体中文"]
  ];

  function renderControl(value = "en") {
    const onChange = vi.fn();
    render(<SegmentedControl label="Language" value={value} options={OPTIONS} onChange={onChange} />);
    return { onChange, buttons: screen.getAllByRole("button") };
  }

  it("marks the selected option and only that one", () => {
    const { buttons } = renderControl("en");
    expect(buttons[0].className).toContain("active");
    expect(buttons[1].className).not.toContain("active");
  });

  it("moves the mark when the value changes", () => {
    const { buttons } = renderControl("zh-CN");
    expect(buttons[0].className).not.toContain("active");
    expect(buttons[1].className).toContain("active");
  });

  it("reports the value the operator picked, not the index", () => {
    const { onChange, buttons } = renderControl("en");
    fireEvent.click(buttons[1]);
    expect(onChange).toHaveBeenCalledWith("zh-CN");
  });

  it("labels the group so the buttons are not announced as bare text", () => {
    render(
      <div>
        <SegmentedControl label="Language" value="en" options={OPTIONS} onChange={vi.fn()} />
      </div>
    );
    expect(screen.getByLabelText("Language")).toBeTruthy();
  });
});

describe("AssetList", () => {
  it("caps the visible list and says how many were dropped", () => {
    const { container } = render(<AssetList title="Assets" items={Array.from({ length: 9 }, (_, i) => `a${i}`)} />);
    expect(container.querySelectorAll("li")).toHaveLength(6);
    expect(container.textContent).toContain("+3");
  });

  it("adds no overflow marker when everything fits", () => {
    const { container } = render(<AssetList title="Assets" items={["a", "b"]} />);
    expect(container.textContent).not.toContain("+");
  });
});

describe("Metric", () => {
  it("puts the id on the value, so a test or an anchor can address it", () => {
    const { container } = render(<Metric label="Runs" value="3" id="playtest-run-count" />);
    expect(container.querySelector("#playtest-run-count")?.textContent).toBe("3");
  });
});

describe("Panel", () => {
  it("marks the active tab's panel and hides the other's", () => {
    const { container } = render(
      <>
        <Panel tab="review" activeTab="review">R</Panel>
        <Panel tab="specs" activeTab="review">S</Panel>
      </>
    );
    const review = container.querySelector("#review-panel");
    const specs = container.querySelector("#specs-panel");
    expect(review?.className).toContain("active");
    expect(specs?.className).not.toContain("active");
    expect(review?.getAttribute("data-panel")).toBe("review");
  });
});
