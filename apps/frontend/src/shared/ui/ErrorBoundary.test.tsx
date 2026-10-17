import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { makeTranslator, studioI18n } from "../i18n";
import { ErrorBoundary } from "./ErrorBoundary";

afterEach(() => {
  // RTL registers its automatic cleanup through a *global* `afterEach`, and this
  // project runs vitest with `globals: false` -- so it never registers. Without
  // this the DOM accumulates across the tests in a file, and a `getByText` in a
  // later test then matches an earlier test's tree: a pass that proves nothing,
  // which is worse here than anywhere else because every test after the first
  // renders the same fallback text.
  cleanup();
});

/**
 * The boundary is the only thing between one panel's render error and a white
 * window, so it is tested directly rather than only through the shell.
 *
 * The shell-level case can show one panel crashing; what it cannot show is the
 * pair of properties that make a boundary worth having at all -- the throwing
 * subtree is replaced, and nothing outside it is touched. Both are visible
 * here, and the second is the one a wrong implementation gets wrong: a boundary
 * that unmounts its parent's siblings, or one that swallows the error without
 * replacing anything, passes a shell test that only asserts the fallback text.
 */

const t = makeTranslator("en", studioI18n);

/** A component that throws during render, which is the only thing caught here. */
function Boom(): never {
  throw new Error("probe: this subtree always throws");
}

describe("ErrorBoundary", () => {
  it("renders its children while nothing has thrown", () => {
    render(
      <ErrorBoundary t={t}>
        <p>the real panel content</p>
      </ErrorBoundary>
    );

    expect(screen.getByText("the real panel content")).toBeTruthy();
    expect(screen.queryByText(t("panelCrashedTitle"))).toBeNull();
  });

  it("replaces the subtree that threw and leaves the rest of the tree alone", () => {
    // React logs a caught error; without this the output carries a stack trace
    // for a throw that is the entire point of the test.
    const logged = vi.spyOn(console, "error").mockImplementation(() => {});

    render(
      <div>
        <ErrorBoundary t={t}>
          <Boom />
        </ErrorBoundary>
        <p>the panel that has to survive</p>
      </div>
    );

    expect(screen.getByText(t("panelCrashedTitle"))).toBeTruthy();
    expect(screen.getByText("the panel that has to survive")).toBeTruthy();
    expect(screen.queryByText("the real panel content")).toBeNull();

    logged.mockRestore();
  });

  it("reports the catch, because production React does not", () => {
    // `componentDidCatch` is what makes a caught error audible outside
    // development: React's own "the above error occurred in..." report is
    // dev-only, so without this line the fallback would appear and nothing
    // anywhere would record that the panel threw. The message is matched
    // rather than the call index, because React logs its own report too and
    // the order between the two is not something to depend on.
    const logged = vi.spyOn(console, "error").mockImplementation(() => {});

    render(
      <ErrorBoundary t={t}>
        <Boom />
      </ErrorBoundary>
    );

    const messages = logged.mock.calls.map((call) => String(call[0]));
    expect(messages.some((message) => message.includes("replaced by its fallback"))).toBe(true);

    logged.mockRestore();
  });

  it("shows the fallback in the locale the shell is in", () => {
    // The fallback text is the panel's own i18n, not a hardcoded English
    // string: the boundary is rendered by the shell, so it inherits the
    // shell's translator. A hardcoded string here would be the one part of the
    // UI that ignores the locale switch.
    const zh = makeTranslator("zh-CN", studioI18n);
    const logged = vi.spyOn(console, "error").mockImplementation(() => {});

    render(
      <ErrorBoundary t={zh}>
        <Boom />
      </ErrorBoundary>
    );

    expect(screen.getByText("这个面板出错了")).toBeTruthy();

    logged.mockRestore();
  });
});
