import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { FlowConsole } from "./console/FlowConsole";
import { StudioShell } from "./studio/StudioShell";

function App() {
  if (window.location.pathname.startsWith("/web-console")) {
    return <FlowConsole />;
  }
  return <StudioShell />;
}

createRoot(document.getElementById("root") as HTMLElement).render(
  <StrictMode>
    <App />
  </StrictMode>
);
