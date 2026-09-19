import { useCallback, useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";
import {
  openManualCorrectionTarget as openManualCorrectionTargetApi,
  previewAssetExecution,
  previewExecute,
  startAssetExecution,
  startExecute,
  getSessionState
} from "../shared/api";
import { consoleI18n, makeTranslator } from "../shared/i18n";
import { useLocaleTheme } from "../shared/localeTheme";
import type {
  CorrectionMode,
  EnemyPressureTuning,
  ExecuteResult,
  ExecuteStage,
  Locale,
  ManualCorrectionTarget,
  SessionState,
  StatusState,
  Theme
} from "../shared/types";
import {
  GateItem,
  ReviewPanel,
  SpecBundlePanel,
  SpecRegenPanel,
  selectedEngineVersion,
  statusLabel,
  usesGodotEngine
} from "./rendering";
import {
  useActivityLog,
  useApprovalManifest,
  useAssetJobPolling,
  useDemoJobPolling,
  useEnemyTuning,
  useManualTargets,
  usePlanningHandoff,
  useSpecPreview,
  useSpecRegen
} from "./hooks";
import "../styles/console.css";

const correctionModeKeys: Record<CorrectionMode, string> = {
  gameplay: "modeGameplay",
  visuals: "modeVisuals",
  scope: "modeScope",
  import: "modeImport"
};

const correctionModeManualTargets: Record<CorrectionMode, string> = {
  gameplay: "planning",
  visuals: "comfyui",
  scope: "planning",
  import: "engine"
};

const manualTargetKeys: Record<string, { label: string; detail: string }> = {
  planning: { label: "manualTargetPlanning", detail: "manualPlanningDetail" },
  comfyui: { label: "manualTargetComfyui", detail: "manualComfyMissing" },
  blender: { label: "manualTargetBlender", detail: "manualBlenderMissing" },
  unreal: { label: "manualTargetUnreal", detail: "manualUnrealMissing" },
  godot: { label: "manualTargetGodot", detail: "manualGodotMissing" },
  generated: { label: "manualTargetGenerated", detail: "manualGeneratedDetail" }
};

type TabKey = "review" | "specs";

// The console keeps only what the workbench does not have: asset review (which
// owns the approval manifest) and the production spec bundle. The other panels
// used to be duplicated here -- overview / tasks / build / visuals / gdd / dsl --
// as second copies of the shared implementations in `shared/panels/PlanPanels.tsx`.
// Those duplicates are gone: the workbench is the single place to read a plan,
// and the console is the place to act on it. The shared implementations were
// left untouched; only this entry point was removed.
const tabGroups: Array<{ labelKey: string; tabs: Array<[TabKey, string]> }> = [
  {
    labelKey: "tabGroupAssets",
    tabs: [
      ["review", "tabReview"],
      ["specs", "tabSpecs"]
    ]
  }
];

/**
 * `active` defaults to true so the console behaves as it always did when it is
 * rendered on its own -- which is how the component tests mount it. The shell
 * passes the real value: a view it keeps mounted after the operator switches
 * away is no longer the view a fresh handoff is addressed to.
 */
export function FlowConsole({ active = true }: { active?: boolean } = {}) {
  // Locale and theme are the provider's, not this view's. The console used to
  // own both and write `document.documentElement` itself -- correct while it was
  // its own document, wrong now that it renders inside the shell, where two
  // effects writing the same attribute is a race with no author.
  const { locale, theme, setLocale, setTheme } = useLocaleTheme();
  const [status, setStatus] = useState<StatusState>("idle");
  const [selectedCorrectionMode, setSelectedCorrectionMode] = useState<CorrectionMode>("gameplay");
  const [correctionEntries, setCorrectionEntries] = useState<Array<{ mode: CorrectionMode; notes: string; createdAt: string }>>([]);
  const [correctionNotes, setCorrectionNotes] = useState("");
  const [activeTab, setActiveTab] = useState<TabKey>("review");
  const [withAssets, setWithAssets] = useState(false);
  const [withVisuals, setWithVisuals] = useState(false);
  const [withGameplay, setWithGameplay] = useState(false);
  const [generateEffects, setGenerateEffects] = useState<string[] | null>(null);
  const [generateResult, setGenerateResult] = useState<ExecuteResult | null>(null);
  const [pollJobId, setPollJobId] = useState<string | null>(null);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [sessionState, setSessionState] = useState<SessionState | null>(null);
  const [assetWithAssets, setAssetWithAssets] = useState(true);
  const [assetWithVisuals, setAssetWithVisuals] = useState(true);
  const [assetEffects, setAssetEffects] = useState<string[] | null>(null);
  const [assetResult, setAssetResult] = useState<ExecuteResult | null>(null);
  const [pollAssetJobId, setPollAssetJobId] = useState<string | null>(null);

  const t = useMemo(() => makeTranslator(locale, consoleI18n), [locale]);
  const { activityEntries, addActivity } = useActivityLog();
  const { enemyTuning, setEnemyTuningValue } = useEnemyTuning();
  const {
    currentPlan,
    currentHandoff,
    reviewDecisions,
    setReviewDecisions,
    updateProductionSpecBundle,
    titleForPlan,
    renderHandoffTitle,
    loadPlanningHandoff
  } = usePlanningHandoff({ active, locale, t, addActivity, setStatus });
  const { manualTargetsPayload, loadManualTargets, fallbackManualTargets } = useManualTargets(currentPlan);
  const { specPreview, specPreviewError } = useSpecPreview(currentPlan, activeTab === "specs");
  const { request: specRegenRequest, regenerated, regenerating, regenError, regenerate, clear: clearRegen } =
    useSpecRegen(currentPlan);
  const { approvalManifestPath, onWriteApprovalManifest } = useApprovalManifest({
    currentPlan,
    reviewDecisions,
    setStatus,
    addActivity,
    t,
    onBundleSynced: updateProductionSpecBundle
  });

  const modeLabel = useCallback((mode: CorrectionMode) => t(correctionModeKeys[mode] || "modeGameplay"), [t]);

  const recommendedManualTargetId = useCallback(() => {
    const mapped = correctionModeManualTargets[selectedCorrectionMode] || "planning";
    if (mapped === "engine") return usesGodotEngine(currentPlan) ? "godot" : "unreal";
    return mapped;
  }, [currentPlan, selectedCorrectionMode]);

  const manualTargetLabel = useCallback((target?: ManualCorrectionTarget) => t(manualTargetKeys[target?.id || "planning"]?.label || "manualTargetPlanning"), [t]);

  const manualTargetDetail = useCallback(
    (target?: ManualCorrectionTarget) => {
      const keys = manualTargetKeys[target?.id || "planning"] || manualTargetKeys.planning;
      if (target?.status === "ready" && target.id !== "planning" && target.id !== "generated") {
        const readyKey = `manual${target.id.charAt(0).toUpperCase()}${target.id.slice(1)}Ready`;
        return t(readyKey);
      }
      return target?.detail_key ? t(target.detail_key) : target?.detail || t(keys.detail);
    },
    [t]
  );

  const targets = manualTargetsPayload?.targets?.length ? manualTargetsPayload.targets : fallbackManualTargets();
  const recommendedTarget = targets.find((target) => target.id === recommendedManualTargetId()) || targets[0];
  const enemies = currentPlan?.gameplay_spec?.enemies || [];

  const { cancelling: demoCancelling, cancel: cancelDemoJob } = useDemoJobPolling({
    jobId: pollJobId,
    setJobId: setPollJobId,
    setResult: setGenerateResult,
    setStatus,
    addActivity,
    doneLabel: t("generateDone"),
    failedLabel: t("generateFailed"),
    cancelledLabel: t("generateCancelled"),
    projectDirOnDone: true
  });

  const { cancelling: assetCancelling, cancel: cancelAssetJob } = useAssetJobPolling({
    jobId: pollAssetJobId,
    setJobId: setPollAssetJobId,
    setResult: setAssetResult,
    setStatus,
    addActivity,
    doneLabel: t("assetExecutionDone"),
    failedLabel: t("assetExecutionFailed"),
    cancelledLabel: t("assetExecutionCancelled")
  });

  const recordCorrection = () => {
    const notes = correctionNotes.trim();
    if (!currentPlan) {
      setStatus("error");
      addActivity(t("correctionRequiresPlan"), t("openPlanningHint"));
      return;
    }
    if (!notes) return;
    setCorrectionEntries((entries) => [{ mode: selectedCorrectionMode, notes, createdAt: new Date().toISOString() }, ...entries].slice(0, 12));
    setCorrectionNotes("");
    setStatus("ready");
    addActivity(t("correctionRecorded"), `${modeLabel(selectedCorrectionMode)}: ${notes}`);
  };

  const openManualTarget = async (targetId: string) => {
    if (targetId === "planning") {
      // Opened as a document of its own, so it reads locale and theme from the
      // shared localStorage key -- the same one this window just wrote. It used
      // to carry them across as `?locale=&theme=`, which was the last remaining
      // copy of the parameter-passing protocol the iframes needed.
      window.open("/workbench", "_blank", "noopener");
      addActivity(t("manualOpenStarted"), t("manualTargetPlanning"));
      return;
    }
    const target = targetId === "engine" ? recommendedManualTargetId() : targetId;
    // The backend gate (local_tools.open_manual_correction_target) refuses
    // without this confirmation, and spawning an editor is a real side effect.
    // Ask first instead of passing `true` blindly.
    const label = t(manualTargetKeys[target]?.label || "manualTargetPlanning");
    if (!window.confirm(t("manualOpenConfirm", { target: label }))) {
      addActivity(t("manualOpenCancelled"), target);
      return;
    }
    try {
      const result = await openManualCorrectionTargetApi(target, selectedEngineVersion(currentPlan), true);
      const label = result.detail_key ? t(result.detail_key) : result.detail || result.status || "";
      if (result.status === "started" || result.status === "client_route") {
        addActivity(t("manualOpenStarted"), `${target}: ${result.target || label}`);
      } else {
        addActivity(t("manualOpenBlocked"), `${target}: ${label}`);
      }
    } catch (error) {
      addActivity(t("manualOpenBlocked"), String(error));
    } finally {
      void loadManualTargets();
    }
  };

  const onGenerateClick = async () => {
    if (!currentPlan) {
      addActivity(t("generateRequiresPlan"), t("openPlanningHint"));
      setStatus("error");
      return;
    }
    try {
      const preview = await previewExecute(
        currentPlan,
        usesGodotEngine(currentPlan) ? "godot" : "unreal",
        withAssets,
        withVisuals,
        withGameplay,
        enemyTuning,
        approvalManifestPath || "generated/asset-approval-manifest.yaml"
      );
      setGenerateEffects(preview.planned_side_effects || []);
    } catch (error) {
      setStatus("error");
      addActivity(t("generateFailed"), String(error));
    }
  };

  const startGenerate = async (resumeFrom?: string) => {
    if (!currentPlan) return;
    setGenerateEffects(null);
    setGenerateResult(null);
    setStatus("running");
    addActivity(
      resumeFrom ? t("reworkRunning") : t("generateRunning"),
      resumeFrom ? `${t("reworkFromLabel")}: ${resumeFrom}` : ""
    );
    try {
      // Only a resume reuses the session; a plain run starts a fresh one so
      // node-level rework can never inherit stale artifacts by accident.
      const started = await startExecute(
        currentPlan,
        usesGodotEngine(currentPlan) ? "godot" : "unreal",
        withAssets,
        withVisuals,
        withGameplay,
        enemyTuning,
        approvalManifestPath || "generated/asset-approval-manifest.yaml",
        resumeFrom ? { sessionId: sessionId || undefined, resumeFrom } : {}
      );
      if (started.job_id) {
        setPollJobId(started.job_id);
        if (started.session_id) setSessionId(started.session_id);
      } else {
        setStatus("error");
        addActivity(t("generateFailed"), started.status || "");
      }
    } catch (error) {
      setStatus("error");
      addActivity(t("generateFailed"), String(error));
    }
  };

  // Once a run settles, read back which nodes finished so the operator can
  // re-run one of them instead of the whole chain.
  useEffect(() => {
    if (!sessionId || pollJobId) return;
    let cancelled = false;
    void getSessionState(sessionId, usesGodotEngine(currentPlan) ? "godot" : "unreal")
      .then((state) => {
        if (!cancelled) setSessionState(state);
      })
      .catch(() => {
        if (!cancelled) setSessionState(null);
      });
    return () => {
      cancelled = true;
    };
  }, [currentPlan, pollJobId, sessionId]);

  const onAssetExecutionClick = async () => {
    if (!currentPlan) {
      addActivity(t("generateRequiresPlan"), t("openPlanningHint"));
      setStatus("error");
      return;
    }
    try {
      const preview = await previewAssetExecution(currentPlan, assetWithAssets, assetWithVisuals);
      setAssetEffects(preview.planned_side_effects || []);
    } catch (error) {
      setStatus("error");
      addActivity(t("assetExecutionFailed"), String(error));
    }
  };

  const startAssetWorkers = async () => {
    if (!currentPlan) return;
    setAssetEffects(null);
    setAssetResult(null);
    setStatus("running");
    addActivity(t("assetExecutionRunning"), "");
    try {
      const started = await startAssetExecution(currentPlan, assetWithAssets, assetWithVisuals);
      if (started.job_id) {
        setPollAssetJobId(started.job_id);
      } else {
        setStatus("error");
        addActivity(t("assetExecutionFailed"), started.status || "");
      }
    } catch (error) {
      setStatus("error");
      addActivity(t("assetExecutionFailed"), String(error));
    }
  };

  // Both metrics are computed from what this view holds. The console used to
  // also show `production_pipeline.current_stage` / `next_stage` and a strip of
  // the pipeline's stage rows -- plan-time values, written once when the plan
  // was authored, rendered as if they were run state. The board is the one
  // place that shows a stage's real status now; this view shows what it can
  // actually vouch for.
  const metrics = {
    reviewItems: String(currentPlan?.creative_review?.items?.length || 0),
    blockedTasks: String((currentPlan?.task_breakdown?.tasks || []).filter((task) => task.status === "blocked").length)
  };

  return (
    <main className="shell">
      <header className="top-bar">
        <div className="brand-block">
          <span className="brand-mark" aria-hidden="true">FA</span>
          <div>
            <p className="eyebrow">{t("productLabel")}</p>
            <h1>{t("brandName")}</h1>
          </div>
        </div>
        <div className="plan-headline">
          <div className="plan-headline-text">
            <p className="eyebrow">{t("statusLabel")}</p>
            <h2 id="plan-title">{currentPlan ? titleForPlan(currentPlan) : t("emptyTitle")}</h2>
          </div>
          <div className="status-chip" id="status-chip" data-state={status}>
            {t(status)}
          </div>
        </div>
        <div className="top-controls">
          <SegmentedControl
            label="Interface language"
            value={locale}
            options={[
              ["en", "EN"],
              ["zh-CN", "\u4e2d\u6587"]
            ]}
            onChange={(value) => {
              setLocale(value as Locale);
              addActivity(t("switchedLocale"), value);
            }}
          />
          <SegmentedControl
            label="Theme"
            value={theme}
            options={[
              ["dark", t("themeDark")],
              ["light", t("themeLight")]
            ]}
            onChange={(value) => setTheme(value as Theme)}
            className="theme-switch"
            buttonClassName="theme-option"
          />
        </div>
      </header>

      <section className="workspace" aria-label={t("cockpitLabel")}>
        <aside className="side-rail plan-rail" aria-label="Plan intake and corrections">
          <p className="rail-title">{t("railPlanTitle")}</p>

          <section className="rail-card handoff-panel" aria-label="Planning handoff">
            <div className="pane-section-header">
              <h2>{t("handoffTitle")}</h2>
              <span className="handoff-chip" id="handoff-state">
                {currentHandoff?.plan ? t("handoffLoadedShort") : t("waitingForPlan")}
              </span>
            </div>
            <div id="handoff-summary" className="handoff-summary">
              {currentHandoff?.invalid ? (
                <p>{t("invalidHandoff")}</p>
              ) : currentHandoff?.plan ? (
                <>
                  <strong>{renderHandoffTitle(currentHandoff)}</strong>
                  <div className="handoff-meta">
                    <span>
                      {t("handoffSource")}: {currentHandoff.source || "-"}
                    </span>
                    <span>
                      {t("handoffTime")}: {formatSavedAt(currentHandoff.savedAt, locale)}
                    </span>
                    <span>
                      {t("session")}: {currentHandoff.plan.gameplay_spec?.target_session_minutes || "-"} {t("minutes")}
                    </span>
                  </div>
                </>
              ) : (
                <>
                  <p>{t("handoffEmpty")}</p>
                  <p>{t("openPlanningHint")}</p>
                </>
              )}
            </div>
            <div className="handoff-actions">
              <button className="primary-action" type="button" id="load-handoff-button" onClick={() => loadPlanningHandoff()}>
                {t("loadHandoff")}
              </button>
            </div>
            <p className="handoff-note">{t("handoffHint")}</p>
          </section>

          <section className="rail-card correction-panel" aria-label="Correction queue">
            <div className="pane-section-header">
              <h2>{t("correctionTitle")}</h2>
            </div>
            <div className="mode-grid" role="group" aria-label="Correction mode">
              {(["gameplay", "visuals", "scope", "import"] as CorrectionMode[]).map((mode) => (
                <button
                  className={`mode-option ${selectedCorrectionMode === mode ? "active" : ""}`}
                  type="button"
                  data-correction-mode={mode}
                  key={mode}
                  onClick={() => setSelectedCorrectionMode(mode)}
                >
                  {modeLabel(mode)}
                </button>
              ))}
            </div>
            <label className="field-label" htmlFor="correction-notes">
              {t("correctionNotes")}
            </label>
            <textarea
              id="correction-notes"
              rows={5}
              placeholder={t("correctionPlaceholder")}
              value={correctionNotes}
              onChange={(event) => setCorrectionNotes(event.target.value)}
            />
            <button className="secondary-action" type="button" id="record-correction-button" onClick={recordCorrection}>
              {t("recordCorrection")}
            </button>
          </section>

          <section className="rail-card manual-correction-panel" aria-label="Manual correction tools">
            <div className="pane-section-header">
              <h2>{t("manualCorrectionTitle")}</h2>
            </div>
            <p className="handoff-note">{t("manualCorrectionHint")}</p>
            <div className="manual-summary-row">
              <span id="manual-tool-summary">
                {t("manualRecommended")}: {manualTargetLabel(recommendedTarget)} / {modeLabel(selectedCorrectionMode)}
              </span>
              <button
                className="secondary-action compact-action"
                type="button"
                id="open-recommended-tool-button"
                disabled={!recommendedTarget?.openable}
                onClick={() => void openManualTarget(recommendedTarget?.id || recommendedManualTargetId())}
              >
                {t("manualOpenRecommended")}
              </button>
            </div>
            <div id="manual-tool-grid" className="manual-tool-list">
              {targets.map((target) => (
                <article
                  className="manual-tool-row"
                  data-state={target.status || "unavailable"}
                  data-recommended={target.id === recommendedManualTargetId() ? "true" : undefined}
                  key={target.id}
                >
                  <div className="manual-tool-name">
                    <h3>{manualTargetLabel(target)}</h3>
                    {target.id === recommendedManualTargetId() ? <span className="task-pill ready">{t("manualRecommended")}</span> : null}
                  </div>
                  <div className="manual-tool-side">
                    <span className="task-pill">{manualStatusLabel(target.status, t)}</span>
                    <button className="mini-action" type="button" data-manual-target={target.id} disabled={!target.openable} onClick={() => void openManualTarget(target.id)}>
                      {t("manualOpen")}
                    </button>
                  </div>
                  <p>{manualTargetDetail(target)}</p>
                </article>
              ))}
            </div>
          </section>

          <section className="rail-card operator-strip" aria-label="Execution confirmations">
            <div className="pane-section-header">
              <h2>{t("gatesTitle")}</h2>
            </div>
            <div id="gate-summary" className="gate-stack">
              {currentPlan ? (
                <>
                  {correctionEntries.slice(0, 3).map((entry) => (
                    <GateItem key={entry.createdAt} title={`${t("correctionPending")} · ${modeLabel(entry.mode)}`} detail={entry.notes} />
                  ))}
                  {(currentPlan.task_breakdown?.tasks || []).filter((task) => task.requires_confirmation).slice(0, 6).map((task) => (
                    <GateItem key={task.id} title={task.title || task.id || t("confirmation")} detail={task.side_effects?.join(", ") || task.status || ""} />
                  ))}
                </>
              ) : (
                <>
                  <GateItem title={t("defaultGateVisuals")} detail={t("waitingForPlan")} />
                  <GateItem title={t("defaultGateMeshes")} detail={t("waitingForPlan")} />
                  <GateItem title={t("defaultGateUnreal")} detail={t("waitingForPlan")} />
                </>
              )}
            </div>
          </section>

        </aside>

        <section className="center-pane" aria-label="Plan inspection">
          <section className="insight-row" aria-label="Plan metrics">
            <Metric label={t("reviewItems")} value={metrics.reviewItems} id="metric-review-items" />
            <Metric label={t("blockedTasks")} value={metrics.blockedTasks} id="metric-blocked-tasks" />
          </section>

          <nav className="tabs" aria-label="Plan views">
            {tabGroups.map((group) => (
              <div className="tab-group" key={group.labelKey}>
                <span className="tab-group-label">{t(group.labelKey)}</span>
                <div className="tab-group-buttons">
                  {group.tabs.map(([tab, label]) => (
                    <button className={`tab ${activeTab === tab ? "active" : ""}`} type="button" data-tab={tab} key={tab} onClick={() => setActiveTab(tab)}>
                      {t(label)}
                    </button>
                  ))}
                </div>
              </div>
            ))}
          </nav>

          <section className="content-frame">
            <Panel tab="review" activeTab={activeTab}>
              <ReviewPanel
                review={currentPlan?.creative_review}
                decisions={reviewDecisions}
                setDecision={(assetId, decision) => {
                  setReviewDecisions((decisions) => ({ ...decisions, [assetId]: decision }));
                  addActivity(t("reviewDecision"), `${assetId}: ${statusLabel(decision, t)}`);
                }}
                manifestPath={approvalManifestPath}
                onWriteManifest={() => void onWriteApprovalManifest()}
                t={t}
              />
            </Panel>
            <Panel tab="specs" activeTab={activeTab}>
              <SpecBundlePanel
                bundle={currentPlan?.production_spec_bundle}
                preview={specPreview}
                error={specPreviewError}
                t={t}
              />
              {currentPlan?.production_spec_bundle ? (
                <SpecRegenPanel
                  request={specRegenRequest}
                  regenerated={regenerated}
                  regenerating={regenerating}
                  error={regenError}
                  baseline={currentPlan?.gameplay_spec}
                  onRegenerate={() => void regenerate()}
                  onClear={clearRegen}
                  t={t}
                />
              ) : null}
            </Panel>
          </section>

        </section>

        <aside className="side-rail run-rail" aria-label="Execution center">
          <p className="rail-title">{t("railRunTitle")}</p>

          <section className="rail-card generate-panel" aria-label="Run approved asset workers">
            <div className="pane-section-header">
              <h2>{t("assetExecutionTitle")}</h2>
            </div>
            <p className="handoff-note">{t("assetExecutionHint")}</p>
            <div className="generate-options">
              <label>
                <input type="checkbox" id="asset-with-assets" checked={assetWithAssets} onChange={(event) => setAssetWithAssets(event.target.checked)} /> <span>{t("generateWithAssets")}</span>
              </label>
              <label>
                <input type="checkbox" id="asset-with-visuals" checked={assetWithVisuals} onChange={(event) => setAssetWithVisuals(event.target.checked)} /> <span>{t("generateWithVisuals")}</span>
              </label>
            </div>
            <button className="secondary-action" type="button" id="asset-execute-button" disabled={status === "running"} onClick={() => void onAssetExecutionClick()}>
              {t("assetExecutionButton")}
            </button>
            {pollAssetJobId ? (
              <button className="secondary-action" type="button" id="asset-execute-stop" disabled={assetCancelling} onClick={() => void cancelAssetJob()}>
                {assetCancelling ? t("stoppingJob") : t("stopJob")}
              </button>
            ) : null}
            {assetEffects ? (
              <div id="asset-execute-confirm" className="generate-confirm">
                <strong>{t("generateConfirmTitle")}</strong>
                <p>{t("generateConfirmIntro")}</p>
                <ul>{assetEffects.map((effect) => <li key={effect}>{effect}</li>)}</ul>
                <div className="handoff-actions">
                  <button className="primary-action" type="button" id="asset-execute-proceed" onClick={() => void startAssetWorkers()}>
                    {t("generateConfirmProceed")}
                  </button>
                  <button className="ghost-action" type="button" id="asset-execute-cancel" onClick={() => setAssetEffects(null)}>
                    {t("generateConfirmCancel")}
                  </button>
                </div>
              </div>
            ) : null}
            <div id="asset-execute-stages" className="generate-stages">
              {assetResult?.stages?.map((stage) => <ExecutionStageCard key={stage.name} stage={stage} t={t} />)}
            </div>
          </section>

          <section className="rail-card generate-panel" aria-label="Generate playable demo">
            <div className="pane-section-header">
              <h2>{t("generateTitle")}</h2>
            </div>
            <p className="handoff-note">{t("generateHint")}</p>
            <div className="generate-options">
              <label>
                <input type="checkbox" id="generate-with-assets" checked={withAssets} onChange={(event) => setWithAssets(event.target.checked)} /> <span>{t("generateWithAssets")}</span>
              </label>
              <label>
                <input type="checkbox" id="generate-with-visuals" checked={withVisuals} onChange={(event) => setWithVisuals(event.target.checked)} /> <span>{t("generateWithVisuals")}</span>
              </label>
              <label>
                <input type="checkbox" id="generate-with-gameplay" checked={withGameplay} onChange={(event) => setWithGameplay(event.target.checked)} /> <span>{t("generateWithGameplay")}</span>
              </label>
            </div>
            {withGameplay ? (
              <div className="enemy-tuning-panel">
                <div>
                  <strong>{t("enemyPressureTitle")}</strong>
                  <p>{t("enemyPressureHint")}</p>
                </div>
                <div className="enemy-roster">
                  {enemies.length ? enemies.map((enemy, index) => (
                    <span className="enemy-chip" key={`${enemy.name || "enemy"}-${index}`}>
                      {enemy.name || t("enemyFallbackName")} / {enemy.behavior || "patrol"} x{enemy.count || 1}
                    </span>
                  )) : <span className="enemy-chip">{t("enemyRosterEmpty")}</span>}
                </div>
                <div className="tuning-grid">
                  {(
                    [
                      ["enemy_count_multiplier", "enemyCountMultiplier", 0, 3],
                      ["move_speed_multiplier", "enemySpeedMultiplier", 0.25, 3],
                      ["detection_radius_multiplier", "enemyDetectionMultiplier", 0.25, 3],
                      ["patrol_radius_multiplier", "enemyPatrolMultiplier", 0.25, 3],
                      ["ranged_interval_multiplier", "enemyRangedIntervalMultiplier", 0.25, 3]
                    ] as Array<[keyof EnemyPressureTuning, string, number, number]>
                  ).map(([key, labelKey, min, max]) => (
                    <label className="tuning-field" key={key}>
                      <span>{t(labelKey)}</span>
                      <input
                        type="number"
                        min={min}
                        max={max}
                        step="0.05"
                        value={enemyTuning[key]}
                        onChange={(event) => setEnemyTuningValue(key, Number(event.target.value))}
                      />
                    </label>
                  ))}
                </div>
              </div>
            ) : null}
            <button className="primary-action" type="button" id="generate-demo-button" disabled={status === "running"} onClick={() => void onGenerateClick()}>
              {t("generateButton")}
            </button>
            {pollJobId ? (
              <button className="secondary-action" type="button" id="generate-stop" disabled={demoCancelling} onClick={() => void cancelDemoJob()}>
                {demoCancelling ? t("stoppingJob") : t("stopJob")}
              </button>
            ) : null}
            {generateEffects ? (
              <div id="generate-confirm" className="generate-confirm">
                <strong>{t("generateConfirmTitle")}</strong>
                <p>{t("generateConfirmIntro")}</p>
                <ul>{generateEffects.map((effect) => <li key={effect}>{effect}</li>)}</ul>
                <div className="handoff-actions">
                  <button className="primary-action" type="button" id="generate-proceed" onClick={() => void startGenerate()}>
                    {t("generateConfirmProceed")}
                  </button>
                  <button className="ghost-action" type="button" id="generate-cancel" onClick={() => setGenerateEffects(null)}>
                    {t("generateConfirmCancel")}
                  </button>
                </div>
              </div>
            ) : null}
            <div id="generate-stages" className="generate-stages">
              {generateResult?.stages?.map((stage) => <ExecutionStageCard key={stage.name} stage={stage} t={t} />)}
              {generateResult?.project_dir ? (
                <p className="handoff-note">
                  {t("generateArtifact")}: <code>{generateResult.project_dir}</code>
                </p>
              ) : null}
            </div>
            {sessionId && sessionState?.found ? (
              <div className="rework-panel" id="rework-panel">
                <div className="pane-section-header">
                  <h3>{t("reworkTitle")}</h3>
                </div>
                <p className="handoff-note">{t("reworkHint")}</p>
                <p className="handoff-note">
                  {t("reworkSession")}: <code>{sessionId}</code>
                </p>
                <ul className="rework-list">
                  {(sessionState?.stages || []).map((stage) => (
                    <li key={stage.name} className={`rework-item rework-${stage.status || "unknown"}`}>
                      <span className="rework-name">{stage.name}</span>
                      <span className="rework-status">{stage.status}</span>
                      <button
                        className="ghost-action"
                        type="button"
                        disabled={status === "running" || !stage.name}
                        onClick={() => void startGenerate(stage.name)}
                      >
                        {t("reworkResume")}
                      </button>
                    </li>
                  ))}
                </ul>
              </div>
            ) : null}
          </section>

          <section className="rail-card activity-card" id="activity-drawer" aria-label="Activity log">
            <div className="activity-head">
              <strong>{t("activityTitle")}</strong>
              <span id="activity-count">{activityEntries.length}</span>
            </div>
            <ol id="activity-log" className="activity-log">
              {activityEntries.map((entry, index) => (
                <li key={`${entry.time}-${index}`}>
                  <span>{entry.time}</span>
                  <div>
                    <strong>{entry.label}</strong>
                    <br />
                    {entry.message}
                  </div>
                </li>
              ))}
            </ol>
          </section>
        </aside>
      </section>
    </main>
  );
}

// Exported so the stage rendering (including the logs list) can be unit tested
// without mounting the whole console.
export function ExecutionStageCard({ stage, t }: { stage: ExecuteStage; t: (key: string) => string }) {
  const metadata = stage.metadata || {};
  const approved = metadata.approved_assets || [];
  const skipped = metadata.skipped_assets || [];
  const revision = metadata.revision_asset_ids || [];
  const rejected = metadata.rejected_asset_ids || [];
  const pending = metadata.pending_asset_ids || [];
  const hasApprovalPreview = stage.name === "approval_gate" && Object.keys(metadata).length > 0;

  return (
    <article className="mcp-status-card" data-state={stage.status === "done" ? "ready" : stage.status === "failed" ? "unavailable" : "degraded"}>
      <div className="mcp-status-top">
        <h4>{stage.name}</h4>
        <span className="mcp-state">{stage.status}</span>
      </div>
      <p>{stage.detail}</p>
      {stage.artifacts?.length ? <code>{stage.artifacts.join(", ")}</code> : null}
      {stage.logs?.length ? (
        <div className="approval-assets">
          <span>{t("stageLogs")}</span>
          <ul>
            {stage.logs.map((line) => (
              <li key={line}>{line}</li>
            ))}
          </ul>
        </div>
      ) : null}
      {hasApprovalPreview ? (
        <div className="approval-preview">
          <div className="approval-summary">
            <span>{t("approvalGateApproved")}: {approved.length}</span>
            <span>{t("approvalGateSkipped")}: {skipped.length}</span>
            <span>{t("approvalGateRevision")}: {revision.length}</span>
            <span>{t("approvalGateRejected")}: {rejected.length}</span>
            <span>{t("approvalGatePending")}: {pending.length}</span>
          </div>
          {metadata.manifest_path ? <p>{t("approvalGateManifest")}: <code>{metadata.manifest_path}</code></p> : null}
          {metadata.report_path ? <p>{t("approvalGateReport")}: <code>{metadata.report_path}</code></p> : null}
          {metadata.blocked_reason ? <p>{t("approvalGateBlockedReason")}: {metadata.blocked_reason}</p> : null}
          {approved.length ? <AssetList title={t("approvalGateApprovedAssets")} items={approved} /> : null}
          {skipped.length ? <AssetList title={t("approvalGateSkippedAssets")} items={skipped} /> : null}
        </div>
      ) : null}
    </article>
  );
}

function AssetList({ title, items }: { title: string; items: string[] }) {
  return (
    <div className="approval-assets">
      <strong>{title}</strong>
      <ul>{items.slice(0, 6).map((item) => <li key={item}>{item}</li>)}</ul>
      {items.length > 6 ? <span>+{items.length - 6}</span> : null}
    </div>
  );
}

function SegmentedControl({
  label,
  value,
  options,
  onChange,
  className = "locale-switch",
  buttonClassName = "locale-option"
}: {
  label: string;
  value: string;
  options: Array<[string, string]>;
  onChange: (value: string) => void;
  className?: string;
  buttonClassName?: string;
}) {
  return (
    <div className={className} aria-label={label}>
      {options.map(([optionValue, optionLabel]) => (
        <button className={`${buttonClassName} ${value === optionValue ? "active" : ""}`} type="button" key={optionValue} onClick={() => onChange(optionValue)}>
          {optionLabel}
        </button>
      ))}
    </div>
  );
}

function formatSavedAt(savedAt: string | null | undefined, locale: Locale) {
  if (!savedAt) return "-";
  const parsed = new Date(savedAt);
  if (Number.isNaN(parsed.getTime())) return savedAt;
  return parsed.toLocaleString(locale, { month: "short", day: "2-digit", hour: "2-digit", minute: "2-digit" });
}

function manualStatusLabel(status: string | undefined, t: (key: string) => string) {
  if (status === "ready") return t("manualStatusReady");
  if (status === "degraded") return t("manualStatusDegraded");
  return t("manualStatusUnavailable");
}

function Metric({ label, value, id }: { label: string; value: string; id: string }) {
  return (
    <div className="metric">
      <span>{label}</span>
      <strong id={id}>{value}</strong>
    </div>
  );
}

function Panel({ tab, activeTab, children }: { tab: TabKey; activeTab: TabKey; children: ReactNode }) {
  return (
    <section className={`panel ${activeTab === tab ? "active" : ""}`} id={`${tab}-panel`} data-panel={tab}>
      {children}
    </section>
  );
}
