import { makeTranslator } from "./i18n";
import { useLocaleTheme } from "./localeTheme";
import { projectI18n } from "./projectI18n";
import { projectStore, useProject } from "./projectStore";
import { Button } from "./ui/primitives";
export function DraftActions({ showLatest, onShowLatest }: { showLatest: boolean; onShowLatest: (value: boolean) => void }) {
  const project = useProject(); const { locale } = useLocaleTheme(); const t = makeTranslator(locale, projectI18n);
  if (!project.draft) return null;
  return <div className="project-draft" data-status={project.conflict ? "warning" : "ready"}>
    <p>{t("draft", { version: project.draft.baseVersion })}</p>
    {project.conflict ? <><p role="alert">{t("conflict")}</p><Button onClick={() => onShowLatest(!showLatest)}>{t(showLatest ? "keepDraft" : "latest")}</Button></> : null}
    <Button disabled={project.saving || (project.conflict && !showLatest)} onClick={() => { if (!project.active) void projectStore.create(project.draft!.plan.gameplay_spec?.title ?? t("project"), project.draft!.plan); else void projectStore.saveDraft(project.conflict); }}>{t(project.saving ? "saving" : project.conflict ? "replace" : "save")}</Button>
    <Button disabled={project.saving} onClick={() => projectStore.discardDraft()}>{t("discard")}</Button>
  </div>;
}
