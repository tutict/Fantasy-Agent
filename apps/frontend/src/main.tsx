import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
// Tokens first, and only here. Every view needs them, and importing them from a
// view stylesheet would let Vite inline a second copy (see tokens.css).
import "./styles/tokens.css";
import "./styles/ui.css";
import { LocaleThemeProvider } from "./shared/localeTheme";
import { JourneyProvider } from "./shared/journeyContext";
import { StudioShell } from "./studio/StudioShell";

// One root component, one entry.
//
// `main.tsx` used to pick between three: `/web-console` rendered `FlowConsole`
// on its own, `/workbench` rendered `PlanningWorkbench` on its own, and anything
// else rendered `StudioShell`, which then embedded both of the others in
// iframes. So the same view had two chromes depending on how you reached it, and
// the shell had to hand locale and theme across the frame boundary through
// `?locale=` / `?theme=` query parameters.
//
// The pathname still selects the view -- `StudioShell` reads it once and keeps
// `/web-console` and `/workbench` working as deep links -- but every path now
// renders the same shell around it.
declare global {
  interface Window {
    __fantasyAgentRoot?: ReturnType<typeof createRoot>;
  }
}

const rootElement = document.getElementById("root");
if (!rootElement) throw new Error("Missing #root container");
const root = window.__fantasyAgentRoot ?? createRoot(rootElement);
window.__fantasyAgentRoot = root;
root.render(
  <StrictMode>
    <LocaleThemeProvider>
        <JourneyProvider>
      <StudioShell />
    </JourneyProvider>
      </LocaleThemeProvider>
  </StrictMode>
);
