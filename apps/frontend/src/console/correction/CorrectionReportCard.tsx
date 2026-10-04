import type { CorrectionReport } from "../../shared/types";

export function CorrectionReportCard({ report, t }: { report: CorrectionReport; t: (key: string, args?: Record<string, unknown>) => string }) {
  const drifted = report.drifted || [];
  const recoverable = report.recoverable || [];
  const engineOnly = report.engine_only || [];

  // Both numbers can be missing, and neither means "unchanged": `generated_value`
  // is absent when the manifest recorded no baseline for the anchor, `value` when
  // the script did not yield a number. Rendering those as empty slots next to an
  // arrow produced " -> 4.0" and "8 -> ", neither of which tells the reader
  // where the number came from -- and "no evidence" is the claim this report
  // makes everywhere else too (`correctionHashUnknown` on a file).
  const delta = (item: { generated_value?: number | null; value?: number }) => (
    <>
      {item.generated_value === null || item.generated_value === undefined ? (
        <span className="task-pill">{t("correctionNoBaseline")}</span>
      ) : (
        item.generated_value
      )}
      {" → "}
      {item.value === undefined ? (
        <span className="task-pill">{t("correctionNoValue")}</span>
      ) : (
        <strong>{item.value}</strong>
      )}
    </>
  );

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
                <span>{delta(item)}</span>
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
                <span>{delta(item)}</span>
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
