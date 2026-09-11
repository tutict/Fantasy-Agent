import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { FlowConsole } from "./console/FlowConsole";
import { StudioShell } from "./studio/StudioShell";
import { PlanningWorkbench } from "./workbench/PlanningWorkbench";

function normalizedPathname() {
  const base = import.meta.env.BASE_URL.replace(/\/$/, "");
  const pathname = window.location.pathname;
  if (base && base !== "/" && pathname.startsWith(base)) {
    return pathname.slice(base.length) || "/";
  }
  return pathname;
}

function App() {
  const pathname = normalizedPathname();
  if (pathname.startsWith("/web-console")) {
    return <FlowConsole />;
  }
  if (pathname.startsWith("/workbench")) {
    return <PlanningWorkbench />;
  }
  return <StudioShell />;
}

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
    <App />
  </StrictMode>
);