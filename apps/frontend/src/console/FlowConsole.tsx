import { useCallback, useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";
import {
  getAssetExecutionJob,
  getExecuteJob,
  getManualCorrectionTargets,
  openManualCorrectionTarget as openManualCorrectionTargetApi,
  previewAssetExecution,
  previewExecute,
  startAssetExecution,
  startExecute,
  writeApprovalManifest
} from "../shared/api";
import { consoleI18n, makeTranslator } from "../shared/i18n";
import {
  CONSOLE_LOCALE_KEY,
  HANDOFF_KEY,
  THEME_KEY,
  initialLocale,
  initialTheme,
  readPlanningHandoff,
  savePlanningHandoff
} from "../shared/storage";
import type {
  CorrectionMode,
  DirectorBuildPlan,
  EnemyPressureTuning,
  ExecuteResult,
  ExecuteStage,
  Locale,
  ManualCorrectionTarget,
  ManualTargetsPayload,
  PlanningHandoff,
  StatusState,
  Theme
} from "../shared/types";
import {
  BuildPanel,
  GateItem,
  OverviewPanel,
  PipelinePanel,
  QaPanel,
  ReviewPanel,
  TasksPanel,
  VisualsPanel,
  localizedStageTitle,
  preferredTitle,
  selectedEngineVersion,
  statusLabel,
  usesGodotEngine
} from "./rendering";
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

const defaultEnemyTuning: EnemyPressureTuning = {
  enemy_count_multiplier: 1.0,
  move_speed_multiplier: 1.0,
  detection_radius_multiplier: 1.0,
  patrol_radius_multiplier: 1.0,
  ranged_interval_multiplier: 1.0
};

const manualTargetKeys: Record<string, { label: string; detail: string }> = {
  planning: { label: "manualTargetPlanning", detail: "manualPlanningDetail" },
  comfyui: { label: "manualTargetComfyui", detail: "manualComfyMissing" },
  blender: { label: "manualTargetBlender", detail: "manualBlenderMissing" },
  unreal: { label: "manualTargetUnreal", detail: "manualUnrealMissing" },
  godot: { label: "manualTargetGodot", detail: "manualGodotMissing" },
  generated: { label: "manualTargetGenerated", detail: "manualGeneratedDetail" }
};

type TabKey = "overview" | "pipeline" | "tasks" | "review" | "build" | "visuals" | "qa" | "gdd" | "dsl";

interface ActivityEntry {
  time: string;
  label: string;
  message: string;
}

interface CorrectionEntry {
  mode: CorrectionMode;
  notes: string;
  createdAt: string;
}

export function FlowConsole() {
  const [locale, setLocale] = useState<Locale>(() => initialLocale(CONSOLE_LOCALE_KEY));
  const [theme, setTheme] = useState<Theme>(() => initialTheme());
  const [status, setStatus] = useState<StatusState>("idle");
  const [currentPlan, setCurrentPlan] = useState<DirectorBuildPlan | null>(null);
  const [currentHandoff, setCurrentHandoff] = useState<PlanningHandoff | null>(null);
  const [gddLocale, setGddLocale] = useState<Locale>(locale);
  const [selectedCorrectionMode, setSelectedCorrectionMode] = useState<CorrectionMode>("gameplay");
  const [reviewDecisions, setReviewDecisions] = useState<Record<string, string>>({});
  const [correctionEntries, setCorrectionEntries] = useState<CorrectionEntry[]>([]);
  const [activityEntries, setActivityEntries] = useState<ActivityEntry[]>([]);
  const [manualTargetsPayload, setManualTargetsPayload] = useState<ManualTargetsPayload | null>(null);
  const [correctionNotes, setCorrectionNotes] = useState("");
  const [activeTab, setActiveTab] = useState<TabKey>("overview");
  const [logOpen, setLogOpen] = useState(true);
  const [withAssets, setWithAssets] = useState(false);
  const [withVisuals, setWithVisuals] = useState(false);
  const [withGameplay, setWithGameplay] = useState(false);
  const [enemyTuning, setEnemyTuning] = useState<EnemyPressureTuning>(defaultEnemyTuning);
  const [generateEffects, setGenerateEffects] = useState<string[] | null>(null);
  const [generateResult, setGenerateResult] = useState<ExecuteResult | null>(null);
  const [pollJobId, setPollJobId] = useState<string | null>(null);
  const [assetWithAssets, setAssetWithAssets] = useState(true);
  const [assetWithVisuals, setAssetWithVisuals] = useState(true);
  const [assetEffects, setAssetEffects] = useState<string[] | null>(null);
  const [assetResult, setAssetResult] = useState<ExecuteResult | null>(null);
  const [pollAssetJobId, setPollAssetJobId] = useState<string | null>(null);
  const [approvalManifestPath, setApprovalManifestPath] = useState<string>("");

  const t = useMemo(() => makeTranslator(locale, consoleI18n), [locale]);
  const titleForPlan = useCallback((plan: DirectorBuildPlan) => preferredTitle(plan, locale, t), [locale, t]);

  const addActivity = useCallback((label: string, message: string) => {
    const time = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
    setActivityEntries((entries) => [{ time, label, message }, ...entries].slice(0, 30));
  }, []);

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

  const fallbackManualTargets = useCallback((): ManualCorrectionTarget[] => {
    const engineTarget = usesGodotEngine(currentPlan) ? "godot" : "unreal";
    return ["planning", "comfyui", "blender", engineTarget, "generated"].map((id) => ({
      id: id as ManualCorrectionTarget["id"],
      status: id === "planning" || id === "generated" ? "ready" : "degraded",
      target: id === "planning" ? "/workbench" : "-",
      openable: id === "planning" || id === "generated",
      detail_key: manualTargetKeys[id]?.detail
    }));
  }, [currentPlan]);

  const targets = manualTargetsPayload?.targets?.length ? manualTargetsPayload.targets : fallbackManualTargets();
  const recommendedTarget = targets.find((target) => target.id === recommendedManualTargetId()) || targets[0];
  const enemies = currentPlan?.gameplay_spec?.enemies || [];

  const setEnemyTuningValue = useCallback((key: keyof EnemyPressureTuning, value: number) => {
    setEnemyTuning((current) => ({ ...current, [key]: value }));
  }, []);

  const loadManualTargets = useCallback(async () => {
    try {
      const payload = await getManualCorrectionTargets(selectedEngineVersion(currentPlan));
      setManualTargetsPayload(payload);
    } catch {
      setManualTargetsPayload(null);
    }
  }, [currentPlan]);

  const renderHandoffTitle = useCallback((handoff: PlanningHandoff | null) => handoff?.title || titleForPlan(handoff?.plan || {}) || t("emptyTitle"), [titleForPlan, t]);

  const loadPlanningHandoff = useCallback(
    (options: { silent?: boolean; activityLabel?: string } = {}) => {
      const handoff = readPlanningHandoff(titleForPlan);
      setCurrentHandoff(handoff);
      if (!handoff?.plan) {
        if (!options.silent) {
          setStatus("error");
          addActivity(t("handoffEmpty"), t("openPlanningHint"));
        }
        return false;
      }
      setCurrentPlan(handoff.plan);
      setReviewDecisions((decisions) => {
        const next = { ...decisions };
        for (const item of handoff.plan?.creative_review?.items || []) {
          if (item.asset_id) next[item.asset_id] = next[item.asset_id] || item.approval_status || "";
        }
        return next;
      });
      setStatus("ready");
      if (!options.silent) addActivity(options.activityLabel || t("handoffLoaded"), renderHandoffTitle(handoff));
      return true;
    },
    [addActivity, renderHandoffTitle, t, titleForPlan]
  );

  useEffect(() => {
    document.documentElement.lang = locale;
    localStorage.setItem(CONSOLE_LOCALE_KEY, locale);
    setGddLocale(locale);
  }, [locale]);

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    localStorage.setItem(THEME_KEY, theme);
  }, [theme]);

  useEffect(() => {
    loadPlanningHandoff({ silent: true });
  }, [loadPlanningHandoff]);

  useEffect(() => {
    void loadManualTargets();
  }, [loadManualTargets]);

  useEffect(() => {
    const onStorage = (event: StorageEvent) => {
      if (event.key === HANDOFF_KEY) loadPlanningHandoff({ activityLabel: t("handoffReceived") });
    };
    const onMessage = (event: MessageEvent) => {
      if (event.origin !== window.location.origin) return;
      const data = event.data as { method?: string; plan?: DirectorBuildPlan; source?: string };
      if (data?.method === "fantasy-agent/planning-handoff" && data.plan?.gameplay_spec) {
        const handoff = savePlanningHandoff(data.plan, preferredTitle(data.plan, locale, t), data.source || "planning-workbench");
        setCurrentHandoff(handoff);
        setCurrentPlan(data.plan);
        setStatus("ready");
        addActivity(t("handoffReceived"), renderHandoffTitle(handoff));
      }
    };
    window.addEventListener("storage", onStorage);
    window.addEventListener("message", onMessage);
    return () => {
      window.removeEventListener("storage", onStorage);
      window.removeEventListener("message", onMessage);
    };
  }, [addActivity, loadPlanningHandoff, locale, renderHandoffTitle, t]);

  useEffect(() => {
    if (!pollJobId) return;
    const timer = window.setInterval(async () => {
      try {
        const job = await getExecuteJob(pollJobId);
        if (job.result) setGenerateResult(job.result);
        if (job.status !== "running") {
          window.clearInterval(timer);
          setPollJobId(null);
          if (job.status === "done") {
            setStatus("ready");
            addActivity(t("generateDone"), job.result?.project_dir || "");
          } else {
            setStatus("error");
            addActivity(t("generateFailed"), job.error || job.status || "");
          }
        }
      } catch (error) {
        setStatus("error");
        addActivity(t("generateFailed"), String(error));
        setPollJobId(null);
        window.clearInterval(timer);
      }
    }, 1500);
    return () => window.clearInterval(timer);
  }, [addActivity, pollJobId, t]);

  useEffect(() => {
    if (!pollAssetJobId) return;
    const timer = window.setInterval(async () => {
      try {
        const job = await getAssetExecutionJob(pollAssetJobId);
        if (job.result) setAssetResult(job.result);
        if (job.status !== "running") {
          window.clearInterval(timer);
          setPollAssetJobId(null);
          if (job.status === "done") {
            setStatus("ready");
            addActivity(t("assetExecutionDone"), "");
          } else {
            setStatus("error");
            addActivity(t("assetExecutionFailed"), job.error || job.status || "");
          }
        }
      } catch (error) {
        setStatus("error");
        addActivity(t("assetExecutionFailed"), String(error));
        setPollAssetJobId(null);
        window.clearInterval(timer);
      }
    }, 1500);
    return () => window.clearInterval(timer);
  }, [addActivity, pollAssetJobId, t]);

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
      window.open(localizedRoute("/workbench", locale, theme), "_blank", "noopener");
      addActivity(t("manualOpenStarted"), t("manualTargetPlanning"));
      return;
    }
    const target = targetId === "engine" ? recommendedManualTargetId() : targetId;
    try {
      const result = await openManualCorrectionTargetApi(target, selectedEngineVersion(currentPlan));
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

  const startGenerate = async () => {
    if (!currentPlan) return;
    setGenerateEffects(null);
    setGenerateResult(null);
    setStatus("running");
    addActivity(t("generateRunning"), "");
    try {
      const started = await startExecute(
        currentPlan,
        usesGodotEngine(currentPlan) ? "godot" : "unreal",
        withAssets,
        withVisuals,
        withGameplay,
        enemyTuning,
        approvalManifestPath || "generated/asset-approval-manifest.yaml"
      );
      if (started.job_id) {
        setPollJobId(started.job_id);
      } else {
        setStatus("error");
        addActivity(t("generateFailed"), started.status || "");
      }
    } catch (error) {
      setStatus("error");
      addActivity(t("generateFailed"), String(error));
    }
  };

  const onWriteApprovalManifest = async () => {
    if (!currentPlan?.creative_review) {
      setStatus("error");
      addActivity(t("approvalManifestFailed"), t("noItems"));
      return;
    }
    try {
      const response = await writeApprovalManifest(currentPlan.creative_review, reviewDecisions);
      setApprovalManifestPath(response.manifest_path || "");
      addActivity(t("approvalManifestWritten"), response.manifest_path || "");
    } catch (error) {
      setStatus("error");
      addActivity(t("approvalManifestFailed"), String(error));
    }
  };

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

  const metrics = {
    currentStage: currentPlan?.production_pipeline?.current_stage || "-",
    nextStage: currentPlan?.production_pipeline?.next_stage || "-",
    reviewItems: String(currentPlan?.creative_review?.items?.length || 0),
    blockedTasks: String((currentPlan?.task_breakdown?.tasks || []).filter((task) => task.status === "blocked").length)
  };

  const gddDocs = currentPlan?.gdd?.markdown_by_locale || {};
  const gddText = gddDocs[gddLocale] || gddDocs.en || currentPlan?.gdd?.markdown || "";

  return (
    <main className="shell">
      <section className="workspace" aria-label="Fantasy Agent production cockpit">
        <aside className="input-pane">
          <header className="brand-block">
            <div>
              <p className="eyebrow">{t("productLabel")}</p>
              <h1>Fantasy Agent</h1>
            </div>
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
          </header>

          <section className="handoff-panel" aria-label="Planning handoff">
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

          <section className="correction-panel" aria-label="Correction queue">
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

          <section className="manual-correction-panel" aria-label="Manual correction tools">
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
            <div id="manual-tool-grid" className="manual-tool-grid">
              {targets.map((target) => (
                <article className="manual-tool-card" data-state={target.status || "unavailable"} key={target.id}>
                  <div className="manual-tool-top">
                    <h3>{manualTargetLabel(target)}</h3>
                    {target.id === recommendedManualTargetId() ? <span className="task-pill ready">{t("manualRecommended")}</span> : null}
                  </div>
                  <p>{manualTargetDetail(target)}</p>
                  <div className="manual-tool-footer">
                    <span className="task-pill">{manualStatusLabel(target.status, t)}</span>
                    <button className="mini-action" type="button" data-manual-target={target.id} disabled={!target.openable} onClick={() => void openManualTarget(target.id)}>
                      {t("manualOpen")}
                    </button>
                  </div>
                </article>
              ))}
            </div>
          </section>

          <section className="operator-strip" aria-label="Execution confirmations">
            <h2>{t("gatesTitle")}</h2>
            <div id="gate-summary" className="gate-stack">
              {currentPlan ? (
                <>
                  {correctionEntries.slice(0, 3).map((entry) => (
                    <GateItem key={entry.createdAt} title={`${t("correctionPending")} 鐠?${modeLabel(entry.mode)}`} detail={entry.notes} />
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

          <section className="generate-panel" aria-label="Run approved asset workers">
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

          <section className="generate-panel" aria-label="Generate playable demo">
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
          </section>
        </aside>

        <section className="output-pane">
          <header className="status-bar">
            <div>
              <p className="eyebrow">{t("statusLabel")}</p>
              <h2 id="plan-title">{currentPlan ? titleForPlan(currentPlan) : t("emptyTitle")}</h2>
            </div>
            <div className="status-actions">
              <div className="status-chip" id="status-chip" data-state={status}>
                {t(status)}
              </div>
              <button className="ghost-action" id="log-toggle" type="button" onClick={() => setLogOpen((open) => !open)}>
                {t("toggleLog")}
              </button>
            </div>
          </header>

          <section className="stage-strip" aria-label="Production pipeline" id="stage-strip">
            {currentPlan?.production_pipeline?.stages?.length
              ? currentPlan.production_pipeline.stages.map((stage) => (
                  <div className={`stage-node ${stage.status || ""} ${stage.id === currentPlan.production_pipeline?.current_stage ? "is-active" : ""}`} key={stage.id || stage.order}>
                    <span>{String(stage.order ?? "").padStart(2, "0")}</span>
                    <strong>{localizedStageTitle(stage, locale)}</strong>
                  </div>
                ))
              : ["Gameplay", "ComfyUI", "Blender", "Review", "UE", "QA"].map((label, index) => (
                  <div className={`stage-node ${index === 0 ? "is-active" : ""}`} key={label}>
                    <span>{String(index + 1).padStart(2, "0")}</span>
                    <strong>{label}</strong>
                  </div>
                ))}
          </section>

          <section className="insight-row" aria-label="Plan metrics">
            <Metric label={t("currentStage")} value={metrics.currentStage} id="metric-current-stage" />
            <Metric label={t("nextStage")} value={metrics.nextStage} id="metric-next-stage" />
            <Metric label={t("reviewItems")} value={metrics.reviewItems} id="metric-review-items" />
            <Metric label={t("blockedTasks")} value={metrics.blockedTasks} id="metric-blocked-tasks" />
          </section>

          <nav className="tabs" aria-label="Plan views">
            {[
              ["overview", "tabOverview"],
              ["pipeline", "tabPipeline"],
              ["tasks", "tabTasks"],
              ["review", "tabReview"],
              ["build", "tabBuild"],
              ["visuals", "tabVisuals"],
              ["qa", "tabQa"],
              ["gdd", "tabGdd"],
              ["dsl", "tabDsl"]
            ].map(([tab, label]) => (
              <button className={`tab ${activeTab === tab ? "active" : ""}`} type="button" data-tab={tab} key={tab} onClick={() => setActiveTab(tab as TabKey)}>
                {t(label)}
              </button>
            ))}
          </nav>

          <section className="content-frame">
            <Panel tab="overview" activeTab={activeTab}>
              {!currentPlan ? <EmptyState t={t} /> : <OverviewPanel plan={currentPlan} locale={locale} t={t} />}
            </Panel>
            <Panel tab="pipeline" activeTab={activeTab}>
              {currentPlan ? <PipelinePanel plan={currentPlan} locale={locale} t={t} /> : null}
            </Panel>
            <Panel tab="tasks" activeTab={activeTab}>
              {currentPlan ? <TasksPanel breakdown={currentPlan.task_breakdown} locale={locale} t={t} /> : null}
            </Panel>
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
            <Panel tab="build" activeTab={activeTab}>
              {currentPlan ? <BuildPanel plan={currentPlan} t={t} /> : null}
            </Panel>
            <Panel tab="visuals" activeTab={activeTab}>
              {currentPlan ? <VisualsPanel comfy={currentPlan.comfyui_plan} review={currentPlan.creative_review} t={t} /> : null}
            </Panel>
            <Panel tab="qa" activeTab={activeTab}>
              {currentPlan ? <QaPanel qa={currentPlan.qa_plan} t={t} /> : null}
            </Panel>
            <Panel tab="gdd" activeTab={activeTab}>
              <div className="gdd-toolbar">
                {(["en", "zh-CN"] as Locale[]).map((item) => (
                  <button className={`mini-action ${gddLocale === item ? "active" : ""}`} type="button" data-gdd-locale={item} key={item} onClick={() => setGddLocale(item)}>
                    {item === "en" ? "English" : "\u4e2d\u6587"}
                  </button>
                ))}
              </div>
              <pre id="gdd-output" className="code-output">
                {gddText}
              </pre>
            </Panel>
            <Panel tab="dsl" activeTab={activeTab}>
              <pre id="dsl-output" className="code-output">
                {currentPlan?.gameplay_spec ? JSON.stringify(currentPlan.gameplay_spec, null, 2) : ""}
              </pre>
            </Panel>
          </section>

          <aside className={`activity-drawer ${logOpen ? "is-open" : ""}`} id="activity-drawer" aria-label="Activity log">
            <div className="drawer-header">
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
          </aside>
        </section>
      </section>
    </main>
  );
}

function ExecutionStageCard({ stage, t }: { stage: ExecuteStage; t: (key: string) => string }) {
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

function localizedRoute(path: string, locale: Locale, theme: Theme) {
  const search = new URLSearchParams({ locale, theme });
  return `${path}?${search.toString()}`;
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

function EmptyState({ t }: { t: (key: string) => string }) {
  return (
    <div className="empty-state">
      <div className="signal-map" aria-hidden="true">
        <div className="signal-route" />
        <div className="signal-dot dot-a" />
        <div className="signal-dot dot-b" />
        <div className="signal-dot dot-c" />
      </div>
      <h3>{t("emptyHeading")}</h3>
      <p>{t("emptyBody")}</p>
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
