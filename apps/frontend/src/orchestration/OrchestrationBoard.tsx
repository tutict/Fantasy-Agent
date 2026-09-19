/**
 * The orchestration board: the only view that renders `production_pipeline`.
 *
 * Until F3 the pipeline had two renderers -- a stage row in the console and
 * another in the workbench -- and neither was the same: the console showed
 * `risks`, the workbench did not, and neither showed `depends_on`, which is the
 * one field the orchestrator actually gates on. Both are gone; their cards are
 * here, as a card that renders the *runtime* status of a plan rather than a
 * snapshot of it.
 *
 * Where the plan comes from: the handed-off plan in localStorage, which is the
 * same object the flow console executes. That is why the run request carries a
 * plan instead of a prompt -- the cards and the pass have to describe one plan.
 *
 * What is deliberately *not* here:
 *
 *   - **No approve button on a human gate.** `Orchestrator.pending_confirmations`
 *     leaves those out because approving one does not make it run; a button
 *     would be a control that does nothing. The gate card points at the
 *     approval screen in the flow console instead.
 *   - **No approval state of its own.** `confirm_stages` and `rewind_stage` are
 *     built from clicks on this board and travel with the request. Writing
 *     either as a default would take the gate off the backend, which AGENTS.md
 *     is explicit about.
 */

import { useCallback, useEffect, useState } from "react";

import { getOrchestrationState, runOrchestration } from "../shared/api";
import { localizedTitle } from "../shared/planModel";
import {
  readHandoffPlan,
  readOrchestrationSessionId,
  saveOrchestrationSessionId
} from "../shared/storage";
import type { DirectorBuildPlan, Locale, OrchestrationSession } from "../shared/types";
import {
  HUMAN_STAGE_KIND,
  approvableCards,
  boardCards,
  drilldown,
  newSessionId,
  reworkableCards,
  statusLabelKey,
  type BoardCard
} from "./orchestrationModel";
import "../styles/orchestration.css";

type Translator = (key: string, args?: Record<string, unknown>) => string;

export function OrchestrationBoard({
  active,
  locale,
  t,
  onOpenConsole
}: {
  /**
   * Whether this view is the visible one.
   *
   * The shell mounts a view on first visit and then keeps it mounted, so a
   * mount-time read of the handoff would go stale the moment the operator
   * edited the plan in the workbench. The handoff is re-read on activation
   * instead -- the storage event that used to carry it across is only delivered
   * to *other* documents, and there is one document now.
   */
  active: boolean;
  locale: Locale;
  t: Translator;
  onOpenConsole: () => void;
}) {
  const [plan, setPlan] = useState<DirectorBuildPlan | null>(() => readHandoffPlan());
  const [session, setSession] = useState<OrchestrationSession | null>(null);
  const [sessionId] = useState(() => readOrchestrationSessionId() || newSessionId());
  const [translation, setTranslation] = useState<Record<string, string[]>>({});
  const [approved, setApproved] = useState<string[]>([]);
  const [expanded, setExpanded] = useState<string[]>([]);
  const [allowWrite, setAllowWrite] = useState(false);
  const [allowExecute, setAllowExecute] = useState(false);
  const [maxTurns, setMaxTurns] = useState(8);
  const [busy, setBusy] = useState(false);
  const [failure, setFailure] = useState("");

  useEffect(() => {
    if (active) setPlan(readHandoffPlan());
  }, [active]);

  // Adopt whatever this session has already done, and pick up the route's
  // drill-down table. Both come from the same read: a session the server does
  // not know answers `found: false` with the translation still present, which is
  // what lets the board offer the drill-down before its first run.
  useEffect(() => {
    saveOrchestrationSessionId(sessionId);
    let cancelled = false;
    getOrchestrationState(sessionId)
      .then((state) => {
        if (cancelled) return;
        setTranslation(state.stage_translation ?? {});
        // Only adopt a session that ran: `found: false` means the id is new, and
        // `stages` is empty then anyway, but claiming an empty session would
        // hide the plan behind an empty board.
        if (state.found && state.stages?.length) setSession(state);
      })
      .catch(() => {
        // A board with no drill-down and no recovered session is still a board:
        // the cards, the plan and the run button all work without it.
      });
    return () => {
      cancelled = true;
    };
  }, [sessionId]);

  const run = useCallback(
    async (rewindStage: string) => {
      if (!plan?.production_pipeline?.stages?.length) {
        setFailure(t("orchestrationNoPlan"));
        return;
      }
      setBusy(true);
      setFailure("");
      try {
        const payload = await runOrchestration({
          plan,
          session_id: sessionId,
          confirm_stages: approved,
          rewind_stage: rewindStage,
          allow_write: allowWrite,
          allow_execute: allowExecute,
          max_turns: maxTurns
        });
        setSession(payload);
        if (payload.stage_translation) setTranslation(payload.stage_translation);
        // The server recorded these; keeping them ticked would re-send an
        // approval the operator already gave.
        setApproved([]);
        if (payload.status === "error") setFailure(payload.error || t("orchestrationFailed"));
      } catch (error) {
        setFailure(`${t("orchestrationFailed")} ${error}`);
      } finally {
        setBusy(false);
      }
    },
    [allowExecute, allowWrite, approved, maxTurns, plan, sessionId, t]
  );

  const cards = boardCards(plan, session);
  const pending = session?.pending_confirmations ?? [];
  const gates = cards.filter((card) => card.kind === HUMAN_STAGE_KIND);

  const toggle = (list: string[], id: string): string[] =>
    list.includes(id) ? list.filter((entry) => entry !== id) : [...list, id];

  return (
    <div className="or-shell" data-testid="orchestration-board">
      <header className="api-header">
        <div>
          <h3>{t("orchestrationTitle")}</h3>
          <p>{t("orchestrationHint")}</p>
        </div>
      </header>

      <p className="api-summary" data-state={failure ? "error" : "ok"} id="orchestration-summary">
        {failure ||
          (session
            ? `[${session.status}] ${t("orchestrationSession")}: ${session.session_id}${
                session.rewound?.length
                  ? ` · ${t("orchestrationRewound")}: ${session.rewound.join(", ")}`
                  : ""
              }`
            : t("orchestrationNoRunYet"))}
      </p>

      {plan ? (
        <div className="or-plan-meta">
          <span className="or-meta-line">
            {t("orchestrationProject")}: {plan.production_pipeline?.project_name || "-"}
          </span>
          <span className="or-meta-line">
            {t("orchestrationGoal")}: {plan.production_pipeline?.goal || "-"}
          </span>
          <button
            className="or-link"
            type="button"
            id="orchestration-reload"
            onClick={() => {
              setPlan(readHandoffPlan());
              setFailure("");
            }}
          >
            {t("orchestrationReload")}
          </button>
        </div>
      ) : null}

      <form
        className="api-form"
        id="orchestration-form"
        autoComplete="off"
        onSubmit={(event) => {
          event.preventDefault();
          void run("");
        }}
      >
        <div className="api-field">
          <label htmlFor="orchestration-max-turns">{t("orchestrationMaxTurns")}</label>
          <input
            id="orchestration-max-turns"
            type="number"
            min={1}
            max={64}
            step={1}
            value={maxTurns}
            onChange={(event) => setMaxTurns(Number(event.target.value))}
          />
        </div>

        <label className="api-toggle">
          <input
            type="checkbox"
            id="orchestration-allow-write"
            checked={allowWrite}
            onChange={(event) => setAllowWrite(event.target.checked)}
          />
          <span>{t("orchestrationAllowWrite")}</span>
        </label>

        <label className="api-toggle">
          <input
            type="checkbox"
            id="orchestration-allow-execute"
            checked={allowExecute}
            onChange={(event) => setAllowExecute(event.target.checked)}
          />
          <span>{t("orchestrationAllowExecute")}</span>
        </label>

        <div className="api-actions">
          <button
            className="primary-action"
            type="submit"
            id="orchestration-run"
            disabled={busy || !cards.length}
          >
            {busy ? t("orchestrationRunning") : session ? t("orchestrationContinue") : t("orchestrationRun")}
          </button>
        </div>
      </form>

      {pending.length ? (
        <p className="or-pending" id="orchestration-pending" data-count={pending.length}>
          {t("orchestrationPending", { count: pending.length })}: {pending.join(", ")}
        </p>
      ) : null}

      {gates.length ? (
        <section className="or-gates" id="orchestration-gates">
          <h4>{t("orchestrationHumanGates")}</h4>
          {gates.map((gate) => (
            <div className="or-gate" data-gate={gate.id} key={gate.id}>
              <span>{localizedTitle(gate, locale) || gate.id}</span>
              <button className="or-link" type="button" onClick={onOpenConsole}>
                {t("orchestrationOpenApproval")}
              </button>
            </div>
          ))}
        </section>
      ) : null}

      {cards.length ? (
        <div className="or-cards" id="orchestration-cards">
          {cards.map((card) => (
            <StageCard
              key={card.id}
              card={card}
              locale={locale}
              t={t}
              steps={drilldown(card, translation)}
              open={expanded.includes(card.id)}
              onToggleOpen={() => setExpanded((list) => toggle(list, card.id))}
              approved={approved.includes(card.id)}
              onToggleApproved={() => setApproved((list) => toggle(list, card.id))}
              busy={busy}
              onRework={() => void run(card.id)}
              onOpenConsole={onOpenConsole}
            />
          ))}
        </div>
      ) : (
        <p className="or-empty">{t("orchestrationNoPlan")}</p>
      )}
    </div>
  );
}

function StageCard({
  card,
  locale,
  t,
  steps,
  open,
  onToggleOpen,
  approved,
  onToggleApproved,
  busy,
  onRework,
  onOpenConsole
}: {
  card: BoardCard;
  locale: Locale;
  t: Translator;
  steps: string[];
  open: boolean;
  onToggleOpen: () => void;
  approved: boolean;
  onToggleApproved: () => void;
  busy: boolean;
  onRework: () => void;
  onOpenConsole: () => void;
}) {
  const isHuman = card.kind === HUMAN_STAGE_KIND;
  const canApprove = approvableCards([card]).length > 0;
  const canRework = reworkableCards([card]).length > 0;

  return (
    <article className="or-card" data-stage={card.id} data-status={card.status} data-plan-status={card.plan_status}>
      <header className="or-card-head">
        <span className="or-order">{String(card.order).padStart(2, "0")}</span>
        <h3>{localizedTitle(card, locale) || card.id}</h3>
        <span className="or-status" data-status={card.status}>
          {t(statusLabelKey(card.status) || card.status)}
        </span>
        <span className="or-status or-status-plan" data-plan-status={card.plan_status}>
          {t("orchestrationPlanned")}: {t(statusLabelKey(card.plan_status) || card.plan_status)}
        </span>
      </header>

      {card.purpose ? <p className="or-purpose">{card.purpose}</p> : null}

      <div className="or-pills">
        {isHuman ? <span className="or-pill or-pill-human">{t("orchestrationHumanGate")}</span> : null}
        {card.owner_agent ? (
          <span className="or-pill">
            {t("orchestrationOwner")}: {card.owner_agent}
          </span>
        ) : null}
        {card.confirmed ? <span className="or-pill or-pill-ok">{t("orchestrationConfirmed")}</span> : null}
        {card.depends_on.length ? (
          <span className="or-pill">
            {t("orchestrationDependsOn")}: {card.depends_on.join(", ")}
          </span>
        ) : null}
      </div>

      {/*
        A human gate shows the approval route instead of a tool list. It carries
        no `mcp_tools` by contract, so listing them would render an empty row and
        suggest the stage is waiting for a machine.
      */}
      {isHuman ? (
        <p className="or-note">
          {t("orchestrationHumanGateNote")}{" "}
          <button className="or-link" type="button" onClick={onOpenConsole}>
            {t("orchestrationOpenApproval")}
          </button>
        </p>
      ) : (
        <>
          {card.mcp_tools.length ? (
            <p className="or-line">
              {t("orchestrationTools")}: {card.mcp_tools.join(", ")}
            </p>
          ) : null}
          {card.tools.length ? (
            <p className="or-line">
              {t("orchestrationOffered")}: {card.tools.join(", ")}
            </p>
          ) : null}
        </>
      )}

      {card.exit_checks.length || card.checks.length ? (
        <p className="or-line">
          {t("orchestrationExitChecks")}: {(card.checks.length ? card.checks : card.exit_checks).join(", ")}
        </p>
      ) : null}

      {/*
        Both of these were rendered by the panel this card replaced, and by only
        one of the two copies before that: the console's stage row showed
        `risks` and the workbench's did not. Dropping them here would have
        undone the field-coverage work in the one place stages are drawn now.
      */}
      {card.quality_gates.length ? (
        <p className="or-line">
          {t("orchestrationQualityGates")}: {card.quality_gates.join(" / ")}
        </p>
      ) : null}
      {card.risks.length ? (
        <p className="or-line">
          {t("orchestrationRisks")}: {card.risks.join(" / ")}
        </p>
      ) : null}

      {card.detail ? (
        <p className="or-line or-line-detail">
          {t("orchestrationDetail")}: {card.detail}
        </p>
      ) : null}

      {card.tool_calls || card.refusals.length ? (
        <p className="or-line">
          {t("orchestrationToolCalls")}: {card.tool_calls}
          {card.refusals.length ? ` · ${t("orchestrationRefusals")}: ${card.refusals.join(", ")}` : ""}
        </p>
      ) : null}

      {card.answer ? <p className="or-answer">{card.answer}</p> : null}

      <div className="or-actions">
        {canApprove ? (
          <button
            className={`or-button${approved ? " is-on" : ""}`}
            type="button"
            data-approve={card.id}
            aria-pressed={approved}
            disabled={busy}
            onClick={onToggleApproved}
          >
            {approved ? t("orchestrationApproved") : t("orchestrationApprove")}
          </button>
        ) : null}
        {canRework ? (
          <button
            className="or-button"
            type="button"
            data-rework={card.id}
            disabled={busy}
            onClick={onRework}
          >
            {t("orchestrationRework")}
          </button>
        ) : null}
        {!isHuman && steps.length ? (
          <button
            className="or-button"
            type="button"
            data-drilldown={card.id}
            aria-expanded={open}
            onClick={onToggleOpen}
          >
            {open ? t("orchestrationHideSteps") : t("orchestrationShowSteps")}
          </button>
        ) : null}
      </div>

      {open && steps.length ? (
        <ol className="or-steps" data-steps={card.id}>
          {steps.map((step) => (
            <li key={step}>{step}</li>
          ))}
        </ol>
      ) : null}
    </article>
  );
}
