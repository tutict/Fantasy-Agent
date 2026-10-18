import { Component, type ErrorInfo, type ReactNode } from "react";

import type { Translator } from "../i18n";

/**
 * One panel's crash stays that panel's crash.
 *
 * `architecture.md` §1.1 keeps every visited panel mounted forever -- the
 * console polls a job in flight and the workbench holds an unsaved
 * conversation, so unmounting on a panel switch is not on the table. The price
 * of that decision is that the panels share one React tree, and an error
 * thrown during render takes the whole tree with it: one bad panel used to be
 * a white window, sidebar and all.
 *
 * **A boundary per panel, not one around all of them.** A shared boundary
 * would still lose every panel's content to the one that threw, which is most
 * of the shell. Per-panel, the nav and the other panels keep working, and what
 * the user sees is "this panel is broken" rather than "the app is broken".
 *
 * **It wraps the children, so it sits inside each panel's `<section>`.** The
 * section carries the `data-panel` attribute and the `active` class that CSS
 * visibility depends on; replacing the section itself would break panel
 * switching and every test that queries the frame. Replacing only what is
 * inside leaves the frame standing with a stand-in in it.
 *
 * **It owns its fallback rather than taking one as a prop.** Six call sites
 * need the identical stand-in, and a `fallback` prop would be the same JSX
 * written six times -- with the one thing that must not differ between panels
 * left to each caller to get right. The boundary is in `shared/ui/` next to
 * `primitives.tsx`, where `JourneyHeader` takes a translator the same way.
 *
 * **`componentDidCatch` is the reason this is a class component, and it is not
 * decoration.** React prints the "the above error occurred in..." report in
 * development only; in production a caught error is otherwise silent, so the
 * user would see the fallback and nothing anywhere would say the panel threw.
 * Logging here keeps the catch audible, the same way the backend reports a
 * degraded load instead of swallowing it.
 *
 * The error itself is logged and never rendered: a thrown value can carry
 * paths and internals, the user can act on neither, and the console already
 * has the stack.
 *
 * The fallback has no button on purpose. Re-rendering a subtree that threw
 * deterministically throws again, so a retry control would be a lie; the real
 * recovery is a reload, which is what the message says. It also keeps the
 * fallback free of focusable elements, which is what keeps `:focus-visible`
 * out of it -- the focus ring has exactly one home (`ui.css`) and
 * `cssHygiene.test.ts` fails the build if a second one appears.
 *
 * The class is `wb-empty`, the shared panels' empty state, because this is the
 * same situation wearing a different hat: a panel with nothing to show. It is
 * styled by `workbench.css`, which is always in the shell's graph --
 * `StudioShell` imports `PlanningWorkbench`, which imports that sheet at module
 * level, so the rules are present on every route rather than only on the one
 * that mounts the workbench.
 */
export class ErrorBoundary extends Component<
  { t: Translator; children: ReactNode },
  { error: Error | null }
> {
  state: { error: Error | null } = { error: null };

  static getDerivedStateFromError(error: Error): { error: Error | null } {
    return { error };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error("a panel subtree threw and was replaced by its fallback", error, info.componentStack);
  }

  render() {
    if (this.state.error !== null) {
      return (
        <p className="wb-empty">
          <strong>{this.props.t("panelCrashedTitle")}</strong>
          <br />
          {this.props.t("panelCrashedBody")}
        </p>
      );
    }
    return this.props.children;
  }
}
