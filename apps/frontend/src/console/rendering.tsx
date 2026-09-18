/**
 * Console-specific rendering.
 *
 * The six plan panels this file used to own (overview / pipeline / tasks /
 * build / visuals / qa) now live once, in `shared/panels/PlanPanels.tsx`, and
 * are re-exported here so the console's own imports stay put. What remains is
 * what only the console renders: the creative review workspace with its
 * per-asset decision buttons, the spec-bundle inspector, and the small
 * formatting helpers those two need.
 *
 * `selectedEngineVersion` and `usesGodotEngine` also moved to
 * `shared/planModel.ts`; they are re-exported for the same reason.
 */

import type { CreativeReview, CreativeReviewItem, Locale, ProductionSpecBundle, SpecBundlePreviewResponse } from "../shared/types";

export {
  BuildPanel,
  OverviewPanel,
  PipelinePanel,
  QaPanel,
  TasksPanel,
  VisualsPanel,
  type Translator
} from "../shared/panels/PlanPanels";
export { selectedEngineVersion, usesGodotEngine } from "../shared/planModel";

/**
 * The shared panels emit `wb-*` class names, and `workbench.css` is where they
 * are styled. The workbench imports that sheet; the console has to load it too
 * or the panels it now re-exports render as unstyled HTML. Imported here rather
 * than in `FlowConsole.tsx` so the dependency sits next to the reason for it.
 */
import "../styles/workbench.css";

/**
 * The console's stage track and the shared panels both resolve a stage's
 * display title the same way, so this is the shared helper under the name the
 * console already imports it by.
 */
export { localizedTitle as localizedStageTitle } from "../shared/planModel";

/** The console translates with a flat key lookup, so the fallback is the key. */
type Translator = (key: string) => string;

export function preferredTitle(
  plan: { gameplay_spec?: { title?: string } } | undefined,
  locale: Locale,
  t: Translator
): string {
  const spec = plan?.gameplay_spec as
    | { title?: string; i18n?: { field_translations?: { title?: Partial<Record<Locale, string>> } } }
    | undefined;
  if (!spec) return t("emptyTitle");
  return locale === "zh-CN" && spec.i18n?.field_translations?.title?.["zh-CN"]
    ? spec.i18n.field_translations.title["zh-CN"] ?? t("emptyTitle")
    : spec.title ?? t("emptyTitle");
}

export function statusLabel(status: string | undefined, t: Translator): string {
  if (status === "approved") return t("approved");
  if (status === "needs_revision") return t("needsRevision");
  if (status === "rejected") return t("rejected");
  if (status === "pending_user_review") return t("pendingReview");
  return status || "-";
}

export function GateItem({ title, detail }: { title: string; detail: string }) {
  return (
    <div className="gate-item">
      <strong>{title}</strong>
      <span>{detail}</span>
    </div>
  );
}

function list(items: unknown[] | undefined, t: Translator) {
  if (!items?.length) return <p>{t("noItems")}</p>;
  return (
    <ul>
      {items.map((item, index) => (
        <li key={`${String(item)}-${index}`}>{String(item)}</li>
      ))}
    </ul>
  );
}

export function ReviewPanel({
  review,
  decisions,
  setDecision,
  manifestPath,
  onWriteManifest,
  t
}: {
  review?: CreativeReview;
  decisions: Record<string, string>;
  setDecision: (assetId: string, decision: string) => void;
  manifestPath?: string;
  onWriteManifest?: () => void;
  t: Translator;
}) {
  const items = review?.items || [];
  return (
    <div className="review-layout">
      <div className="review-board" id="review-output">
        {items.length ? (
          items.map((item) => (
            <ReviewItem
              key={item.asset_id}
              item={item}
              decision={decisions[item.asset_id || ""] || item.approval_status || ""}
              setDecision={setDecision}
              t={t}
            />
          ))
        ) : (
          <section className="review-item">
            <div>
              <h3>{t("creativeReview")}</h3>
              <p>{t("noItems")}</p>
            </div>
          </section>
        )}
      </div>
      <aside className="review-inspector" id="review-inspector">
        {review ? (
          <>
            <h3>{t("artDirection")}</h3>
            <p>{review.art_direction?.visual_intent}</p>
            <h3>{t("reviewQuestions")}</h3>
            {list(review.art_direction?.user_review_questions, t)}
            <h3>{t("requiredDecisions")}</h3>
            {list(review.required_user_decisions, t)}
            <div className="review-meta">
              <span className="review-pill">
                {t("approvalGate")}: {review.approval_gate}
              </span>
            </div>
            <button className="secondary-action" type="button" onClick={onWriteManifest}>
              {t("writeApprovalManifest")}
            </button>
            {manifestPath ? (
              <p className="handoff-note">
                {t("approvalManifestWritten")}: <code>{manifestPath}</code>
              </p>
            ) : null}
          </>
        ) : null}
      </aside>
    </div>
  );
}

function ReviewItem({
  item,
  decision,
  setDecision,
  t
}: {
  item: CreativeReviewItem;
  decision: string;
  setDecision: (assetId: string, decision: string) => void;
  t: Translator;
}) {
  const actions: Array<[string, string]> = [
    ["approved", t("approve")],
    ["needs_revision", t("revise")],
    ["rejected", t("reject")]
  ];
  return (
    <section className="review-item">
      <div>
        <h3>{item.asset_id}</h3>
        <p>{item.user_prompt}</p>
        <code>{item.asset_path}</code>
        <div className="review-meta">
          <span className={`review-pill ${decision}`}>{statusLabel(decision, t)}</span>
          <span className="review-pill">{item.source}</span>
          <span className="review-pill">{item.gameplay_role}</span>
        </div>
      </div>
      <div className="review-actions">
        {actions.map(([value, label]) => (
          <button
            className={`review-action ${decision === value ? "active" : ""}`}
            type="button"
            data-asset-id={item.asset_id}
            data-decision={value}
            key={value}
            onClick={() => item.asset_id && setDecision(item.asset_id, value)}
          >
            {label}
          </button>
        ))}
      </div>
    </section>
  );
}

export function SpecBundlePanel({
  bundle,
  preview,
  error,
  t
}: {
  bundle?: ProductionSpecBundle;
  preview?: SpecBundlePreviewResponse | null;
  error?: string | null;
  t: Translator;
}) {
  if (!bundle) {
    return (
      <div className="spec-bundle-layout">
        <p>{t("specBundleEmpty")}</p>
      </div>
    );
  }
  const segments = [
    bundle.level?.teaching_segment,
    ...(bundle.level?.mid_segments || []),
    bundle.level?.final_test
  ].filter(Boolean);
  const validation = preview?.validation || bundle.validation || undefined;
  const qaResults = preview?.executable_qa?.results || [];
  return (
    <div className="spec-bundle-layout">
      <header className="spec-bundle-header">
        <div>
          <p className="eyebrow">{t("specBundleSource")}</p>
          <h3>{bundle.gameplay_spec_title || t("specBundleTitle")}</h3>
        </div>
        <span className={`status-chip spec-status ${validation?.status || "idle"}`}>
          {validation?.status || t("specPreviewLoading")}
        </span>
      </header>
      {error ? (
        <p className="handoff-note">
          {t("specPreviewFailed")}: {error}
        </p>
      ) : null}
      <div className="spec-domain-grid">
        <section className="spec-domain">
          <h3>{t("specCombat")}</h3>
          <strong>{bundle.combat?.encounters?.length || 0}</strong>
          <p>{t("specEncounters")}</p>
        </section>
        <section className="spec-domain">
          <h3>{t("specLevel")}</h3>
          <strong>{segments.length}</strong>
          <p>{(bundle.level?.objective_gates || []).join(", ") || "-"}</p>
        </section>
        <section className="spec-domain">
          <h3>{t("specNumeric")}</h3>
          <strong>{bundle.numeric?.target_session_minutes || "-"} min</strong>
          <p>
            {t("specMoveSpeed")}: {bundle.numeric?.player_move_speed || "-"}
          </p>
        </section>
        <section className="spec-domain">
          <h3>{t("specNarrative")}</h3>
          <strong>{bundle.narrative?.beats?.length || 0}</strong>
          <p>{bundle.narrative?.hud_text?.objective || bundle.narrative?.premise || "-"}</p>
        </section>
        <section className="spec-domain">
          <h3>{t("specConfig")}</h3>
          <strong>{bundle.config_tables?.tables?.length || 0}</strong>
          <p>{(bundle.config_tables?.tables || []).map((table) => table.table_id).join(", ")}</p>
        </section>
        <section className="spec-domain">
          <h3>{t("specResources")}</h3>
          <strong>{bundle.resource_pipeline?.assets?.length || 0}</strong>
          <p>
            {t("specBlocked")}: {bundle.resource_pipeline?.blocked_assets?.length || 0}
          </p>
        </section>
      </div>
      <section className="spec-section">
        <h3>{t("specValidation")}</h3>
        {validation?.issues?.length ? (
          <ul>
            {validation.issues.map((issue, index) => (
              <li key={`${issue.field || "issue"}-${index}`}>
                <strong>{issue.severity}</strong> <code>{issue.field}</code> {issue.message}
              </li>
            ))}
          </ul>
        ) : (
          <p>{t("specValidationClean")}</p>
        )}
      </section>
      <section className="spec-section">
        <h3>{t("specArtifacts")}</h3>
        {list((preview?.artifacts || []).map((artifact) => artifact.path || "-"), t)}
      </section>
      <section className="spec-section">
        <h3>{t("specTrace")}</h3>
        <div className="spec-trace-list">
          {(preview?.traces || []).map((trace, index) => (
            <div className="spec-trace-row" key={`${trace.spec_field || "trace"}-${index}`}>
              <code>{trace.spec_field}</code>
              <span>-&gt;</span>
              <code>{trace.artifact_path}</code>
              <span>{trace.consumer}</span>
            </div>
          ))}
          {!preview?.traces?.length ? <p>{t("specPreviewLoading")}</p> : null}
        </div>
      </section>
      <section className="spec-section">
        <h3>{t("specExecutableQa")}</h3>
        <div className="spec-qa-list">
          {qaResults.map((result) => (
            <div
              className="spec-qa-row"
              data-state={result.passed ? "passed" : result.severity}
              key={result.assertion_id}
            >
              <strong>{result.assertion_id}</strong>
              <span>{result.passed ? t("specQaPassed") : result.message}</span>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
