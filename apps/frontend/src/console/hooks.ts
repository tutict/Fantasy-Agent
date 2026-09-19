import { useCallback, useEffect, useState } from "react";
import {
  cancelAssetExecutionJob,
  cancelExecuteJob,
  getAssetExecutionJob,
  getExecuteJob,
  getManualCorrectionTargets,
  previewGameplaySpec,
  previewSpecBundle,
  writeApprovalManifest
} from "../shared/api";
import { HANDOFF_KEY, readPlanningHandoff, savePlanningHandoff } from "../shared/storage";
import type {
  CorrectionMode,
  DirectorBuildPlan,
  EnemyPressureTuning,
  ExecuteResult,
  GameplaySpec,
  Locale,
  ManualCorrectionTarget,
  ManualTargetsPayload,
  PlanningHandoff,
  ProductionSpecBundle,
  PromptRequest,
  SpecBundlePreviewResponse,
  StatusState
} from "../shared/types";
import { preferredTitle, selectedEngineVersion, usesGodotEngine } from "./rendering";

export interface ActivityEntry {
  time: string;
  label: string;
  message: string;
}

export interface CorrectionEntry {
  mode: CorrectionMode;
  notes: string;
  createdAt: string;
}

export const defaultEnemyTuning: EnemyPressureTuning = {
  enemy_count_multiplier: 1.0,
  move_speed_multiplier: 1.0,
  detection_radius_multiplier: 1.0,
  patrol_radius_multiplier: 1.0,
  ranged_interval_multiplier: 1.0
};

export function useActivityLog() {
  const [activityEntries, setActivityEntries] = useState<ActivityEntry[]>([]);

  const addActivity = useCallback((label: string, message: string) => {
    const time = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
    setActivityEntries((entries) => [{ time, label, message }, ...entries].slice(0, 30));
  }, []);

  return { activityEntries, addActivity };
}

export function useEnemyTuning() {
  const [enemyTuning, setEnemyTuning] = useState<EnemyPressureTuning>(defaultEnemyTuning);

  const setEnemyTuningValue = useCallback((key: keyof EnemyPressureTuning, value: number) => {
    setEnemyTuning((current) => ({ ...current, [key]: value }));
  }, []);

  return { enemyTuning, setEnemyTuningValue };
}

export function useSpecPreview(currentPlan: DirectorBuildPlan | null, enabled: boolean) {
  const [specPreview, setSpecPreview] = useState<SpecBundlePreviewResponse | null>(null);
  const [specPreviewError, setSpecPreviewError] = useState<string | null>(null);

  useEffect(() => {
    if (!enabled || !currentPlan?.production_spec_bundle) {
      setSpecPreview(null);
      setSpecPreviewError(null);
      return;
    }
    let active = true;
    void previewSpecBundle(
      currentPlan.production_spec_bundle,
      usesGodotEngine(currentPlan) ? "godot" : "unreal"
    )
      .then((preview) => {
        if (active) {
          setSpecPreview(preview);
          setSpecPreviewError(null);
        }
      })
      .catch((error) => {
        if (active) {
          setSpecPreview(null);
          setSpecPreviewError(String(error));
        }
      });
    return () => {
      active = false;
    };
  }, [currentPlan, enabled]);

  return { specPreview, specPreviewError };
}

/** How the console names the engine to `previewSpecBundle` / `getSessionState`. */
export function specTarget(plan: DirectorBuildPlan | null): "godot" | "unreal" {
  return usesGodotEngine(plan) ? "godot" : "unreal";
}

/**
 * Rebuild the `PromptRequest` a loaded plan came from.
 *
 * **Why this is the best available reconstruction, and not a faithful one.**
 * The prompt text is genuinely not recoverable from the handoff: the workbench
 * extracts an `IdeaSeed`, derives `seed.next_prompt` from it, generates the plan
 * from that, and then persists only the plan. `DirectorBuildPlan` has no prompt
 * field on either side of the REST boundary, and `WriterConfig` has no prompt
 * either -- so there is nothing to read it back from.
 *
 * What *is* recoverable is the scope half every `PromptRequest` carries, all of
 * which is legible from the plan itself:
 *
 *   - `target_minutes` from the spec, which the schema pins to 5-15
 *   - `engine_version` from whichever engine plan the pipeline chose
 *   - `platforms` / `constraints` from the spec's declared asset list
 *   - `source_locale` / `output_locales` from the i18n bundle, which is the one
 *     field that records what the spec was derived *under*
 *
 * The prompt itself falls back to the title plus the logline. That is
 * deliberately **not** the original prompt, so the regenerated spec must be
 * read as "what the backend makes of this plan's headline idea now", never as
 * "what the original prompt produces". The panel says so in the UI, because an
 * operator who mistook this for a re-run of their own prompt would silently
 * compare two unrelated specs.
 */
export function promptRequestFromPlan(plan: DirectorBuildPlan | null): PromptRequest | null {
  const spec = plan?.gameplay_spec;
  if (!spec) return null;
  const godot = usesGodotEngine(plan);
  return {
    prompt: [spec.title, spec.logline].filter(Boolean).join(". ") || spec.player_fantasy || "",
    target_minutes: spec.target_session_minutes,
    engine_version: godot
      ? plan?.godot_plan?.engine_version || "Godot 4"
      : plan?.unreal_plan?.engine_version || "UE5",
    platforms: [inferPlatform(plan)],
    jam_scope: true,
    // The spec does not carry the request's free-form constraints; `asset_needs`
    // is the closest thing the plan records, and it is what the panel shows as
    // the payload it sends.
    constraints: [],
    source_locale: spec.i18n?.source_locale ?? "en",
    output_locales: spec.i18n?.output_locales ?? ["en", "zh-CN"]
  };
}

/**
 * The plan does not record a platform, so read one off the assets it declared.
 *
 * `MOBILE_NEEDLE` is boundary-anchored, and that is load-bearing rather than
 * cosmetic: a bare `ios` substring matches "kiosk" and "prioritization", so a
 * plan whose assets say `asset kiosk prop` would regenerate against `Android`
 * with nothing on screen to explain where that platform came from. The boundary
 * is `[^a-z0-9]` rather than `\b` on purpose -- `\b` would reject the matches
 * that matter (`ios_controls`, `mobile-first`), because `_` and `-` are word
 * characters to `\b` but separators to us. Case-insensitive because the needle
 * list is lowercase while real asset names write `iOS`.
 *
 * There is no `console` needle for the same reason the mobile list needed this
 * guard: `console` matches `console.log`, and a spec whose asset notes mention a
 * debug console would silently regenerate against `Console`. `gamepad` and
 * `controller` have no such embedded collision, so they carry the Console branch
 * on their own.
 */
export const MOBILE_NEEDLE = /(?:^|[^a-z0-9])(?:touch|mobile|android|ios|handheld)(?![a-z0-9])/i;
const CONSOLE_NEEDLE = /(?:^|[^a-z0-9])(?:console|gamepad|controller)(?![a-z0-9])/i;

function inferPlatform(plan: DirectorBuildPlan | null): string {
  const needles = (plan?.gameplay_spec?.asset_needs ?? []).join(" ").toLowerCase();
  if (MOBILE_NEEDLE.test(needles)) return "Android";
  if (CONSOLE_NEEDLE.test(needles)) return "Console";
  return "Windows";
}

/**
 * Preview of the spec the backend would derive from a loaded plan *now*.
 *
 * The console's spec tab shows the spec frozen into the handoff, so a plan built
 * under an older prompt, an older generator, or different LLM settings is
 * indistinguishable from a current one. This is the other half of that
 * comparison -- see `shared/specDiff.ts` for the rows.
 *
 * Nothing is written and no process starts, so there is no approval flag; the
 * deterministic generator makes it repeatable when LLM generation is off.
 */
export function useSpecRegen(plan: DirectorBuildPlan | null) {
  const [regenerated, setRegenerated] = useState<GameplaySpec | null>(null);
  const [regenerating, setRegenerating] = useState(false);
  const [regenError, setRegenError] = useState<string | null>(null);

  const request = promptRequestFromPlan(plan);

  // A new plan invalidates the old comparison: the diff would otherwise show a
  // regenerated spec derived from a plan the console is no longer looking at.
  useEffect(() => {
    setRegenerated(null);
    setRegenError(null);
  }, [plan]);

  const regenerate = useCallback(async () => {
    if (!request) {
      setRegenError(null);
      setRegenerated(null);
      return;
    }
    setRegenerating(true);
    try {
      setRegenerated(await previewGameplaySpec(request));
      setRegenError(null);
    } catch (error) {
      setRegenerated(null);
      setRegenError(String(error));
    } finally {
      setRegenerating(false);
    }
  }, [request]);

  const clear = useCallback(() => {
    setRegenerated(null);
    setRegenError(null);
  }, []);

  return { request, regenerated, regenerating, regenError, regenerate, clear };
}


const fallbackManualTargetDetailKeys: Record<string, string> = {
  planning: "manualPlanningDetail",
  comfyui: "manualComfyMissing",
  blender: "manualBlenderMissing",
  unreal: "manualUnrealMissing",
  godot: "manualGodotMissing",
  generated: "manualGeneratedDetail"
};

export function useManualTargets(currentPlan: DirectorBuildPlan | null) {
  const [manualTargetsPayload, setManualTargetsPayload] = useState<ManualTargetsPayload | null>(null);

  const loadManualTargets = useCallback(async () => {
    try {
      const payload = await getManualCorrectionTargets(selectedEngineVersion(currentPlan));
      setManualTargetsPayload(payload);
    } catch {
      setManualTargetsPayload(null);
    }
  }, [currentPlan]);

  const fallbackManualTargets = useCallback((): ManualCorrectionTarget[] => {
    const engineTarget = usesGodotEngine(currentPlan) ? "godot" : "unreal";
    return ["planning", "comfyui", "blender", engineTarget, "generated"].map((id) => ({
      id: id as ManualCorrectionTarget["id"],
      status: id === "planning" || id === "generated" ? "ready" : "degraded",
      target: id === "planning" ? "/workbench" : "-",
      openable: id === "planning" || id === "generated",
      detail_key: fallbackManualTargetDetailKeys[id]
    }));
  }, [currentPlan]);

  useEffect(() => {
    void loadManualTargets();
  }, [loadManualTargets]);

  return {
    manualTargetsPayload,
    loadManualTargets,
    fallbackManualTargets
  };
}

export function usePlanningHandoff({
  active,
  locale,
  t,
  addActivity,
  setStatus
}: {
  /**
   * Whether the console is the visible view.
   *
   * The handoff used to arrive live: the workbench and the console were
   * separate documents, so a write to the shared localStorage key raised a
   * `storage` event in the other one. They are one document now (F4), and
   * `storage` is only delivered to *other* documents -- so that channel went
   * quiet without anything failing. Re-reading on activation is what replaces
   * it: the shell mounts a view on first visit and keeps it mounted, so a
   * mount-time read alone would show the plan as it was the first time the
   * operator opened this view.
   */
  active: boolean;
  locale: Locale;
  t: (key: string) => string;
  addActivity: (label: string, message: string) => void;
  setStatus: (status: StatusState) => void;
}) {
  const [currentPlan, setCurrentPlan] = useState<DirectorBuildPlan | null>(null);
  const [currentHandoff, setCurrentHandoff] = useState<PlanningHandoff | null>(null);
  const [reviewDecisions, setReviewDecisions] = useState<Record<string, string>>({});

  const titleForPlan = useCallback((plan: DirectorBuildPlan) => preferredTitle(plan, locale, t), [locale, t]);
  const renderHandoffTitle = useCallback(
    (handoff: PlanningHandoff | null) => handoff?.title || titleForPlan(handoff?.plan || {}) || t("emptyTitle"),
    [titleForPlan, t]
  );

  const mergeReviewDefaults = useCallback((plan: DirectorBuildPlan) => {
    setReviewDecisions((decisions) => {
      const next = { ...decisions };
      for (const item of plan.creative_review?.items || []) {
        if (item.asset_id) next[item.asset_id] = next[item.asset_id] || item.approval_status || "";
      }
      return next;
    });
  }, []);

  const acceptHandoff = useCallback(
    (handoff: PlanningHandoff, activityLabel: string) => {
      setCurrentHandoff(handoff);
      if (handoff.plan) {
        setCurrentPlan(handoff.plan);
        mergeReviewDefaults(handoff.plan);
      }
      setStatus("ready");
      addActivity(activityLabel, renderHandoffTitle(handoff));
    },
    [addActivity, mergeReviewDefaults, renderHandoffTitle, setStatus]
  );

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
      mergeReviewDefaults(handoff.plan);
      setStatus("ready");
      if (!options.silent) addActivity(options.activityLabel || t("handoffLoaded"), renderHandoffTitle(handoff));
      return true;
    },
    [addActivity, mergeReviewDefaults, renderHandoffTitle, setStatus, t, titleForPlan]
  );

  // Loaded once on mount (the console only mounts when it is first opened, so
  // it is active by then) and again on every later activation. The silent flag
  // keeps a panel switch from writing an activity line every time.
  useEffect(() => {
    if (active) loadPlanningHandoff({ silent: true });
  }, [active, loadPlanningHandoff]);

  // Still worth keeping for the case it was written for -- a second browser tab
  // -- but it is no longer how a handoff reaches *this* view: within one
  // document `storage` is not delivered to the writer's own document. The
  // activation effect above is what does that now.
  useEffect(() => {
    const onStorage = (event: StorageEvent) => {
      if (event.key === HANDOFF_KEY) loadPlanningHandoff({ activityLabel: t("handoffReceived") });
    };
    const onMessage = (event: MessageEvent) => {
      if (event.origin !== window.location.origin) return;
      const data = event.data as { method?: string; plan?: DirectorBuildPlan; source?: string };
      if (data?.method === "fantasy-agent/planning-handoff" && data.plan?.gameplay_spec) {
        const handoff = savePlanningHandoff(data.plan, preferredTitle(data.plan, locale, t), data.source || "planning-workbench");
        acceptHandoff(handoff, t("handoffReceived"));
      }
    };
    window.addEventListener("storage", onStorage);
    window.addEventListener("message", onMessage);
    return () => {
      window.removeEventListener("storage", onStorage);
      window.removeEventListener("message", onMessage);
    };
  }, [acceptHandoff, loadPlanningHandoff, locale, t]);

  const updateProductionSpecBundle = useCallback(
    (bundle: ProductionSpecBundle) => {
      if (!currentPlan) return;
      const nextPlan = { ...currentPlan, production_spec_bundle: bundle };
      // Persist the synced plan so a reload (or another tab) keeps the
      // approval state the backend already wrote to
      // generated/specs/production-spec-bundle.yaml instead of reverting
      // to the pre-sync handoff.
      const handoff = savePlanningHandoff(
        nextPlan,
        currentHandoff?.title || titleForPlan(nextPlan),
        currentHandoff?.source || "flow-console"
      );
      setCurrentHandoff(handoff);
      setCurrentPlan(nextPlan);
    },
    [currentHandoff, currentPlan, titleForPlan]
  );

  return {
    currentPlan,
    currentHandoff,
    reviewDecisions,
    setReviewDecisions,
    updateProductionSpecBundle,
    titleForPlan,
    renderHandoffTitle,
    loadPlanningHandoff
  };
}

export function useExecutionJobPolling({
  jobId,
  setJobId,
  setResult,
  setStatus,
  addActivity,
  doneLabel,
  failedLabel,
  cancelledLabel,
  projectDirOnDone,
  fetchJob,
  cancelJob
}: {
  jobId: string | null;
  setJobId: (jobId: string | null) => void;
  setResult: (result: ExecuteResult | null) => void;
  setStatus: (status: StatusState) => void;
  addActivity: (label: string, message: string) => void;
  doneLabel: string;
  failedLabel: string;
  cancelledLabel: string;
  projectDirOnDone?: boolean;
  fetchJob: (jobId: string) => Promise<{ status?: string; result?: ExecuteResult; error?: string }>;
  cancelJob?: (jobId: string) => Promise<unknown>;
}) {
  const [cancelling, setCancelling] = useState(false);

  const cancel = useCallback(async () => {
    if (!jobId || !cancelJob) return;
    setCancelling(true);
    try {
      await cancelJob(jobId);
    } catch (error) {
      setCancelling(false);
      addActivity(failedLabel, String(error));
    }
  }, [addActivity, cancelJob, failedLabel, jobId]);

  useEffect(() => {
    if (!jobId) return;
    const timer = window.setInterval(async () => {
      try {
        const job = await fetchJob(jobId);
        if (job.result) setResult(job.result);
        // "cancelling" is transient: keep polling until the worker unwinds.
        if (job.status === "running" || job.status === "cancelling") return;
        window.clearInterval(timer);
        setJobId(null);
        setCancelling(false);
        if (job.status === "done") {
          setStatus("ready");
          addActivity(doneLabel, projectDirOnDone ? job.result?.project_dir || "" : "");
        } else if (job.status === "cancelled") {
          setStatus("idle");
          addActivity(cancelledLabel, job.error || "");
        } else {
          setStatus("error");
          addActivity(failedLabel, job.error || job.status || "");
        }
      } catch (error) {
        setStatus("error");
        addActivity(failedLabel, String(error));
        setJobId(null);
        setCancelling(false);
        window.clearInterval(timer);
      }
    }, 1500);
    return () => window.clearInterval(timer);
  }, [
    addActivity,
    cancelledLabel,
    doneLabel,
    failedLabel,
    fetchJob,
    jobId,
    projectDirOnDone,
    setJobId,
    setResult,
    setStatus
  ]);

  return { cancelling, cancel };
}

export function useDemoJobPolling(args: Omit<Parameters<typeof useExecutionJobPolling>[0], "fetchJob" | "cancelJob">) {
  return useExecutionJobPolling({ ...args, fetchJob: getExecuteJob, cancelJob: cancelExecuteJob });
}

export function useAssetJobPolling(args: Omit<Parameters<typeof useExecutionJobPolling>[0], "fetchJob" | "cancelJob">) {
  return useExecutionJobPolling({ ...args, fetchJob: getAssetExecutionJob, cancelJob: cancelAssetExecutionJob });
}

export function useApprovalManifest({
  currentPlan,
  reviewDecisions,
  setStatus,
  addActivity,
  t,
  onBundleSynced
}: {
  currentPlan: DirectorBuildPlan | null;
  reviewDecisions: Record<string, string>;
  setStatus: (status: StatusState) => void;
  addActivity: (label: string, message: string) => void;
  t: (key: string) => string;
  onBundleSynced: (bundle: ProductionSpecBundle) => void;
}) {
  const [approvalManifestPath, setApprovalManifestPath] = useState("");

  const onWriteApprovalManifest = useCallback(async () => {
    if (!currentPlan?.creative_review) {
      setStatus("error");
      addActivity(t("approvalManifestFailed"), t("noItems"));
      return;
    }
    try {
      const response = await writeApprovalManifest(
        currentPlan.creative_review,
        reviewDecisions,
        currentPlan.production_spec_bundle
      );
      if (response.production_spec_bundle) onBundleSynced(response.production_spec_bundle);
      setApprovalManifestPath(response.manifest_path || "");
      addActivity(t("approvalManifestWritten"), response.manifest_path || "");
    } catch (error) {
      setStatus("error");
      addActivity(t("approvalManifestFailed"), String(error));
    }
  }, [addActivity, currentPlan, onBundleSynced, reviewDecisions, setStatus, t]);

  return { approvalManifestPath, setApprovalManifestPath, onWriteApprovalManifest };
}
