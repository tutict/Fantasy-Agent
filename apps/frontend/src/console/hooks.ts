import { useCallback, useEffect, useState } from "react";
import { getAssetExecutionJob, getExecuteJob, getManualCorrectionTargets, previewSpecBundle, writeApprovalManifest } from "../shared/api";
import { HANDOFF_KEY, readPlanningHandoff, savePlanningHandoff } from "../shared/storage";
import type {
  CorrectionMode,
  DirectorBuildPlan,
  EnemyPressureTuning,
  ExecuteResult,
  Locale,
  ManualCorrectionTarget,
  ManualTargetsPayload,
  PlanningHandoff,
  ProductionSpecBundle,
  SpecBundlePreviewResponse,
  StatusState,
  Theme
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
  locale,
  t,
  addActivity,
  setStatus
}: {
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

  useEffect(() => {
    loadPlanningHandoff({ silent: true });
  }, [loadPlanningHandoff]);

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

  const updateProductionSpecBundle = useCallback((bundle: ProductionSpecBundle) => {
    setCurrentPlan((current) =>
      current ? { ...current, production_spec_bundle: bundle } : current
    );
  }, []);

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
  projectDirOnDone,
  fetchJob
}: {
  jobId: string | null;
  setJobId: (jobId: string | null) => void;
  setResult: (result: ExecuteResult | null) => void;
  setStatus: (status: StatusState) => void;
  addActivity: (label: string, message: string) => void;
  doneLabel: string;
  failedLabel: string;
  projectDirOnDone?: boolean;
  fetchJob: (jobId: string) => Promise<{ status?: string; result?: ExecuteResult; error?: string }>;
}) {
  useEffect(() => {
    if (!jobId) return;
    const timer = window.setInterval(async () => {
      try {
        const job = await fetchJob(jobId);
        if (job.result) setResult(job.result);
        if (job.status !== "running") {
          window.clearInterval(timer);
          setJobId(null);
          if (job.status === "done") {
            setStatus("ready");
            addActivity(doneLabel, projectDirOnDone ? job.result?.project_dir || "" : "");
          } else {
            setStatus("error");
            addActivity(failedLabel, job.error || job.status || "");
          }
        }
      } catch (error) {
        setStatus("error");
        addActivity(failedLabel, String(error));
        setJobId(null);
        window.clearInterval(timer);
      }
    }, 1500);
    return () => window.clearInterval(timer);
  }, [addActivity, doneLabel, failedLabel, fetchJob, jobId, projectDirOnDone, setJobId, setResult, setStatus]);
}

export function useDemoJobPolling(args: Omit<Parameters<typeof useExecutionJobPolling>[0], "fetchJob">) {
  useExecutionJobPolling({ ...args, fetchJob: getExecuteJob });
}

export function useAssetJobPolling(args: Omit<Parameters<typeof useExecutionJobPolling>[0], "fetchJob">) {
  useExecutionJobPolling({ ...args, fetchJob: getAssetExecutionJob });
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

export function localizedRoute(path: string, locale: Locale, theme: Theme) {
  const search = new URLSearchParams({ locale, theme });
  return `${path}?${search.toString()}`;
}
