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
 *     would be a control that does nothing. What a gate takes is a *decision*,
 *     which is what the two buttons on its card send -- see
 *     `decidableCards`.
 *   - **No approval state of its own.** `confirm_stages` and `rewind_stage` are
 *     built from clicks on this board and travel with the request. Writing
 *     either as a default would take the gate off the backend, which AGENTS.md
 *     is explicit about. The decision rides the same way: it is built from the
 *     click and nothing else.
 */

import { useCallback, useEffect, useState } from "react";
import { useJourney } from "../shared/journeyContext";
import { EmptyState } from "../shared/ui/primitives";

import { decideHumanGate, getOrchestrationState, runOrchestration } from "../shared/api";
import { localizedTitle } from "../shared/planModel";
import {
  readHandoffPlan,
  readOrchestrationEngine,
  readOrchestrationSessionId,
  saveOrchestrationEngine,
  saveOrchestrationSessionId
} from "../shared/storage";
import type { DirectorBuildPlan, Locale, OrchestrationSession } from "../shared/types";
import {
  HUMAN_STAGE_KIND,
  boardCards,
  decidableCards,
  drilldown,
  newSessionId
} from "./orchestrationModel";
import { StageCard } from "./StageCard";
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
  onOpenConsole: (stageId?: string) => void;
}) {
  const { update } = useJourney();
  const [plan, setPlan] = useState<DirectorBuildPlan | null>(() => readHandoffPlan());
  const [session, setSession] = useState<OrchestrationSession | null>(null);
  const [sessionId] = useState(() => readOrchestrationSessionId() || newSessionId());
  // Which engine's snapshot directory this session lives in. Read from storage
  // rather than inferred from `plan`: a restart goes looking for the directory
  // *that session* wrote, and an operator who edited the plan since the run --
  // or a board opened before any handoff exists -- would send us to the wrong
  // one and read `found: false` for a run that is on disk.
  const [engine] = useState(() => readOrchestrationEngine());
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
    getOrchestrationState(sessionId, engine)
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
  }, [engine, sessionId]);

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
        // The server decided which engine it ran under, from the plan it was
        // posted. Recording that is what keeps the next read pointed at the same
        // directory: a board that re-derived it here could disagree with the
        // inference that actually chose where to write.
        if (payload.engine) saveOrchestrationEngine(payload.engine);
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

  const decide = useCallback(
    async (stageId: string, decision: string) => {
      if (!plan?.production_pipeline?.stages?.length) {
        setFailure(t("orchestrationNoPlan"));
        return;
      }
      setBusy(true);
      setFailure("");
      try {
        const payload = await decideHumanGate(sessionId, stageId, decision, engine);
        setSession(payload);
        if (payload.stage_translation) setTranslation(payload.stage_translation);
        // The server recorded which engine it ran under; recording that keeps
        // the next read pointed at the same directory.
        if (payload.engine) saveOrchestrationEngine(payload.engine);
        // `error` is the discriminator, not `status`: the endpoint answers with
        // the last pass's fold, which reads "error" on a session whose earlier
        // pass failed -- that is not the decision being refused. A non-empty
        // `error` is the only refusal signal there is.
        if (payload.error) {
          // A bad decision value or a card that is not a gate: the endpoint
          // answers with the cards still attached, so the board keeps them and
          // says what was wrong instead of blanking.
          setFailure(payload.error || t("orchestrationDecisionFailed"));
          return;
        }
        // The endpoint records the decision and persists it; it deliberately
        // does not advance the plan, because `/api/orchestration/run` is the
        // single path that dispatches a stage. Chaining the pass here is what
        // turns one click into one visible result -- and the run below is the
        // same call the run button makes, with the operator's own grants.
        await run("");
      } catch (error) {
        setFailure(`${t("orchestrationDecisionFailed")} ${error}`);
      } finally {
        setBusy(false);
      }
    },
    [engine, plan, run, sessionId, t]
  );

  const cards = boardCards(plan, session);
  useEffect(() => update({ plan, session }), [plan, session, update]);
  const pending = session?.pending_confirmations ?? [];
  // Gates nobody has decided yet. Its own list, its own line: a gate is
  // decided, not approved, and the two summaries answer different questions.
  const pendingGates = session?.pending_human_gates ?? [];
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
            aria-describedby="orchestration-run-reason"
          >
            {busy ? t("orchestrationRunning") : session ? t("orchestrationContinue") : t("orchestrationRun")}
          </button>
          <p id="orchestration-run-reason">{busy ? t("operationRunning") : cards.length ? t("operationIdle") : t("operationNeedsPlan")}</p>
        </div>
      </form>

      {pending.length ? (
        <p className="or-pending" id="orchestration-pending" data-count={pending.length}>
          {t("orchestrationPending", { count: pending.length })}: {pending.join(", ")}
        </p>
      ) : null}

      {pendingGates.length ? (
        <p className="or-pending or-pending-gates" id="orchestration-pending-gates" data-count={pendingGates.length}>
          {t("orchestrationGatesPending", { count: pendingGates.length })}: {pendingGates.join(", ")}
        </p>
      ) : null}

      {gates.length ? (
        <section className="or-gates" id="orchestration-gates">
          <h4>{t("orchestrationHumanGates")}</h4>
          {gates.map((gate) => (
            <div className="or-gate" data-gate={gate.id} key={gate.id}>
              <span>{localizedTitle(gate, locale) || gate.id}</span>
              <button className="or-link" type="button" onClick={() => onOpenConsole(gate.id)}>
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
              // A decision attaches to a session: before the first pass there
              // is nothing on the server to attach it to, and a button that
              // could only answer "run the plan first" would be a dead end
              // that looks like a control.
              decidable={session !== null && decidableCards([card]).length > 0}
              onDecide={(decision) => void decide(card.id, decision)}
            />
          ))}
        </div>
      ) : (
        <EmptyState title={t("orchestrationNoPlan")} body={t("operationNeedsPlan")} />
      )}
    </div>
  );
}
