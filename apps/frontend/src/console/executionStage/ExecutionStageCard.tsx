import type { ExecuteStage } from "../../shared/types";
import { AssetList } from "../FlowConsole.parts";


export function ExecutionStageCard({ stage, t }: { stage: ExecuteStage; t: (key: string) => string }) {
  const metadata = stage.metadata || {};
  const approved = metadata.approved_assets || [];
  const skipped = metadata.skipped_assets || [];
  const revision = metadata.revision_asset_ids || [];
  const rejected = metadata.rejected_asset_ids || [];
  const pending = metadata.pending_asset_ids || [];
  const hasApprovalPreview = stage.name === "approval_gate" && Object.keys(metadata).length > 0;

  return (
    <article className="stage-card" data-state={stage.status === "done" ? "ready" : stage.status === "failed" ? "unavailable" : "degraded"}>
      <div className="stage-top">
        <h4>{stage.name}</h4>
        <span className="mcp-state">{stage.status}</span>
      </div>
      <p>{stage.detail}</p>
      {stage.artifacts?.length ? <code>{stage.artifacts.join(", ")}</code> : null}
      {stage.logs?.length ? (
        <div className="approval-assets">
          <span>{t("stageLogs")}</span>
          <ul>
            {stage.logs.map((line) => (
              <li key={line}>{line}</li>
            ))}
          </ul>
        </div>
      ) : null}
      {hasApprovalPreview ? (
        <div className="approval-preview">
          <div className="approval-summary">
            <span>{t("approvalGateApproved")}: {approved.length}</span>
            <span>{t("approvalGateSkipped")}: {skipped.length}</span>
            <span>{t("approvalGateRevision")}: {revision.length}</span>
            <span>{t("approvalGateRejected")}: {rejected.length}</span>
            <span>{t("approvalGatePending")}: {pending.length}</span>
          </div>
          {metadata.manifest_path ? <p>{t("approvalGateManifest")}: <code>{metadata.manifest_path}</code></p> : null}
          {metadata.report_path ? <p>{t("approvalGateReport")}: <code>{metadata.report_path}</code></p> : null}
          {metadata.blocked_reason ? <p>{t("approvalGateBlockedReason")}: {metadata.blocked_reason}</p> : null}
          {approved.length ? <AssetList title={t("approvalGateApprovedAssets")} items={approved} /> : null}
          {skipped.length ? <AssetList title={t("approvalGateSkippedAssets")} items={skipped} /> : null}
        </div>
      ) : null}
    </article>
  );
}
