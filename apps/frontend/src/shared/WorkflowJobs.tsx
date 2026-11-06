import { useEffect, useRef, useState } from "react";
import { makeTranslator } from "./i18n";
import { useLocaleTheme } from "./localeTheme";
import { planningText } from "./planModel";
import { projectClient } from "./projectClient";
import { projectI18n } from "./projectI18n";
import { projectStore, useProject } from "./projectStore";
import type { ProjectResource, ProjectSnapshot, WorkflowJobDetail } from "./projectTypes";
import { Button, StatusBadge } from "./ui/primitives";

const statusKeys: Record<string, string> = { failed: "statusFailed", interrupted: "statusInterrupted", expired: "statusExpired", awaiting_confirmation: "confirmation_required", awaiting_human: "pending_review", pending_user_review: "pending_review", needs_revision: "pending_review" };
const toolKeys: Record<string, string> = { execute_demo: "toolExecute", execute_assets: "toolAssets", playtest_godot_project: "toolPlaytest", run_evolution: "toolEvolution" };
const nextAction: Record<string, string> = { pending_user_review: "review", needs_revision: "review", confirmation_required: "authorization", awaiting_confirmation: "authorization", pending_review: "review", pending_adoption: "adopt", interrupted: "interrupted", expired: "expired" };
export function resultData(job: WorkflowJobDetail | undefined): Record<string, unknown> | undefined {
  const result = job?.result;
  return result?.kind && result.status && result.data ? result.data : (result as Record<string, unknown> | undefined);
}
export function currentWorkflowResult(project: ProjectSnapshot | null, jobs: Record<string, WorkflowJobDetail>, tool: string) {
  const job = [...(project?.jobs ?? [])].reverse().find((item) => item.tool_name === tool && item.plan_version === project?.plan_version && ["done", "failed", "cancelled", "interrupted"].includes(item.status));
  return job ? resultData(jobs[job.job_id] ?? job) : undefined;
}
function ResourcePreview({ projectId, resource }: { projectId: string; resource: ProjectResource }) {
  const { locale } = useLocaleTheme(); const t = makeTranslator(locale, projectI18n);
  const [preview, setPreview] = useState<{ data: unknown; mime_type: string; encoding?: "base64" } | null>(null);
  const [error, setError] = useState("");
  const [open, setOpen] = useState(false);
  const text = preview && preview.encoding !== "base64" && (/^text\//.test(preview.mime_type) || /(?:json|yaml)$/.test(preview.mime_type));
  const raster = preview?.encoding === "base64" && /^(image\/(png|jpeg|webp|gif))$/.test(preview.mime_type) && typeof preview.data === "string" && preview.data.length < 24 * 1024 * 1024;
  async function load() {
    if (open) { setOpen(false); return; }
    try { setPreview(await projectClient.resource(projectId, resource.resource_id)); setOpen(true); setError(""); }
    catch { setError(t("failed")); }
  }
  return <li className="project-resource"><code>{resource.name ?? resource.path ?? resource.resource_id}</code>
    <Button onClick={() => void load()}>{t(open ? "close" : "preview")}</Button>
    {error ? <p role="alert">{error}</p> : null}
    {open && preview ? raster ? <img alt={resource.name ?? resource.path ?? resource.resource_id} src={`data:${preview.mime_type};base64,${preview.data}`} /> : text ? <pre>{typeof preview.data === "string" ? preview.data : JSON.stringify(preview.data, null, 2)}</pre> : <p>{t("unsupported")}</p> : null}
  </li>;
}
export function WorkflowJobs() {
  const project = useProject(); const { locale } = useLocaleTheme(); const t = makeTranslator(locale, projectI18n);
  const [cancelling, setCancelling] = useState(""); const [error, setError] = useState("");
  const bindingKey = `${project.active?.project_id ?? ""}:${project.active?.plan_version ?? 0}`;
  const currentBinding = useRef(bindingKey); currentBinding.current = bindingKey;
  useEffect(() => { setCancelling(""); setError(""); }, [bindingKey]);
  async function cancel(jobId: string) {
    const captured = project.active?.project_id; if (!captured) return;
    const key = bindingKey;
    setCancelling(jobId);
    try { await projectClient.cancel(captured, jobId); await projectStore.refresh(); }
    catch { if (currentBinding.current === key) setError(t("failed")); }
    finally { if (currentBinding.current === key) setCancelling(""); }
  }
  if (!project.active?.jobs?.length) return null;
  return <section className="project-workflow" aria-label={t("workflow")}>
    <h3>{t("workflow")}</h3>{error ? <p role="alert">{error}</p> : null}
    {[...project.active.jobs].reverse().map((job) => {
      const detail = project.jobs[job.job_id]; const current = job.plan_version === project.active!.plan_version;
      const resultStatus = detail?.result?.status;
      const data = resultData(detail ?? job);
      const evolution = data?.report && typeof data.report === "object" ? data.report as Record<string, unknown> : data;
      const needsAdoption = job.tool_name === "run_evolution" && evolution?.status === "improved"
        && Number.isInteger(evolution.best_iteration) && evolution.adopted_iteration == null;
      const action = resultStatus && nextAction[resultStatus] ? nextAction[resultStatus] : needsAdoption ? "adopt" : nextAction[job.status];
      const actions = detail?.next_actions?.map((item) => typeof item === "string" ? item
        : item.summary ?? (item.tool === "request_candidate_adoption" ? t("adopt") : item.tool ?? "")).filter(Boolean) ?? [];
      return <details className="project-job" key={`${project.active!.project_id}:${job.job_id}`} open={!["done", "cancelled"].includes(job.status)}>
        <summary><span title={job.tool_name}>{t(toolKeys[job.tool_name] ?? job.tool_name)}</span><StatusBadge status={job.status} label={t(statusKeys[job.status] ?? job.status)} /><span>{t("version", { version: job.plan_version })}</span></summary>
        <p>{detail?.summary ?? job.job_id}</p>
        {detail?.detail_read_failed ? <p role="alert">{t("failed")}<Button onClick={() => void projectStore.refresh()}>{t("retry")}</Button></p> : null}
        {!current ? <p className="ui-hint">{t("oldVersion", { version: job.plan_version, current: project.active!.plan_version })}</p> : null}
        {actions.length ? actions.map((item, index) => <p role="status" key={index}>{item}</p>) : action ? <p role="status">{t(action)}</p> : null}
        {detail?.blockers?.length ? <p>{t("blockers")}: {detail.blockers.join(" · ")}</p> : null}
        {detail?.progress?.stages?.length ? <ol>{detail.progress.stages.map((stage, index) => <li key={index}>{stage.name === "playtest" ? t("toolPlaytest") : planningText(stage.name, locale)} · {planningText(t(statusKeys[stage.status ?? "running"] ?? stage.status ?? "running"), locale)} {stage.detail}</li>)}</ol> : null}
        {["queued", "running", "cancelling"].includes(job.status) ? <Button disabled={cancelling === job.job_id} onClick={() => void cancel(job.job_id)}>{t(cancelling === job.job_id ? "cancelling" : "cancel")}</Button> : null}
        {detail?.logs?.length ? <details><summary>{t("logs")}</summary><pre>{detail.logs.join("\n")}</pre></details> : null}
        {detail?.resources?.length ? <ul aria-label={t("resources")}>{detail.resources.map((resource) => <ResourcePreview key={`${project.active!.project_id}:${resource.resource_id}`} resource={resource} projectId={project.active!.project_id} />)}</ul> : null}
      </details>;
    })}
  </section>;
}
