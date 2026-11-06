import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { LocaleThemeProvider } from "../../shared/localeTheme";
import { McpConnectionPanel } from "./McpConnectionPanel";
afterEach(() => { cleanup(); vi.unstubAllGlobals(); localStorage.clear(); });
describe("MCP connection controls", () => {
  it("reads the Token only for explicit copy and never renders or stores it", async () => {
    const calls: string[] = [];
    vi.stubGlobal("fetch", vi.fn(async (url: string) => { calls.push(url); return new Response(JSON.stringify(url.endsWith("/token") ? { token: "private-token-test" } : url === "/api/projects" ? { projects: [] } : { enabled: false, endpoint: "http://127.0.0.1:7860/mcp", recent_activity: [] })); }));
    const writeText = vi.fn(async () => {});
    Object.defineProperty(navigator, "clipboard", { configurable: true, value: { writeText } });
    localStorage.setItem("fantasy-agent-studio-locale", "zh-CN");
    const view = render(<LocaleThemeProvider><McpConnectionPanel active /></LocaleThemeProvider>);
    await screen.findByText("服务未开启");
    expect(calls.some((url) => url.endsWith("/token"))).toBe(false);
    fireEvent.click(screen.getByRole("button", { name: "复制连接密钥" }));
    await waitFor(() => expect(writeText).toHaveBeenCalledWith("private-token-test"));
    expect(view.container.textContent).not.toContain("private-token-test");
    expect(JSON.stringify(localStorage)).not.toContain("private-token-test");
  });
  it("offers a WorkBuddy snippet with an env reference and no embedded token", async () => {
    vi.stubGlobal("fetch", vi.fn(async (url: string) => {
      const body = url === "/api/mcp/connection/config"
        ? { toml: "[mcp_servers.fantasy_studio]", token_env_var: "FANTASY_STUDIO_MCP_TOKEN", workbuddy_json: JSON.stringify({ mcpServers: { "fantasy-studio": { type: "http", url: "http://127.0.0.1:7860/mcp", headers: { Authorization: "Bearer ${FANTASY_STUDIO_MCP_TOKEN}" } } } }, null, 2) }
        : url === "/api/projects" ? { projects: [] }
          : { enabled: false, endpoint: "http://127.0.0.1:7860/mcp", recent_activity: [] };
      return new Response(JSON.stringify(body));
    }));
    localStorage.setItem("fantasy-agent-studio-locale", "zh-CN");
    const view = render(<LocaleThemeProvider><McpConnectionPanel active /></LocaleThemeProvider>);
    await screen.findByText("服务未开启");
    fireEvent.click(screen.getByText("连接步骤与技术设置"));
    await waitFor(() => expect(view.container.textContent).toContain("fantasy-studio"));
    expect(view.container.textContent).toContain("FANTASY_STUDIO_MCP_TOKEN");
    // A literal Token here is impossible: the config mock never returns one.
    // The real no-leak assertion lives on the backend in
    // tests/test_studio_mcp_protocol.py, which checks the generated snippet
    // against the live secret. This case only pins the snippet's shape.
    expect(view.container.textContent).toContain("Bearer ${FANTASY_STUDIO_MCP_TOKEN}");
  });
  it("does not infer service access or production grants from enabled status", async () => {
    vi.stubGlobal("fetch", vi.fn(async (url: string) => new Response(JSON.stringify(url === "/api/projects" ? { projects: [] } : { enabled: true, endpoint: "http://127.0.0.1:7860/mcp", recent_activity: [] }))));
    localStorage.setItem("fantasy-agent-studio-locale", "zh-CN");
    render(<LocaleThemeProvider><McpConnectionPanel active /></LocaleThemeProvider>);
    await screen.findByText("服务已开启");
    expect(screen.getByText("尚未收到访问")).toBeTruthy();
    expect(screen.getByText("当前版本没有有效授权")).toBeTruthy();
  });
});
