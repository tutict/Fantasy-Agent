/**
 * Planning workbench: interview a game idea, extract an idea seed, then build
 * the production plan panel by panel.
 *
 * This replaces the retired static page
 * `apps/studio/static/planning-workbench.html`. Planning here never writes
 * files or spawns processes -- that stays in the flow console, so unlike the
 * console there is no approval gate to thread through, only the "confirm the
 * idea before generating" rule the old page enforced.
 */

import { useCallback, useEffect, useMemo, useState } from "react";

import { callWorkbenchTool } from "../shared/api";
import { workbenchI18n, makeTranslator } from "../shared/i18n";
import {
  THEME_KEY,
  WORKBENCH_LOCALE_KEY,
  initialLocale,
  initialTheme,
  savePlanningHandoff
} from "../shared/storage";
import type {
  DirectorBuildPlan,
  IdeaSeed,
  InterviewAnswer,
  Locale,
  PromptRequest,
  StatusState,
  Theme,
  WorkbenchConfig,
  WorkbenchPanelKey,
  WorkbenchToolResult
} from "../shared/types";
import { DiscoveryThread, type ThreadEntry } from "./DiscoveryThread";
import {
  BuildPanel,
  DslPanel,
  GddPanel,
  OverviewPanel,
  PANEL_KEYS,
  PipelinePanel,
  QaPanel,
  TasksPanel,
  ToolActions,
  VisualsPanel
} from "./PlanPanels";
import { SeedInspector } from "./SeedInspector";
import "../styles/workbench.css";
import {
  EMPTY_SEED_FIELDS,
  MAX_CHAT_LENGTH,
  MIN_RAW_IDEA_LENGTH,
  appendInterviewAnswer,
  canConfirmSeed,
  canGenerate,
  clampTargetMinutes,
  currentInterviewQuestion,
  defaultConfig,
  ideaDiscoveryPayload,
  interviewQuestions,
  normalizeToolResult,
  planDisplayTitle,
  promptRequestFromEditor,
  requestPayload,
  resultPanel,
  seedFromEditor,
  joinLines,
  type SeedEditorFields
} from "./workbenchModel";

export const EXTRACT_TOOL = "extract_idea_seed";

function isEmbed(): boolean {
  if (typeof window === "undefined") return false;
  return new URLSearchParams(window.location.search).get("embed") === "1";
}

/** Only merge keys the tool actually returned, so one tool cannot blank another's output. */
function mergePlanPatch(
  previous: DirectorBuildPlan | null,
  patch: Partial<DirectorBuildPlan>
): DirectorBuildPlan {
  const next: Record<string, unknown> = { ...(previous ?? {}) };
  for (const [key, value] of Object.entries(patch)) {
    if (value !== undefined && value !== null) next[key] = value;
  }
  return next as unknown as DirectorBuildPlan;
}

export function PlanningWorkbench() {
  const [locale, setLocale] = useState<Locale>(() => initialLocale(WORKBENCH_LOCALE_KEY));
  const [theme, setTheme] = useState<Theme>(() => initialTheme());
  const [status, setStatus] = useState<StatusState>("idle");
  const [error, setError] = useState<string | null>(null);

  const [chatInput, setChatInput] = useState("");
  const [rawIdea, setRawIdea] = useState("");
  const [answers, setAnswers] = useState<InterviewAnswer[]>([]);
  const [seed, setSeed] = useState<IdeaSeed | null>(null);
  const [seedConfirmed, setSeedConfirmed] = useState(false);
  const [plan, setPlan] = useState<DirectorBuildPlan | null>(null);
  const [fields, setFields] = useState<SeedEditorFields>(EMPTY_SEED_FIELDS);
  const [config, setConfig] = useState<WorkbenchConfig>(() => defaultConfig());
  const [activePanel, setActivePanel] = useState<WorkbenchPanelKey>("overview");
  const [running, setRunning] = useState<string | null>(null);

  const t = useMemo(() => makeTranslator(locale, workbenchI18n), [locale]);
  const embedded = useMemo(isEmbed, []);

  useEffect(() => {
    document.documentElement.lang = locale;
    document.documentElement.dataset.theme = theme;
    document.title = t("navPlanning");
    localStorage.setItem(WORKBENCH_LOCALE_KEY, locale);
    localStorage.setItem(THEME_KEY, theme);
  }, [locale, theme, t]);

  const question = currentInterviewQuestion(answers, locale);
  const busy = running !== null;

  /** Rebuild the seed from the editor; the editor is the source of truth once edited. */
  const rebuildSeed = useCallback(
    (nextFields: SeedEditorFields, nextConfig: WorkbenchConfig, previous?: IdeaSeed | null) =>
      seedFromEditor(nextFields, nextConfig, previous ?? seed),
    [seed]
  );

  const syncFieldsFromSeed = useCallback((nextSeed: IdeaSeed | null) => {
    if (!nextSeed) {
      setFields(EMPTY_SEED_FIELDS);
      return;
    }
    setFields({
      rawIdea: nextSeed.raw_idea ?? "",
      playerFantasy: nextSeed.player_fantasy ?? "",
      emotionalTarget: nextSeed.emotional_target ?? "",
      coreAction: nextSeed.core_action ?? "",
      tensionSource: nextSeed.tension_source ?? "",
      mustKeep: joinLines(nextSeed.must_keep),
      canCut: joinLines(nextSeed.can_cut),
      referenceFeel: nextSeed.reference_feel ?? "",
      playableLoop: nextSeed.playable_loop_candidate ?? ""
    });
  }, []);

  const applyPromptRequest = useCallback((payload: PromptRequest | undefined) => {
    if (!payload) return;
    setConfig((previous) => ({
      ...previous,
      targetMinutes: clampTargetMinutes(payload.target_minutes ?? previous.targetMinutes),
      engineVersion: payload.engine_version || previous.engineVersion,
      platform: payload.platforms?.[0] || previous.platform,
      sourceLocale: payload.source_locale ?? previous.sourceLocale,
      constraints: payload.constraints ?? previous.constraints
    }));
  }, []);

  const ingest = useCallback(
    (result: WorkbenchToolResult) => {
      const { structured, meta } = normalizeToolResult(result);

      const nextSeed = structured.idea_seed ?? meta.ideaSeed;
      if (nextSeed) {
        setSeed(nextSeed);
        setSeedConfirmed(false);
        syncFieldsFromSeed(nextSeed);
        applyPromptRequest(structured.prompt_request ?? meta.promptRequest);
      }

      const planPatch: Partial<DirectorBuildPlan> = {};
      const nextPlan = structured.plan ?? meta.plan;
      if (structured.task_breakdown ?? meta.taskBreakdown) {
        planPatch.task_breakdown = (structured.task_breakdown ?? meta.taskBreakdown) as never;
      }
      if (structured.production_pipeline ?? meta.productionPipeline) {
        planPatch.production_pipeline = (
          structured.production_pipeline ?? meta.productionPipeline
        ) as never;
      }
      if (structured.gdd ?? meta.gdd) planPatch.gdd = (structured.gdd ?? meta.gdd) as never;
      if (structured.unreal_plan ?? meta.unrealPlan) {
        planPatch.unreal_plan = (structured.unreal_plan ?? meta.unrealPlan) as never;
      }
      if (structured.godot_plan ?? meta.godotPlan) {
        planPatch.godot_plan = (structured.godot_plan ?? meta.godotPlan) as never;
      }
      if (structured.blender_plan ?? meta.blenderPlan) {
        planPatch.blender_plan = (structured.blender_plan ?? meta.blenderPlan) as never;
      }
      if (structured.comfyui_plan ?? meta.comfyuiPlan) {
        planPatch.comfyui_plan = (structured.comfyui_plan ?? meta.comfyuiPlan) as never;
      }
      if (structured.creative_review ?? meta.creativeReview) {
        planPatch.creative_review = (structured.creative_review ?? meta.creativeReview) as never;
      }
      if (structured.qa_plan ?? meta.qaPlan) {
        planPatch.qa_plan = (structured.qa_plan ?? meta.qaPlan) as never;
      }

      if (nextPlan || Object.keys(planPatch).length) {
        setPlan((previous) => {
          const merged = mergePlanPatch(nextPlan ?? previous, planPatch);
          if (merged.gameplay_spec) {
            savePlanningHandoff(merged, planDisplayTitle(merged, locale), "planning-workbench");
          }
          return merged;
        });
      }

      const panel = resultPanel(meta.toolName ?? "", meta);
      if (panel) setActivePanel(panel as WorkbenchPanelKey);
    },
    [applyPromptRequest, locale, syncFieldsFromSeed]
  );

  const runTool = useCallback(
    async (tool: string, payload: PromptRequest | ReturnType<typeof ideaDiscoveryPayload>) => {
      setRunning(tool);
      setStatus("running");
      setError(null);
      try {
        const result = await callWorkbenchTool(tool, payload);
        ingest(result);
        setStatus("ready");
      } catch (failure) {
        setStatus("error");
        setError(failure instanceof Error ? failure.message : String(failure));
      } finally {
        setRunning(null);
      }
    },
    [ingest]
  );

  const planPayload = useCallback(
    () => requestPayload({ ...fields, rawIdea }, config, seed, seedConfirmed),
    [fields, rawIdea, config, seed, seedConfirmed]
  );

  const submitChatInput = useCallback(() => {
    const text = chatInput.trim();
    if (!text) return;
    if (!rawIdea) {
      setRawIdea(text);
      setSeedConfirmed(false);
    } else {
      setAnswers((previous) => appendInterviewAnswer(previous, question, text, locale));
      setSeedConfirmed(false);
    }
    setChatInput("");
  }, [chatInput, rawIdea, question, locale]);

  const extractSeed = useCallback(() => {
    const text = chatInput.trim();
    const idea = text || rawIdea;
    if (idea.length < MIN_RAW_IDEA_LENGTH) return;
    if (text && !rawIdea) setRawIdea(text);
    const base = planPayload();
    const nextAnswers = text && rawIdea ? appendInterviewAnswer(answers, question, text, locale) : answers;
    if (nextAnswers !== answers) setAnswers(nextAnswers);
    setChatInput("");
    const payload = ideaDiscoveryPayload(base, idea, nextAnswers);
    void runTool(EXTRACT_TOOL, payload);
  }, [answers, chatInput, locale, planPayload, question, rawIdea, runTool]);

  const confirmSeed = useCallback(() => {
    if (!canConfirmSeed(fields)) return;
    const nextSeed = rebuildSeed(fields, config, seed);
    setSeed(nextSeed);
    setSeedConfirmed(true);
    setStatus("ready");
  }, [config, fields, rebuildSeed, seed]);

  const onRunPlanTool = useCallback(
    (tool: string) => {
      if (!canGenerate(seed, seedConfirmed)) return;
      void runTool(tool, planPayload());
    },
    [planPayload, runTool, seed, seedConfirmed]
  );

  const entries: ThreadEntry[] = useMemo(() => {
    const thread: ThreadEntry[] = [{ kind: "ai", title: t("aiName"), body: t("welcome") }];
    if (rawIdea) {
      thread.push({ kind: "user", title: t("userName"), body: rawIdea });
    }
    for (const answer of answers) {
      thread.push({ kind: "ai", title: t("aiName"), body: answer.question });
      thread.push({ kind: "user", title: t("userName"), body: answer.answer });
    }
    if (question) {
      thread.push({
        kind: "ai",
        title: t("aiName"),
        body: t("interviewProgress", {
          current: answers.length + 1,
          total: interviewQuestions(locale).length
        })
      });
      thread.push({ kind: "ai", title: t("aiName"), body: question.text });
    } else if (rawIdea) {
      thread.push({ kind: "ai", title: t("aiName"), body: t("readyToExtract") });
    }
    if (seed) {
      thread.push({ kind: "ai", title: t("aiName"), body: t("seedReadyTitle") });
    }
    if (plan) {
      thread.push({ kind: "ai", title: t("ready"), body: planDisplayTitle(plan, locale) });
    }
    return thread;
  }, [answers, locale, plan, question, rawIdea, seed, t]);

  const panelBody = () => {
    switch (activePanel) {
      case "pipeline":
        return <PipelinePanel plan={plan} t={t} locale={locale} />;
      case "tasks":
        return <TasksPanel plan={plan} t={t} locale={locale} />;
      case "build":
        return <BuildPanel plan={plan} t={t} />;
      case "visuals":
        return <VisualsPanel plan={plan} t={t} />;
      case "gdd":
        return <GddPanel plan={plan} t={t} locale={locale} />;
      case "qa":
        return <QaPanel plan={plan} t={t} />;
      case "dsl":
        return <DslPanel plan={plan} seed={seed} t={t} />;
      default:
        return <OverviewPanel plan={plan} seed={seed} t={t} locale={locale} />;
    }
  };

  return (
    <div className={`wb-shell${embedded ? " embedded" : ""}`} data-testid="planning-workbench">
      <header className="wb-topbar">
        <div className="wb-brand">
          <span className="wb-eyebrow">{t("appEyebrow")}</span>
          <strong>{t("navPlanning")}</strong>
        </div>
        <div className="wb-topbar-actions">
          <span className="wb-chip" data-testid="service-chip">
            {t("localService")}: {t("serviceOnline")}
          </span>
          <span className={`wb-chip ${status}`} data-testid="status-chip">
            {t(status)}
          </span>
          <button
            type="button"
            className={`wb-button ghost${locale === "en" ? " active" : ""}`}
            data-locale="en"
            onClick={() => setLocale("en")}
          >
            EN
          </button>
          <button
            type="button"
            className={`wb-button ghost${locale === "zh-CN" ? " active" : ""}`}
            data-locale="zh-CN"
            onClick={() => setLocale("zh-CN")}
          >
            中文
          </button>
          <button
            type="button"
            className={`wb-button ghost${theme === "dark" ? " active" : ""}`}
            onClick={() => setTheme("dark")}
          >
            {t("themeDark")}
          </button>
          <button
            type="button"
            className={`wb-button ghost${theme === "light" ? " active" : ""}`}
            onClick={() => setTheme("light")}
          >
            {t("themeLight")}
          </button>
        </div>
      </header>

      <div className="wb-grid">
        <div className="wb-column">
          <section className="wb-card" aria-label={t("sessionTitle")}>
            <header className="wb-card-head">
              <div>
                <h2>{t("sessionTitle")}</h2>
                <p>{t("sessionSubtitle")}</p>
              </div>
            </header>
            <DiscoveryThread entries={entries} />
            <div className="wb-composer">
              <textarea
                aria-label={t("chatPlaceholder")}
                placeholder={t("chatPlaceholder")}
                maxLength={MAX_CHAT_LENGTH}
                value={chatInput}
                onChange={(event) => setChatInput(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === "Enter" && !event.shiftKey) {
                    event.preventDefault();
                    submitChatInput();
                  }
                }}
              />
              <button type="button" className="wb-button primary" onClick={submitChatInput}>
                {t("promptLabel")}
              </button>
            </div>
            <div className="wb-card-body">
              <span className="wb-composer-meta">
                <span>{t("enterHint")}</span>
                <span>
                  {chatInput.length} / {MAX_CHAT_LENGTH}
                </span>
              </span>
            </div>
          </section>

          <SeedInspector
            t={t}
            locale={locale}
            fields={fields}
            config={config}
            seedConfirmed={seedConfirmed}
            busy={busy}
            canConfirm={canConfirmSeed(fields)}
            canExtract={Boolean(chatInput.trim() || rawIdea)}
            openQuestions={seed?.open_questions ?? []}
            onFieldChange={(patch) => {
              setFields((previous) => ({ ...previous, ...patch }));
              setSeedConfirmed(false);
            }}
            onConfigChange={(patch) => {
              setConfig((previous) => ({ ...previous, ...patch }));
              setSeedConfirmed(false);
            }}
            onConfirm={confirmSeed}
            onExtract={extractSeed}
          />
        </div>

        <div className="wb-column">
          <ToolActions
            t={t}
            enabled={canGenerate(seed, seedConfirmed)}
            busy={busy}
            running={running}
            onRun={onRunPlanTool}
          />

          <section className="wb-card" aria-label={t("overview")}>
            <header className="wb-card-head">
              <div>
                <h2 data-testid="plan-title">{plan ? planDisplayTitle(plan, locale) : t("emptyTitle")}</h2>
                <p>
                  {t("recommended")}: {plan?.next_actions?.[0] ?? t("noPlan")}
                </p>
              </div>
            </header>
            <nav className="wb-tabs" aria-label={t("overview")}>
              {PANEL_KEYS.map((key) => (
                <button
                  key={key}
                  type="button"
                  className={`wb-tab${activePanel === key ? " active" : ""}`}
                  data-panel-button={key}
                  onClick={() => setActivePanel(key)}
                >
                  {t(key)}
                </button>
              ))}
            </nav>
            <div className="wb-panel" data-panel={activePanel}>
              {error ? <p className="wb-empty">{error}</p> : null}
              {panelBody()}
            </div>
          </section>
        </div>
      </div>
    </div>
  );
}
