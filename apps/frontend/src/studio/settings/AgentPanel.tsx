import { useState } from "react";

import { runAgent } from "../../shared/api";
import type { Translator } from "../../shared/i18n";
import type { AgentRunResult } from "../../shared/types";
import { ToolCatalogPanel } from "./ToolCatalogPanel";

/**
 * One agent run: a goal, the grants it may use, and what it did with them.
 *
 * Moved out of `StudioShell.tsx` under the `docs/ui/architecture.md` §5
 * criteria -- over 50 lines, its own `agent-*` class prefix, and dedicated
 * i18n keys. Behaviour is unchanged; it still mounts the tool catalog below the
 * form rather than behind a tab, because "what the run was allowed to do" is
 * part of the same answer as "what it did".
 */
export function AgentPanel({ t }: { t: Translator }) {
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
