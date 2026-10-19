import { useCallback, useEffect, useMemo, useState } from "react";
import type { CSSProperties } from "react";
import { AssetLibrary } from "../assets/AssetLibrary";
import { FlowConsole } from "../console/FlowConsole";
import { OrchestrationBoard } from "../orchestration/OrchestrationBoard";
import {
  getMcpStatus
} from "../shared/api";
import { makeTranslator, studioI18n } from "../shared/i18n";
import { useLocaleTheme } from "../shared/localeTheme";
import { selectedEngineVersion } from "../shared/planModel";
import { useJourney } from "../shared/journeyContext";
import { JOURNEY_PANELS, JOURNEY_STATE_KEYS, JOURNEY_STEP_KEYS, type JourneyStepId } from "../shared/productionJourney";
import { Disclosure, JourneyHeader } from "../shared/ui/primitives";
import { ErrorBoundary } from "../shared/ui/ErrorBoundary";
import { STUDIO_SIDEBAR_COLLAPSED_KEY, STUDIO_SIDEBAR_WIDTH_KEY, readHandoffPlan } from "../shared/storage";
import type {
  McpStatus
} from "../shared/types";
import { PlanningWorkbench } from "../workbench/PlanningWorkbench";
import { AgentPanel } from "./settings/AgentPanel";
import { ApiSettingsPanel } from "./settings/ApiSettingsPanel";
import { McpServiceGrid } from "./settings/McpCard";
import "../styles/studio.css";

type PanelKey = "workbench" | "pipeline" | "console" | "assets" | "mcp" | "api" | "agent";

const panels: Record<PanelKey, { titleKey: string; icon: string }> = {
  workbench: { titleKey: "workbench", icon: "PL" },
  pipeline: { titleKey: "pipeline", icon: "OR" },
  console: { titleKey: "console", icon: "FC" },
  assets: { titleKey: "assets", icon: "AS" },
  mcp: { titleKey: "mcp", icon: "MC" },
  api: { titleKey: "api", icon: "AI" },
  agent: { titleKey: "agent", icon: "AG" }
};

/** The panels that are whole views, so they get their own URL. */
const PANEL_ROUTES: Partial<Record<PanelKey, string>> = {
  workbench: "/workbench",
  pipeline: "/pipeline",
  console: "/web-console",
  assets: "/assets"
};

const DEFAULT_PANEL: PanelKey = "workbench";
const JOURNEY_STEPS: JourneyStepId[] = ["idea", "plan", "orchestrate", "execute", "review", "qa"];
const SETTING_NAV: PanelKey[] = ["mcp", "api", "agent"];



function basePath(): string {
  return import.meta.env.BASE_URL.replace(/\/$/, "");
}

/**
 * The panel a pathname selects.
 *
 * This used to live in `main.tsx`, which rendered a different root component per
 * path: `/workbench` got a bare `PlanningWorkbench`, `/web-console` a bare
 * `FlowConsole`, everything else the shell with those two inside iframes. Two
 * chromes for the same view, and the shell's copy of the path was decided by
 * `src=` attributes. One root component now reads the path once.
 */
function panelFromPathname(): PanelKey {
  const base = basePath();
  const pathname = window.location.pathname;
  const route = base && base !== "/" && pathname.startsWith(base) ? pathname.slice(base.length) || "/" : pathname;

  if (route.startsWith("/web-console")) return "console";
  if (route.startsWith("/pipeline")) return "pipeline";
  // The asset library is its own view, like the console and the board, and
  // not a settings panel: it is somewhere you go to work with assets, not a
  // preference you set once.
  if (route.startsWith("/assets")) return "assets";
  return DEFAULT_PANEL;
}

/**
 * The URL for a panel that has one.
 *
 * Two hosts serve these routes and they do not agree on the prefix. In
 * production FastAPI serves `/web-console` and `/workbench` at the root and only
 * the *assets* live under `BASE_URL`; in the dev server Vite serves the whole app
 * under `BASE_URL`, so the route has to carry it. Pushing the base-prefixed path
 * in production would send the next reload into a 404.
 *
 * `dev` and `base` are parameters rather than closed-over values so that the
 * production branch is reachable from a test. `import.meta.env.DEV` is
 * substituted at build time, so it is `true` in every test environment and the
 * branch it guards cannot be taken through the module's own import -- which is
 * exactly how a base-prefixed path shipped unnoticed until it was traced by
 * hand.
 */
export function panelHref(
  panel: PanelKey,
  dev: boolean = import.meta.env.DEV,
  base: string = basePath()
): string | null {
  const route = PANEL_ROUTES[panel];
  if (!route) return null;

  return dev && base ? `${base}${route}` : route;
}

export function StudioShell() {
  // Locale and theme come from the single provider. The shell used to own its own
  // copy and write the document element itself, which was fine while the views
  // lived in iframes -- three documents, three <html>. They are inline now.
  const { locale, theme, setLocale, setTheme } = useLocaleTheme();
  const { snapshot, update } = useJourney();
  const [activePanel, setActivePanel] = useState<PanelKey>(panelFromPathname);
  // Mounted on first visit, then kept mounted and hidden with CSS.
  //
  // The console polls the execute-status endpoint while a job is in flight and
  // holds the planning conversation in component state, so unmounting it on a
  // panel switch would abandon a running job's progress tracking. Today the
  // iframe stayed mounted forever and the question never came up; the difference
  // after this change is that the second view is no longer fetched until it is
  // first opened.
  //
  // The route is named rather than spelled out on purpose: the endpoint-coverage
  // guard reads any api-path literal in a non-test source -- comment included --
  // as a call site, because prose and code look the same to a regex. This comment
  // used to carry the path, and the guard went red for an endpoint that does not
  // exist. Writing the pattern here to explain that only repeats the mistake.
  const [visitedPanels, setVisitedPanels] = useState<PanelKey[]>(() => [panelFromPathname()]);
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
    update({ plan: readHandoffPlan() });
  }, [update]);

  useEffect(() => {
    document.title = t("documentTitle");
  }, [t]);

  useEffect(() => {
    setVisitedPanels((visited) => (visited.includes(activePanel) ? visited : [...visited, activePanel]));
  }, [activePanel]);

  // Back/forward move between the panels that have a route of their own.
  useEffect(() => {
    const syncFromHistory = () => setActivePanel(panelFromPathname());
    window.addEventListener("popstate", syncFromHistory);
    return () => window.removeEventListener("popstate", syncFromHistory);
  }, []);

  const [consoleFocus, setConsoleFocus] = useState<"review" | "specs">("review");
  const [reviewStage, setReviewStage] = useState("");
  const [chosenJourneyStep, setChosenJourneyStep] = useState<JourneyStepId | null>(null);
  const selectPanel = useCallback((next: PanelKey, step?: JourneyStepId) => {
    if (step) setChosenJourneyStep(step);
    if (step === "review") setConsoleFocus("review");
    if (step === "qa") setConsoleFocus("specs");
    setActivePanel(next);
    const href = panelHref(next);
    if (href && window.location.pathname !== href) {
      window.history.pushState({ panel: next }, "", href);
    }
  }, []);

  const viewedJourneyStep = useMemo(() => {
    if (chosenJourneyStep && JOURNEY_PANELS[chosenJourneyStep] === activePanel) return chosenJourneyStep;
    if (JOURNEY_PANELS[snapshot.currentStep] === activePanel) return snapshot.currentStep;
    const stepsOnPanel = JOURNEY_STEPS.filter((step) => JOURNEY_PANELS[step] === activePanel);
    return stepsOnPanel.length === 1 ? stepsOnPanel[0] : null;
  }, [activePanel, chosenJourneyStep, snapshot.currentStep]);

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
      setMcpStatus(await getMcpStatus(handedOffEngineVersion()));
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

  return (
    <main
      className={`studio-shell ${sidebarCollapsed ? "sidebar-collapsed" : ""}`}
      style={{ "--sidebar-width": `${sidebarWidth}px` } as CSSProperties}
    >
      <aside className="studio-sidebar">
        <header className="studio-sidebar-header">
          <div className="brand-mark" aria-hidden="true">灵</div>
          <div className="brand">
            <p>{t("productLabel")}</p>
            <h1>{t("brandName")}</h1>
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

        <details className="journey-nav" open>
          <summary>{t("journeyLabel")}</summary>
          <nav className="studio-nav" aria-label={t("journeyLabel")}>
            {JOURNEY_STEPS.map((step, index) => {
              const panel = JOURNEY_PANELS[step];
              const stepState = snapshot.steps.find((item) => item.id === step)?.state ?? "upcoming";
              return (
                <button className={viewedJourneyStep === step ? "active" : ""} type="button" data-target={panel} data-journey={step} aria-current={snapshot.currentStep === step ? "step" : undefined} data-state={stepState} key={step} onClick={() => selectPanel(panel, step)}>
                  <span className="nav-index" aria-hidden="true">{index + 1}</span>
                  <span className="nav-copy">
                    <span className="nav-label">{t(JOURNEY_STEP_KEYS[step])}</span>
                    <span className="nav-state">{t(JOURNEY_STATE_KEYS[stepState])}</span>
                  </span>
                </button>
              );
            })}
          </nav>
        </details>
        <Disclosure className="settings-nav" title={t("journeySettings")}>
          {SETTING_NAV.map((key) => (
            <button className={activePanel === key ? "active" : ""} type="button" data-target={key} key={key} onClick={() => selectPanel(key)}>
              <span className="nav-label">{t(panels[key].titleKey)}</span>
            </button>
          ))}
        </Disclosure>

        {/* Assets get their own group rather than a journey step or a
            settings slot: the six steps are the production journey and asset
            management is not one of them, and it is not a preference you set
            once either. One entry, so it reads as a destination. */}
        <Disclosure className="assets-nav" title={t("assetsNavLabel")}>
          <button className={activePanel === "assets" ? "active" : ""} type="button" data-target="assets" onClick={() => selectPanel("assets")}>
            <span className="nav-label">{t("assets")}</span>
          </button>
        </Disclosure>

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
          <JourneyHeader snapshot={snapshot} t={t} />
        </header>

        <section className="studio-panel-frame">
          {/* One boundary per frame: a panel that throws during render used to
              take the whole tree with it, and these frames stay mounted for the
              session, so the crash would have been permanent. The section stays
              outside the boundary -- it owns the data-panel attribute and the
              `active` class the visibility rules read. */}
          {visitedPanels.includes("workbench") && (
            <section
              className={`studio-frame ${activePanel === "workbench" ? "active" : ""}`}
              data-frame="workbench"
              data-panel="workbench"
              aria-hidden={activePanel !== "workbench"}
            >
              <ErrorBoundary t={t}>
                <PlanningWorkbench />
              </ErrorBoundary>
            </section>
          )}
          {visitedPanels.includes("pipeline") && (
            <section
              className={`studio-frame ${activePanel === "pipeline" ? "active" : ""}`}
              data-frame="pipeline"
              data-panel="pipeline"
              aria-hidden={activePanel !== "pipeline"}
            >
              <ErrorBoundary t={t}>
                <OrchestrationBoard
                  active={activePanel === "pipeline"}
                  locale={locale}
                  t={t}
                  onOpenConsole={(stageId) => { setReviewStage(stageId || ""); selectPanel("console", "review"); }}
                />
              </ErrorBoundary>
            </section>
          )}
          {visitedPanels.includes("console") && (
            <section
              className={`studio-frame ${activePanel === "console" ? "active" : ""}`}
              data-frame="console"
              data-panel="console"
              aria-hidden={activePanel !== "console"}
            >
              <ErrorBoundary t={t}>
                <FlowConsole active={activePanel === "console"} focus={consoleFocus} reviewStage={reviewStage} />
              </ErrorBoundary>
            </section>
          )}
          {visitedPanels.includes("assets") && (
            <section
              className={`studio-frame ${activePanel === "assets" ? "active" : ""}`}
              data-frame="assets"
              data-panel="assets"
              aria-hidden={activePanel !== "assets"}
            >
              <ErrorBoundary t={t}>
                <AssetLibrary t={t} />
              </ErrorBoundary>
            </section>
          )}
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
                  ? `${t("mcpSelectedEngine")}: ${mcpStatus.engine || handedOffEngineVersion()} - ${mcpStatus.required_ready ?? 0}/${mcpStatus.required_total ?? 0} ${t("mcpStatusSummary")}`
                  : t("mcpChecking")}
            </p>
            {/* The grid, not the section: the header and the summary above are
                the shell's own chrome and cannot throw, and the refresh button
                is the panel's recovery, so it stays outside the boundary. The
                fallback lands full-width where the grid was, which is also
                where this panel already puts its fetch error.

                The list is a component rather than a `.map()` here on purpose:
                an error boundary catches its descendants' renders, never the
                render of the component that mounts it, so a map written in this
                function body would put the panel's crash surface above every
                boundary in the tree. See `McpServiceGrid`. */}
            <ErrorBoundary t={t}>
              <div className="mcp-status-grid" id="mcp-status-grid">
                {mcpError ? (
                  <article className="mcp-status-card mcp-status-error" data-state="unavailable">
                    <p>{t("mcpCheckFailed")}: {mcpError}</p>
                  </article>
                ) : (
                  <McpServiceGrid services={mcpStatus?.services} t={t} />
                )}
              </div>
            </ErrorBoundary>
          </section>
          {/* The one settings panel that has to wait for a first visit.
              `ApiSettingsPanel` reads the stored settings in its own mount
              effect, so mounting it with the shell spent that request on every
              page load for a panel nobody opened -- the trade
              `ToolCatalogPanel` already refuses to make for its catalog. Same
              rule as the three views above, and for the same reason: mount on
              first visit, then stay mounted, so switching away and back does
              not re-read.

              The other two settings panels need no such gate. The agent panel
              has no mount effect of its own, and the tool status is already
              fetched only once the mcp panel is the active one. */}
          {visitedPanels.includes("api") && (
            <section className={`api-panel ${activePanel === "api" ? "active" : ""}`} data-panel="api">
              <ErrorBoundary t={t}>
                <ApiSettingsPanel t={t} />
              </ErrorBoundary>
            </section>
          )}
          <section className={`agent-panel ${activePanel === "agent" ? "active" : ""}`} data-panel="agent">
            <ErrorBoundary t={t}>
              <AgentPanel t={t} />
            </ErrorBoundary>
          </section>
        </section>
      </section>
    </main>
  );
}

function panelEndpoint(panel: PanelKey) {
  if (panel === "mcp") return "/api/tool-status";
  if (panel === "console") return "/web-console";
  if (panel === "pipeline") return "/api/orchestration/run";
  if (panel === "assets") return "/api/assets";
  if (panel === "api") return "/api/settings/llm";
  if (panel === "agent") return "/api/agent/run";
  return "/workbench";
}

/**
 * The engine version of the plan the workbench handed over.
 *
 * This used to be a second implementation here -- `JSON.parse` straight out of
 * `localStorage`, then a substring match on stage ids. `shared/planModel.ts`
 * already answered the same question from a plan, so there were two truths, and
 * the copy here was the looser one: `id.includes("godot")` against a planModel
 * check for the exact stage id. The contract makes them equivalent
 * (`ProductionPipelineStage.id` is an 8-member `Literal`, and the only member
 * containing "godot" is `godot_quick_play`), so folding them into one is a
 * behaviour-preserving simplification rather than a behaviour change -- and it
 * drops a decoder that answered "UE5" to both "no handoff" and "corrupt handoff".
 */
function handedOffEngineVersion(): string {
  return selectedEngineVersion(readHandoffPlan());
}

