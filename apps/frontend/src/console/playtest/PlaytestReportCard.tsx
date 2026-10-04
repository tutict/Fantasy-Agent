import type { PlaytestReport } from "../../shared/types";
import { Metric } from "../FlowConsole.parts";


export function PlaytestReportCard({
  report,
  t,
  onResume
}: {
  report: PlaytestReport;
  t: (key: string, args?: Record<string, unknown>) => string;
  onResume?: (stage: string) => void;
}) {
  const aggregate = report.aggregate || {};
  const runs = aggregate.runs ?? 0;
  return (
    <div className="playtest-report" id="playtest-report">
      <span className={`playtest-verdict playtest-${report.status || "unknown"}`}>
        {t(report.status === "passed" ? "playtestStatusPassed" : report.status === "warning" ? "playtestStatusWarning" : "playtestStatusFailed")}
      </span>
      <div className="playtest-metrics">
        <Metric label={t("playtestRuns")} value={String(runs)} id="playtest-run-count" />
        <Metric label={t("playtestPlayable")} value={`${aggregate.playable_runs ?? 0}/${runs}`} id="playtest-playable-count" />
        <Metric label={t("playtestOutcomes")} value={`${aggregate.wins ?? 0} / ${aggregate.failures ?? 0} / ${aggregate.timeouts ?? 0}`} id="playtest-outcomes" />
        <Metric
          label={t("playtestSessionSeconds")}
          value={`${(aggregate.session_seconds_p50 ?? 0).toFixed(1)}s p50 / ${(aggregate.session_seconds_p95 ?? 0).toFixed(1)}s p95`}
          id="playtest-seconds"
        />
      </div>
      {report.findings?.length ? (
        <ul className="playtest-findings">
          {report.findings.map((finding) => (
            <li key={finding.code} className={`playtest-finding playtest-${finding.severity || "warning"}`}>
              <strong>{finding.code}</strong>
              <span>{finding.message}</span>
              <span className="playtest-rework">
                {t("playtestReworkTarget")}: {finding.rework_target}
              </span>
              {finding.resume_stage && onResume ? (
                <button className="ghost-action" type="button" onClick={() => onResume(finding.resume_stage || "")}>
                  {t("playtestResume", { stage: finding.resume_stage || "" })}
                </button>
              ) : null}
            </li>
          ))}
        </ul>
      ) : null}
      {report.goal_notes?.length ? (
        <ul className="playtest-notes">
          {report.goal_notes.map((note) => <li key={note}>{note}</li>)}
        </ul>
      ) : null}
      {report.artifact_paths?.length ? (
        <p className="handoff-note">
          {t("playtestArtifacts")}: <code>{report.artifact_paths.join(", ")}</code>
        </p>
      ) : null}
    </div>
  );
}
