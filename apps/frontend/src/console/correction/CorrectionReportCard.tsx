import type { CorrectionReport } from "../../shared/types";

export function CorrectionReportCard({ report, t }: { report: CorrectionReport; t: (key: string, args?: Record<string, unknown>) => string }) {
  const drifted = report.drifted || [];
  const recoverable = report.recoverable || [];
  const engineOnly = report.engine_only || [];
  return (
    <div className="correction-report" id="correction-report">
      {!report.manifest_found ? (
        <p className="handoff-note">{t("correctionNoManifest")}</p>
      ) : null}
      {drifted.length ? (
        <div className="correction-block">
          <strong>{t("correctionDrifted")}</strong>
          <ul>
            {drifted.map((item) => (
              <li key={item.path} data-kind={item.kind}>
                <code>{item.path}</code>
                {item.hash_unknown ? <span className="task-pill">{t("correctionHashUnknown")}</span> : null}
              </li>
            ))}
          </ul>
          <p className="handoff-note">{t("correctionOverwriteWarning")}</p>
        </div>
      ) : null}
      {recoverable.length ? (
        <div className="correction-block" id="correction-recoverable">
          <strong>{t("correctionRecoverable")}</strong>
          <ul>
            {recoverable.map((item) => (
              <li key={`${item.script_path}-${item.anchor}`}>
                <code>{item.anchor}</code>
                <span>
                  {item.generated_value} → <strong>{item.value}</strong>
                </span>
                <span className="playtest-rework">
                  {t("correctionSpecField")}: {item.spec_field}
                </span>
              </li>
            ))}
          </ul>
        </div>
      ) : null}
      {engineOnly.length ? (
        <div className="correction-block correction-block-warning" id="correction-engine-only">
          <strong>{t("correctionEngineOnly")}</strong>
          <ul>
            {engineOnly.map((item) => (
              <li key={`${item.script_path}-${item.anchor}`}>
                <code>{item.anchor}</code>
                <span>
                  {item.generated_value} → <strong>{item.value}</strong>
                </span>
              </li>
            ))}
          </ul>
          <p className="handoff-note">{t("correctionEngineOnlyHint")}</p>
        </div>
      ) : null}
      {report.notes?.length ? (
        <ul className="correction-notes">
          {report.notes.map((note) => (
            <li key={note}>{note}</li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}
