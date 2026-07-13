import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { FlowConsole } from "./console/FlowConsole";
import { StudioShell } from "./studio/StudioShell";

function normalizedPathname() {
  const base = import.meta.env.BASE_URL.replace(/\/$/, "");
  const pathname = window.location.pathname;
  if (base && base !== "/" && pathname.startsWith(base)) {
    return pathname.slice(base.length) || "/";
  }
  return pathname;
}

function App() {
  if (normalizedPathname().startsWith("/web-console")) {
    return <FlowConsole />;
  }
  return <StudioShell />;
}

createRoot(document.getElementById("root") as HTMLElement).render(
  <StrictMode>
    <App />
  </StrictMode>
);
