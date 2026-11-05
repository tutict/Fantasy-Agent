/**
 * Console-specific rendering.
 *
 * The five plan panels this file used to own (overview / tasks / build /
 * visuals / qa) now live once, in `shared/panels/PlanPanels.tsx`, and are
 * re-exported here so the console's own imports stay put. What remains is what
 * only the console renders: the creative review workspace with its per-asset
 * decision buttons, the spec-bundle inspector, and the small formatting helpers
 * those two need.
 *
 * `pipeline` is not among them any more. Stage rows belong to the orchestration
 * board (`src/orchestration/`), which is the only module that reads
 * `production_pipeline.stages`; there used to be three copies of a stage row
 * here, in the workbench and in the console's own stage track, and no two of
 * them rendered the same fields.
 *
 * `selectedEngineVersion` and `usesGodotEngine` also moved to
 * `shared/planModel.ts`; they are re-exported for the same reason.
 */

import type { CreativeReview, CreativeReviewItem, DirectorBuildPlan, GameplaySpec, Locale, ProductionSpecBundle, PromptRequest, SpecBundlePreviewResponse } from "../shared/types";
import { diffSpecs, specDigest, type SpecDiffResult } from "../shared/specDiff";
import type { Translator } from "../shared/panels/PlanPanels";
import { localizedArray, planDisplayTitle, planningText, specDisplayTitle, specFieldText } from "../shared/planModel";

export {
  BuildPanel,
  OverviewPanel,
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

export function preferredTitle(
  plan: DirectorBuildPlan | undefined,
  locale: Locale,
  t: Translator
): string {
  return planDisplayTitle(plan, locale) || t("emptyTitle");
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
  locale = "en",
  decisions,
  setDecision,
  manifestPath,
  onWriteManifest,
  t
}: {
  review?: CreativeReview;
  locale?: Locale;
  decisions: Record<string, string>;
  setDecision: (assetId: string, decision: string) => void;
  manifestPath?: string;
  onWriteManifest?: () => void;
  t: Translator;
}) {
  const items = review?.items || [];
  return (
    <div className="review-layout" id="approval-creative_review">
      <div className="review-board" id="review-output">
        {items.length ? (
          items.map((item) => (
            <ReviewItem
              key={item.asset_id}
              item={item}
              locale={locale}
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
            <p>{planningText(review.art_direction?.visual_intent, locale)}</p>
            <h3>{t("reviewQuestions")}</h3>
            {list(localizedArray(review.art_direction?.user_review_questions, locale), t)}
            <h3>{t("requiredDecisions")}</h3>
            {list(localizedArray(review.required_user_decisions, locale), t)}
            <div className="review-meta">
              <span className="review-pill">
                {t("approvalGate")}: {planningText(review.approval_gate, locale)}
              </span>
            </div>
            <button className="secondary-action" type="button" onClick={onWriteManifest}>
              {t("writeApprovalManifest")}
            </button>
            {manifestPath ? (
              <p className="ui-hint">
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
  locale,
  decision,
  setDecision,
  t
}: {
  item: CreativeReviewItem;
  locale: Locale;
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
    <section className="review-item" id={`review-asset-${item.asset_id || "unknown"}`} data-review-asset={item.asset_id || ""}>
      <div>
        <h3>{item.asset_id}</h3>
        <p>{planningText(item.user_prompt, locale)}</p>
        <code>{item.asset_path}</code>
        <div className="review-meta">
          <span className="review-pill" data-status={decision}>{statusLabel(decision, t)}</span>
          <span className="review-pill">{item.source}</span>
          <span className="review-pill">{planningText(item.gameplay_role, locale)}</span>
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
  spec,
  locale = "en",
  preview,
  error,
  t
}: {
  bundle?: ProductionSpecBundle;
  spec?: GameplaySpec;
  locale?: Locale;
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
  const titleSpec = spec?.title === bundle.gameplay_spec_title ? spec : { title: bundle.gameplay_spec_title };
  const objective = bundle.narrative?.hud_text?.objective || bundle.narrative?.premise;
  const objectiveField = objective === spec?.win_state ? "win_state" : objective === spec?.logline ? "logline" : "";
  return (
    <div className="spec-bundle-layout">
      <header className="spec-bundle-header">
        <div>
          <p className="eyebrow">{t("specBundleSource")}</p>
          <h3>{specDisplayTitle(titleSpec, locale) || t("specBundleTitle")}</h3>
        </div>
        <span className="status-chip" data-status={validation?.status || "idle"}>
          {planningText(validation?.status, locale) || t("specPreviewLoading")}
        </span>
      </header>
      {error ? (
        <p className="ui-hint">
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
          <p>{(bundle.level?.objective_gates || []).map((value) => value === spec?.win_state ? specFieldText(spec, "win_state", value, locale) : planningText(value, locale)).join(", ") || "-"}</p>
        </section>
        <section className="spec-domain">
          <h3>{t("specNumeric")}</h3>
          <strong>{bundle.numeric?.target_session_minutes || "-"} {locale === "zh-CN" ? t("minutes") : "min"}</strong>
          <p>
            {t("specMoveSpeed")}: {bundle.numeric?.player_move_speed || "-"}
          </p>
        </section>
        <section className="spec-domain">
          <h3>{t("specNarrative")}</h3>
          <strong>{bundle.narrative?.beats?.length || 0}</strong>
          <p>{(objectiveField ? specFieldText(spec, objectiveField, objective, locale) : planningText(objective, locale)) || "-"}</p>
        </section>
        <section className="spec-domain">
          <h3>{t("specConfig")}</h3>
          <strong>{bundle.config_tables?.tables?.length || 0}</strong>
          <p>{t("specTables")}</p>
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
                <strong>{planningText(issue.severity, locale)}</strong> <code>{issue.field}</code> {issue.message}
              </li>
            ))}
          </ul>
        ) : (
          <p>{t("specValidationClean")}</p>
        )}
      </section>
      <details className="spec-section" id="spec-artifacts">
        <summary>{t("specArtifacts")}</summary>
        {list((bundle.config_tables?.tables || []).map((table) => table.table_id || "-"), t)}
        {list((preview?.artifacts || []).map((artifact) => artifact.path || "-"), t)}
      </details>
      <details className="spec-section" id="spec-traces">
        <summary>{t("specTrace")}</summary>
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
      </details>
      <section className="spec-section">
        <h3>{t("specExecutableQa")}</h3>
        <div className="spec-qa-list">
          {qaResults.map((result) => (
            <div
              className="spec-qa-row"
              data-state={result.passed ? "passed" : result.severity}
              key={result.assertion_id}
            >
              <strong title={result.assertion_id}>{planningText(result.assertion_id, locale)}</strong>
              <span>{result.passed ? t("specQaPassed") : planningText(result.message, locale)}</span>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}

/**
 * Diff the spec the handoff froze against the one `/api/design` returns now.
 *
 * **Why this panel exists.** Everything above it renders the spec that arrived
 * inside the handoff, and that snapshot is frozen at publish time. Change the
 * prompt, the generator, or the LLM settings and the numbers above keep drawing
 * the old spec with nothing on screen to say so. Only a regeneration makes the
 * drift visible, and only a field-by-field comparison makes it legible.
 *
 * **The prompt caveat is not decoration.** `promptRequestFromPlan` reconstructs
 * the request from the plan, and the plan never stored the prompt, so the request
 * sent here carries the title plus the logline instead. The hint says that in as
 * many words: without it an operator would read a diff of two unrelated specs as
 * a drift report.
 *
 * **Read-only.** `previewGameplaySpec` writes nothing and launches nothing, so
 * there is no confirm gate here. Adopting the regenerated spec into the plan
 * would be a write, and that is deliberately not offered -- the plan is the
 * planning workbench's to republish.
 */
export function SpecRegenPanel({
  request,
  locale = "en",
  regenerated,
  regenerating,
  error,
  baseline,
  onRegenerate,
  onClear,
  t
}: {
  request: PromptRequest | null;
  locale?: Locale;
  regenerated?: GameplaySpec | null;
  regenerating?: boolean;
  error?: string | null;
  baseline?: GameplaySpec | null;
  onRegenerate?: () => void;
  onClear?: () => void;
  t: Translator;
}) {
  const diff: SpecDiffResult | null = regenerated ? diffSpecs(baseline, regenerated) : null;
  const digest = regenerated ? specDigest(regenerated) : null;

  return (
    <section className="spec-regen" id="spec-regen">
      <div className="spec-regen-head">
        <div>
          <h3>{t("specRegenTitle")}</h3>
          <p className="ui-hint">{t("specRegenHint")}</p>
        </div>
        {diff ? (
          <span className="status-chip" data-status={diff.mirrorStale ? "warning" : "passed"}>
            {diff.mirrorStale
              ? t("specRegenDrifted", { count: String(diff.changedCount) })
              : t("specRegenIdentical")}
          </span>
        ) : null}
      </div>

      {request ? (
        <details className="spec-regen-request">
          <summary>{t("specRegenRequest")}</summary>
          <dl>
            <div>
              <dt>{t("specRegenPrompt")}</dt>
              <dd>
                <code>{request.prompt}</code>
              </dd>
            </div>
            <div>
              <dt>{t("specRegenScope")}</dt>
              <dd>
                {request.target_minutes} {t("minutes")} / {request.engine_version} /{" "}
                {(request.platforms || []).join(", ")} / {(request.output_locales || []).join(", ")}
              </dd>
              {/*
                The scope line lists engine and platforms flat, which reads as
                "all four of these shaped the diff". They did not: the offline
                generator reads the prompt and target length only, and the other
                two are consulted solely on the LLM path. Without this note an
                operator changing the engine, seeing no drift, and concluding the
                backend ignored them would be right -- but for the wrong reason,
                and they would have no way to tell that from a healthy no-op.
              */}
              <dd className="ui-hint">{t("specRegenScopeCaveat")}</dd>
            </div>
          </dl>
          <p className="ui-hint">{t("specRegenPromptCaveat")}</p>
        </details>
      ) : (
        <p className="ui-hint">{t("specRegenNeedsPlan")}</p>
      )}

      <div className="spec-regen-actions">
        <button
          className="secondary-action"
          type="button"
          id="spec-regen-button"
          disabled={!request || regenerating}
          onClick={onRegenerate}
        >
          {regenerating ? t("specRegenRunning") : t("specRegenButton")}
        </button>
        {regenerated ? (
          <button className="ghost-action" type="button" id="spec-regen-clear" onClick={onClear}>
            {t("specRegenClear")}
          </button>
        ) : null}
      </div>

      {error ? (
        <p className="ui-hint" id="spec-regen-error">
          {t("specRegenFailed")}: {error}
        </p>
      ) : null}

      {digest ? (
        <div className="spec-regen-digest" id="spec-regen-digest">
          <span>
            {t("specRegenDigestTitle")}: <strong>{specDisplayTitle(regenerated, locale)}</strong>
          </span>
          <span>
            {t("specRegenDigestTarget")}: <strong>{digest.targetMinutes}</strong> {t("minutes")}
          </span>
          <span>
            {t("specRegenDigestVerbs")}: <strong>{digest.verbs}</strong>
          </span>
          <span>
            {t("specRegenDigestLoop")}: <strong>{digest.loopSteps}</strong>
          </span>
          <span>
            {t("specRegenDigestSystems")}: <strong>{digest.systems}</strong>
          </span>
          <span>
            {t("specRegenDigestBeats")}: <strong>{digest.beats}</strong>
          </span>
          <span>
            {t("specRegenDigestEnemies")}: <strong>{digest.enemies}</strong>
          </span>
        </div>
      ) : null}

      {diff ? (
        diff.changedCount ? (
          <div className="spec-diff-list" id="spec-diff-list">
            {diff.rows
              .filter((row) => row.changed)
              .map((row) => (
                <div className="spec-diff-row" data-state="changed" key={row.field}>
                  <code>{row.field}</code>
                  <span className="spec-diff-before">{row.baseline || t("specDiffEmpty")}</span>
                  <span aria-hidden="true">-&gt;</span>
                  <span className="spec-diff-after">{row.regenerated || t("specDiffEmpty")}</span>
                </div>
              ))}
          </div>
        ) : (
          <p className="ui-hint" id="spec-diff-list">
            {t("specDiffNone")}
          </p>
        )
      ) : null}
    </section>
  );
}
