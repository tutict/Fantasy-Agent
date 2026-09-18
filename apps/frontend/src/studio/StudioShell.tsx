import { useCallback, useEffect, useMemo, useState } from "react";
import type { CSSProperties } from "react";
import {
  deleteLlmSettings,
  getLlmSettings,
  getMcpStatus,
  getToolCatalog,
  putLlmSettings,
  runAgent,
  testLlmSettings
} from "../shared/api";
import { makeTranslator, studioI18n } from "../shared/i18n";
import {
  HANDOFF_KEY,
  STUDIO_LOCALE_KEY,
  STUDIO_SIDEBAR_COLLAPSED_KEY,
  STUDIO_SIDEBAR_WIDTH_KEY,
  THEME_KEY,
  initialLocale,
  initialTheme
} from "../shared/storage";
import type {
  AgentRunResult,
  Locale,
  LlmApiSettings,
  McpService,
  McpStatus,
  Theme,
  ToolCatalog,
  ToolPermission
} from "../shared/types";
import "../styles/studio.css";

type PanelKey = "workbench" | "console" | "mcp" | "api" | "agent";

const panels: Record<PanelKey, { titleKey: string; icon: string }> = {
  workbench: { titleKey: "workbench", icon: "PL" },
  console: { titleKey: "console", icon: "FC" },
  mcp: { titleKey: "mcp", icon: "MC" },
  api: { titleKey: "api", icon: "AI" },
  agent: { titleKey: "agent", icon: "AG" }
};

export function StudioShell() {
  const [locale, setLocale] = useState<Locale>(() => initialLocale(STUDIO_LOCALE_KEY));
  const [theme, setTheme] = useState<Theme>(() => initialTheme());
  const [activePanel, setActivePanel] = useState<PanelKey>("workbench");
  const [sidebarCollapsed, setSidebarCollapsed] = useState(() => localStorage.getItem(STUDIO_SIDEBAR_COLLAPSED_KEY) === "1");
  const [sidebarWidth, setSidebarWidth] = useState(() => {
    const stored = Number(localStorage.getItem(STUDIO_SIDEBAR_WIDTH_KEY));
    return Number.isFinite(stored) && stored > 0 ? stored : 282;
  });
  const [mcpStatus, setMcpStatus] = useState<McpStatus | null>(null);
  const [mcpError, setMcpError] = useState<string | null>(null);
  const [checkingMcp, setCheckingMcp] = useState(false);

  const t = useMemo(() => makeTranslator(locale, studioI18n), [locale]);

  useEffect(() => {
    document.documentElement.lang = locale;
    document.title = t("documentTitle");
    localStorage.setItem(STUDIO_LOCALE_KEY, locale);
  }, [locale, t]);

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    localStorage.setItem(THEME_KEY, theme);
  }, [theme]);

  useEffect(() => {
    localStorage.setItem(STUDIO_SIDEBAR_COLLAPSED_KEY, sidebarCollapsed ? "1" : "0");
  }, [sidebarCollapsed]);

  useEffect(() => {
    localStorage.setItem(STUDIO_SIDEBAR_WIDTH_KEY, String(sidebarWidth));
  }, [sidebarWidth]);

  const loadMcpStatus = useCallback(async () => {
    setCheckingMcp(true);
    setMcpError(null);
    try {
      setMcpStatus(await getMcpStatus(selectedEngineVersion()));
    } catch (error) {
      setMcpStatus(null);
      setMcpError(String(error));
    } finally {
      setCheckingMcp(false);
    }
  }, []);

  useEffect(() => {
    if (activePanel === "mcp" && !mcpStatus && !checkingMcp) {
      void loadMcpStatus();
    }
  }, [activePanel, checkingMcp, loadMcpStatus, mcpStatus]);

  const localizedHref = (href: string, params: Record<string, string> = {}) => {
    const search = new URLSearchParams({ locale, theme, ...params });
    const base = import.meta.env.BASE_URL.replace(/\/$/, "");
    const frontendRoute = href === "/web-console" && import.meta.env.DEV && base ? `${base}${href}` : href;
    return `${frontendRoute}?${search.toString()}`;
  };

  return (
    <main
      className={`studio-shell ${sidebarCollapsed ? "sidebar-collapsed" : ""}`}
      style={{ "--sidebar-width": `${sidebarWidth}px` } as CSSProperties}
    >
      <aside className="studio-sidebar">
        <header className="studio-sidebar-header">
          <div className="brand-mark">FA</div>
          <div className="brand">
            <p>{t("productLabel")}</p>
            <h1>Fantasy Agent</h1>
          </div>
          <button
            className="collapse-button"
            type="button"
            id="sidebar-toggle"
            aria-expanded={!sidebarCollapsed}
            aria-label={sidebarCollapsed ? t("expandSidebar") : t("collapseSidebar")}
            title={sidebarCollapsed ? t("expandSidebar") : t("collapseSidebar")}
            onClick={() => setSidebarCollapsed((collapsed) => !collapsed)}
          >
            {sidebarCollapsed ? ">" : "<"}
          </button>
        </header>

        <div className="locale-switch" aria-label="Interface language">
          <button className={`locale-option ${locale === "en" ? "active" : ""}`} type="button" data-locale="en" onClick={() => setLocale("en")}>
            EN
          </button>
          <button className={`locale-option ${locale === "zh-CN" ? "active" : ""}`} type="button" data-locale="zh-CN" onClick={() => setLocale("zh-CN")}>
            中文
          </button>
        </div>

        <div className="theme-switch" aria-label="Theme">
          <button className={`theme-option ${theme === "dark" ? "active" : ""}`} type="button" data-theme-choice="dark" onClick={() => setTheme("dark")}>
            {t("themeDark")}
          </button>
          <button className={`theme-option ${theme === "light" ? "active" : ""}`} type="button" data-theme-choice="light" onClick={() => setTheme("light")}>
            {t("themeLight")}
          </button>
        </div>

        <nav className="studio-nav" aria-label="Studio panels">
          {(Object.entries(panels) as Array<[PanelKey, { titleKey: string; icon: string }]>).map(([key, panel]) => (
            <button className={activePanel === key ? "active" : ""} type="button" data-target={key} key={key} onClick={() => setActivePanel(key)}>
              <span className="nav-icon">{panel.icon}</span>
              <span className="nav-label">{t(panel.titleKey)}</span>
            </button>
          ))}
        </nav>

        <section className="studio-status">
          <strong>{t(panels[activePanel].titleKey)}</strong>
          <code>{panelEndpoint(activePanel)}</code>
        </section>

        <div
          className="sidebar-resizer"
          id="sidebar-resizer"
          role="separator"
          aria-orientation="vertical"
          onPointerDown={(event) => {
            if (sidebarCollapsed) setSidebarCollapsed(false);
            const target = event.currentTarget;
            target.setPointerCapture(event.pointerId);
          }}
          onPointerMove={(event) => {
            if (!event.currentTarget.hasPointerCapture(event.pointerId)) return;
            setSidebarWidth(Math.max(220, Math.min(430, event.clientX)));
          }}
          onPointerUp={(event) => {
            if (event.currentTarget.hasPointerCapture(event.pointerId)) {
              event.currentTarget.releasePointerCapture(event.pointerId);
            }
          }}
        />
      </aside>

      <section className="studio-main">
        <header className="studio-topbar">
          <div>
            <p>{t("productLabel")}</p>
            <h2 id="panel-title">{t(panels[activePanel].titleKey)}</h2>
          </div>
        </header>

        <section className="studio-panel-frame">
          <iframe
            className={`studio-frame ${activePanel === "workbench" ? "active" : ""}`}
            data-frame="workbench"
            data-panel="workbench"
            title={t("workbenchFrameTitle")}
            src={localizedHref("/workbench", { embed: "1" })}
          />
          <iframe
            className={`studio-frame ${activePanel === "console" ? "active" : ""}`}
            data-frame="console"
            data-panel="console"
            title={t("consoleFrameTitle")}
            src={localizedHref("/web-console", { embed: "1" })}
          />
          <section className={`mcp-panel ${activePanel === "mcp" ? "active" : ""}`} data-panel="mcp">
            <div className="mcp-header">
              <div>
                <h3>{t("mcpStatusTitle")}</h3>
                <p>{t("mcpStatusHint")}</p>
              </div>
              <button className="primary-action" type="button" id="mcp-refresh" onClick={() => void loadMcpStatus()} disabled={checkingMcp}>
                {t("mcpRefresh")}
              </button>
            </div>
            <p className="mcp-summary" id="mcp-status-summary">
              {checkingMcp
                ? t("mcpChecking")
                : mcpStatus
                  ? `${t("mcpSelectedEngine")}: ${mcpStatus.engine || selectedEngineVersion()} - ${mcpStatus.required_ready ?? 0}/${mcpStatus.required_total ?? 0} ${t("mcpStatusSummary")}`
                  : t("mcpChecking")}
            </p>
            <div className="mcp-status-grid" id="mcp-status-grid">
              {mcpError ? (
                <article className="mcp-status-card mcp-status-error" data-state="unavailable">
                  <p>{t("mcpCheckFailed")}: {mcpError}</p>
                </article>
              ) : (
                (mcpStatus?.services || []).map((service) => <McpCard key={service.id} service={service} t={t} />)
              )}
            </div>
          </section>
          <section className={`api-panel ${activePanel === "api" ? "active" : ""}`} data-panel="api">
            <ApiSettingsPanel t={t} />
          </section>
          <section className={`agent-panel ${activePanel === "agent" ? "active" : ""}`} data-panel="agent">
            <AgentPanel t={t} />
          </section>
        </section>
      </section>
    </main>
  );
}

function panelEndpoint(panel: PanelKey) {
  if (panel === "mcp") return "/api/tool-status";
  if (panel === "console") return "/web-console";
  if (panel === "api") return "/api/settings/llm";
  if (panel === "agent") return "/api/agent/run";
  return "/workbench";
}

type Translator = (key: string, args?: Record<string, unknown>) => string;

function ApiSettingsPanel({ t }: { t: Translator }) {
  const [settings, setSettings] = useState<LlmApiSettings | null>(null);
  const [enabled, setEnabled] = useState(false);
  const [provider, setProvider] = useState("anthropic");
  const [baseUrl, setBaseUrl] = useState("");
  const [model, setModel] = useState("");
  const [apiKey, setApiKey] = useState("");
  const [timeoutSeconds, setTimeoutSeconds] = useState(60);
  const [busy, setBusy] = useState(false);
  const [summary, setSummary] = useState("");
  const [failed, setFailed] = useState(false);

  const apply = useCallback((payload: LlmApiSettings) => {
    setSettings(payload);
    setEnabled(Boolean(payload.enabled));
    setProvider(payload.provider || "anthropic");
    setBaseUrl(payload.base_url || "");
    setModel(payload.model || "");
    // The backend only ever returns a masked key, so never echo it into the field.
    setApiKey("");
    setTimeoutSeconds(Math.round(payload.timeout_seconds ?? 60));
  }, []);

  const load = useCallback(async () => {
    setBusy(true);
    try {
      apply(await getLlmSettings());
      setFailed(false);
    } catch (error) {
      setSummary(`${t("apiLoadFailed")} ${error}`);
      setFailed(true);
    } finally {
      setBusy(false);
    }
  }, [apply, t]);

  useEffect(() => {
    void load();
  }, [load]);

  const collect = () => ({
    enabled,
    provider,
    base_url: baseUrl,
    model,
    api_key: apiKey,
    timeout_seconds: timeoutSeconds
  });

  const save = async (testAfter: boolean) => {
    setBusy(true);
    try {
      const payload = await putLlmSettings(collect());
      if (payload.error) {
        setSummary(`${t("apiSaveFailed")} ${payload.error}`);
        setFailed(true);
        return;
      }
      apply(payload);
      setSummary(t("apiSaveOk"));
      setFailed(false);
      if (testAfter) await runTest();
    } catch (error) {
      setSummary(`${t("apiSaveFailed")} ${error}`);
      setFailed(true);
    } finally {
      setBusy(false);
    }
  };

  const runTest = async () => {
    setBusy(true);
    setSummary(t("apiTesting"));
    try {
      const payload = await testLlmSettings(collect());
      if (payload.settings) apply(payload.settings);
      const message = payload.detail_key ? t(payload.detail_key, { ms: payload.latency_ms ?? 0, detail: payload.detail }) : payload.detail || "";
      setSummary(payload.ok ? `${t("apiStateReady")} · ${message}` : message || t("apiSaveFailed"));
      setFailed(!payload.ok);
    } catch (error) {
      setSummary(`${t("apiSaveFailed")} ${error}`);
      setFailed(true);
    } finally {
      setBusy(false);
    }
  };

  const clear = async () => {
    setBusy(true);
    try {
      apply(await deleteLlmSettings());
      setSummary(t("apiClearOk"));
      setFailed(false);
    } catch (error) {
      setSummary(`${t("apiSaveFailed")} ${error}`);
      setFailed(true);
    } finally {
      setBusy(false);
    }
  };

  const keyLabel = settings?.api_key_configured
    ? `${settings.api_key_masked || ""} (${settings.api_key_source === "environment" ? t("apiKeyEnv") : t("apiKeyStored")})`
    : t("apiKeyNone");

  return (
    <>
      <div className="api-header">
        <div>
          <h3>{t("apiTitle")}</h3>
          <p>{t("apiHint")}</p>
        </div>
        <button className="primary-action" type="button" id="api-refresh" onClick={() => void load()} disabled={busy}>
          {t("apiRefresh")}
        </button>
      </div>

      <form
        className="api-form"
        id="api-form"
        autoComplete="off"
        onSubmit={(event) => {
          event.preventDefault();
          void save(false);
        }}
      >
        <label className="api-toggle">
          <input type="checkbox" id="api-enabled" checked={enabled} onChange={(event) => setEnabled(event.target.checked)} />
          <span>{t("apiEnabled")}</span>
        </label>

        <div className="api-field">
          <label htmlFor="api-provider">{t("apiProvider")}</label>
          <select id="api-provider" value={provider} onChange={(event) => setProvider(event.target.value)}>
            <option value="anthropic">anthropic</option>
            <option value="openai_compatible">openai_compatible</option>
            <option value="openai_responses">openai_responses (GPT-6 Astra)</option>
          </select>
        </div>

        <div className="api-field">
          <label htmlFor="api-base-url">{t("apiBaseUrl")}</label>
          <input id="api-base-url" type="text" spellCheck={false} placeholder="https://api.anthropic.com" value={baseUrl} onChange={(event) => setBaseUrl(event.target.value)} />
        </div>

        <div className="api-field">
          <label htmlFor="api-model">{t("apiModel")}</label>
          <input id="api-model" type="text" spellCheck={false} placeholder="claude-opus-4-8" value={model} onChange={(event) => setModel(event.target.value)} />
        </div>

        <div className="api-field">
          <label htmlFor="api-key">{t("apiKey")}</label>
          <input id="api-key" type="password" autoComplete="off" spellCheck={false} placeholder={t("apiKeyPlaceholder")} value={apiKey} onChange={(event) => setApiKey(event.target.value)} />
        </div>

        <div className="api-field">
          <label htmlFor="api-timeout">{t("apiTimeout")}</label>
          <input id="api-timeout" type="number" min={5} max={600} step={1} value={timeoutSeconds} onChange={(event) => setTimeoutSeconds(Number(event.target.value))} />
        </div>

        <div className="api-actions">
          <button className="primary-action" type="button" id="api-save" disabled={busy} onClick={() => void save(false)}>
            {t("apiSave")}
          </button>
          <button className="primary-action" type="button" id="api-test" disabled={busy} onClick={() => void runTest()}>
            {t("apiTest")}
          </button>
          <button className="primary-action" type="button" id="api-clear" disabled={busy} onClick={() => void clear()}>
            {t("apiClear")}
          </button>
        </div>
      </form>

      <p className="api-summary" id="api-summary" data-state={failed ? "error" : "ok"}>
        {summary || (settings ? (settings.ready ? t("apiStateReady") : t("apiStateDisabled")) : t("apiStateIdle"))}
      </p>

      <div className="api-state-grid" id="api-state-grid" aria-live="polite">
        <article className="api-state-card">
          <span>{t("apiStatusReady")}</span>
          <strong>{settings?.ready ? t("apiStateReady") : t("apiStateDisabled")}</strong>
        </article>
        <article className="api-state-card">
          <span>{t("apiStatusKey")}</span>
          <code>{keyLabel}</code>
        </article>
        <article className="api-state-card">
          <span>{t("apiStatusEndpoint")}</span>
          <code>{settings?.base_url || "-"}</code>
        </article>
        <article className="api-state-card">
          <span>{t("apiConfigPath")}</span>
          <code>{settings?.config_path || "-"}</code>
        </article>
      </div>
    </>
  );
}

/**
 * The tool list an agent is actually offered, with the tier the gate enforces.
 *
 * The Agent panel used to show only what a run *did* (calls, refusals). A run
 * that made no calls looked the same whether the model declined to act or the
 * tools were never available, and nothing showed which of the offered tools
 * needed a grant before they would do anything.
 *
 * Collapsed by default, and loaded only when opened: the catalog is 20 rows and
 * most visits to this panel are to type a goal and press Run. Fetching it
 * eagerly would spend a request on a section nobody opened.
 */
/**
 * Exported for its own test. It is still only mounted from `StudioShell`; the
 * export exists because the panel is 100 lines of user-visible copy (the
 * permission tiers, the "declared but not implemented" gap, the argument flags)
 * and mounting the whole shell to reach it would drag in every other panel's
 * network calls along with it.
 */
export function ToolCatalogPanel({ t }: { t: Translator }) {
  const [open, setOpen] = useState(false);
  const [catalog, setCatalog] = useState<ToolCatalog | null>(null);
  const [busy, setBusy] = useState(false);
  const [failure, setFailure] = useState("");

  const load = useCallback(async () => {
    setBusy(true);
    try {
      setCatalog(await getToolCatalog());
      setFailure("");
    } catch (error) {
      setCatalog(null);
      setFailure(`${t("toolsLoadFailed")} ${error}`);
    } finally {
      setBusy(false);
    }
  }, [t]);

  const toggle = () => {
    const next = !open;
    setOpen(next);
    if (next && !catalog && !busy) void load();
  };

  const tools = catalog?.tools || [];
  const counts = catalog?.permission_counts || {};
  const unimplemented = catalog?.declared_without_implementation || [];
  // Only the engine half derives its tier from MCP annotations; separating the
  // two lists keeps "these four planning tools are always read-only" from
  // reading as a claim about the bridges.
  const planning = tools.filter((tool) => tool.source === "planning");
  const engine = tools.filter((tool) => tool.source !== "planning");

  const renderRow = (tool: (typeof tools)[number]) => (
    <article className="tool-row" data-permission={tool.permission} key={tool.name}>
      <div className="tool-row-top">
        <code>{tool.name}</code>
        <span className="tool-tier">{tool.permission}</span>
      </div>
      {tool.server ? <p className="tool-row-server">{tool.server}</p> : null}
      {tool.description ? <p className="tool-row-desc">{tool.description}</p> : null}
      {tool.confirm_field ? (
        <p className="tool-row-flag">
          {t("toolConfirmField")}: <code>{tool.confirm_field}</code>
        </p>
      ) : null}
      {tool.plan_key ? (
        <p className="tool-row-flag">
          {t("toolPlanKey")}: <code>{tool.plan_key}</code>
        </p>
      ) : null}
      {tool.hidden_args?.length ? (
        <p className="tool-row-flag">
          {t("toolHiddenArgs")}: <code>{tool.hidden_args.join(", ")}</code>
        </p>
      ) : null}
      {tool.executable_args?.length ? (
        <p className="tool-row-flag tool-row-flag-danger">
          {/* Named separately from hidden_args because these are also
              overwritten on every call -- a model that sends one is ignored,
              not trusted. */}
          {t("toolExecutableArgs")}: <code>{tool.executable_args.join(", ")}</code>
        </p>
      ) : null}
    </article>
  );

  return (
    <section className="tool-catalog" id="tool-catalog">
      <header className="tool-catalog-head">
        <div>
          <h3>{t("toolsTitle")}</h3>
          <p>{t("toolsHint")}</p>
        </div>
        <button className="primary-action" type="button" id="tool-catalog-toggle" onClick={toggle}>
          {open ? t("toolsHide") : t("toolsShow")}
        </button>
      </header>

      {failure ? (
        <p className="agent-note agent-note-danger" id="tool-catalog-error">
          {failure}
        </p>
      ) : null}

      {open ? (
        <>
          <p className="tool-catalog-summary" id="tool-catalog-summary">
            {busy
              ? t("toolsLoading")
              : t("toolsSummary", {
                  total: tools.length,
                  readOnly: counts.read_only ?? 0,
                  write: counts.write ?? 0,
                  execute: counts.execute ?? 0
                })}
          </p>

          <div className="tool-catalog-group">
            <h4>{t("toolsPlanningGroup")}</h4>
            {planning.map(renderRow)}
          </div>

          <div className="tool-catalog-group">
            <h4>{t("toolsEngineGroup")}</h4>
            {engine.map(renderRow)}
          </div>

          {unimplemented.length ? (
            <p className="tool-catalog-gap" id="tool-catalog-gap">
              {t("toolsDeclaredOnly")}: <code>{unimplemented.join(", ")}</code>
            </p>
          ) : null}
        </>
      ) : null}
    </section>
  );
}

function AgentPanel({ t }: { t: Translator }) {
  const [goal, setGoal] = useState("");
  const [maxTurns, setMaxTurns] = useState(8);
  const [engineTools, setEngineTools] = useState(false);
  const [allowWrite, setAllowWrite] = useState(false);
  const [allowExecute, setAllowExecute] = useState(false);
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<AgentRunResult | null>(null);
  const [failure, setFailure] = useState("");

  const calls = (result?.steps || []).flatMap((step) => step.calls || []);
  const refusals = result?.refusals || [];

  const run = async () => {
    if (!goal.trim()) {
      setFailure(t("agentEmpty"));
      return;
    }
    setBusy(true);
    setFailure("");
    setResult(null);
    try {
      setResult(
        await runAgent({
          goal: goal.trim(),
          max_turns: maxTurns,
          include_engine_tools: engineTools,
          allow_write: allowWrite,
          allow_execute: allowExecute
        })
      );
    } catch (error) {
      setFailure(`${t("agentFailed")} ${error}`);
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
      <div className="api-header">
        <div>
          <h3>{t("agentTitle")}</h3>
          <p>{t("agentHint")}</p>
        </div>
      </div>

      <form
        className="api-form"
        id="agent-form"
        autoComplete="off"
        onSubmit={(event) => {
          event.preventDefault();
          void run();
        }}
      >
        <div className="api-field">
          <label htmlFor="agent-goal">{t("agentGoal")}</label>
          <textarea
            id="agent-goal"
            rows={3}
            value={goal}
            placeholder={t("agentGoalPlaceholder")}
            onChange={(event) => setGoal(event.target.value)}
          />
        </div>

        <div className="api-field">
          <label htmlFor="agent-max-turns">{t("agentMaxTurns")}</label>
          <input
            id="agent-max-turns"
            type="number"
            min={1}
            max={16}
            step={1}
            value={maxTurns}
            onChange={(event) => setMaxTurns(Number(event.target.value))}
          />
        </div>

        <label className="api-toggle">
          <input
            type="checkbox"
            id="agent-engine-tools"
            checked={engineTools}
            onChange={(event) => setEngineTools(event.target.checked)}
          />
          <span>{t("agentEngineTools")}</span>
        </label>
        {engineTools ? <p className="agent-note">{t("agentEngineToolsHint")}</p> : null}

        <label className="api-toggle">
          <input
            type="checkbox"
            id="agent-allow-write"
            checked={allowWrite}
            onChange={(event) => setAllowWrite(event.target.checked)}
          />
          <span>{t("agentAllowWrite")}</span>
        </label>

        <label className="api-toggle">
          <input
            type="checkbox"
            id="agent-allow-execute"
            checked={allowExecute}
            onChange={(event) => setAllowExecute(event.target.checked)}
          />
          <span>{t("agentAllowExecute")}</span>
        </label>
        {allowExecute ? <p className="agent-note agent-note-danger">{t("agentAllowExecuteHint")}</p> : null}

        <div className="api-actions">
          <button className="primary-action" type="submit" id="agent-run" disabled={busy}>
            {busy ? t("agentRunning") : t("agentRun")}
          </button>
        </div>
      </form>

      <p className="api-summary" id="agent-summary" data-state={failure || result?.status === "error" ? "error" : "ok"}>
        {failure ||
          (result
            ? `[${result.status}] ${t("agentToolCalls")}: ${result.tool_calls ?? 0} · ${t("agentRefusals")}: ${
                refusals.join(", ") || t("agentNoRefusals")
              }${result.error ? ` · ${result.error}` : ""}`
            : t("agentHint"))}
      </p>

      {result?.answer ? (
        <div className="agent-answer" id="agent-answer">
          <strong>{t("agentAnswer")}</strong>
          <p>{result.answer}</p>
        </div>
      ) : null}

      {calls.length ? (
        <div className="agent-calls" id="agent-calls">
          {calls.map((call, index) => (
            <article className="agent-call" data-status={call.status} key={`${call.name}-${index}`}>
              <div className="agent-call-top">
                <code>{call.name}</code>
                <span className="agent-call-status">{call.status}</span>
              </div>
              {call.content ? <p>{call.content}</p> : null}
            </article>
          ))}
        </div>
      ) : result ? (
        <p className="agent-note">{t("agentCallsNone")}</p>
      ) : null}

      <ToolCatalogPanel t={t} />
    </>
  );
}

function selectedEngineVersion() {
  try {
    const handoff = JSON.parse(localStorage.getItem(HANDOFF_KEY) || "{}") as {
      plan?: {
        production_pipeline?: { stages?: Array<{ id?: string }> };
        godot_plan?: { engine_version?: string };
        unreal_plan?: { engine_version?: string };
      };
    };
    const stages = handoff?.plan?.production_pipeline?.stages || [];
    if (stages.some((stage) => String(stage.id || "").includes("godot"))) {
      return handoff?.plan?.godot_plan?.engine_version || "Godot 4";
    }
    if (stages.some((stage) => String(stage.id || "").includes("unreal"))) {
      return handoff?.plan?.unreal_plan?.engine_version || "UE5";
    }
  } catch {
    return "UE5";
  }
  return "UE5";
}

function McpCard({ service, t }: { service: McpService; t: (key: string, args?: Record<string, unknown>) => string }) {
  const state = service.status === "ready" || service.status === "degraded" ? service.status : "unavailable";
  const detail = service.detail_key ? t(service.detail_key, service.detail_args) : service.detail;
  const nextAction = service.next_action_key ? t(service.next_action_key, service.next_action_args) : service.next_action;
  return (
    <article className="mcp-status-card" data-state={state}>
      <div className="mcp-status-top">
        <div>
          <h4>{service.label}</h4>
          <p>{service.required ? t("mcpRequired") : t("mcpOptional")}</p>
        </div>
        <span className="mcp-state">{state === "ready" ? t("mcpReady") : state === "degraded" ? t("mcpDegraded") : t("mcpUnavailable")}</span>
      </div>
      <div className="mcp-target">
        <span>{t("mcpTarget")}</span>
        <code>{service.target || "-"}</code>
      </div>
      <p>{detail === service.detail_key ? service.detail : detail}</p>
      <p>
        <strong>{t("mcpNextAction")}:</strong> {nextAction === service.next_action_key ? service.next_action : nextAction}
      </p>
    </article>
  );
}
