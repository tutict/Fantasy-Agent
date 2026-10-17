import { localizedTitle } from "../shared/planModel";
import type { Locale } from "../shared/types";
import type { Translator } from "../shared/i18n";
import {
  HUMAN_STAGE_KIND,
  approvableCards,
  decisionLabelKey,
  reworkableCards,
  statusLabelKey,
  type BoardCard
} from "./orchestrationModel";

/**
 * One stage of the plan, drawn from its runtime status rather than a snapshot.
 *
 * Moved out of `OrchestrationBoard.tsx` under the `docs/ui/architecture.md` §5
 * criteria: over 50 lines, and it carries the `or-*` class prefix that ties its
 * styles to `orchestration.css`. Nothing about it changed -- the card is the
 * only place in the product that renders `risks`, `quality_gates` and
 * `depends_on` together, and the console's old stage row used to show `risks`
 * while the workbench's did not. That is the history this file inherits.
 *
 * Note what is *not* here: no approve button on a human gate. Approving one
 * does not make it run, so the button would be a control that does nothing --
 * a gate takes a *decision*, which is the pair below.
 */
export function StageCard({
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
  onOpenConsole,
  decidable,
  onDecide
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
  onOpenConsole: (stageId?: string) => void;
  /** A human gate with a session behind it and nobody's decision on it yet. */
  decidable: boolean;
  onDecide: (decision: string) => void;
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
        {isHuman && card.human_resolution ? (
          <span className="or-pill or-pill-decision" data-decision-state={card.human_resolution}>
            {t(decisionLabelKey(card.human_resolution) || card.human_resolution)}
          </span>
        ) : null}
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
          <button className="or-link" type="button" onClick={() => onOpenConsole(card.id)}>
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
        {decidable ? (
          <>
            {/*
              The gate's own decision. Two buttons, not a toggle: approving and
              sending back are different outcomes with different consequences
              for what depends on the gate, and a single switch would have to
              pick a default -- which is the one thing a decision may never do.
            */}
            <button
              className="or-button"
              type="button"
              data-decision="approved"
              disabled={busy}
              onClick={() => onDecide("approved")}
            >
              {t("orchestrationDecisionApprove")}
            </button>
            <button
              className="or-button"
              type="button"
              data-decision="rejected"
              disabled={busy}
              onClick={() => onDecide("rejected")}
            >
              {t("orchestrationDecisionReject")}
            </button>
          </>
        ) : null}
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
