import { useState } from "react";
import { makeTranslator } from "./i18n";
import { useLocaleTheme } from "./localeTheme";
import { projectI18n } from "./projectI18n";
import { projectStore, useProject } from "./projectStore";
import { Button } from "./ui/primitives";

export function ProjectControls() {
  const project = useProject();
  const { locale } = useLocaleTheme();
  const t = makeTranslator(locale, projectI18n);
  const [name, setName] = useState("");
  return <div className="project-controls">
    <label><span>{t("project")}</span>
      <select aria-label={t("project")} value={project.active?.project_id ?? ""} disabled={project.loading}
        onChange={(event) => void projectStore.select(event.target.value)}>
        <option value="" disabled>{project.loading ? t("loading") : t("empty")}</option>
        {project.projects.map((item) => <option key={item.project_id} value={item.project_id}>{item.name}</option>)}
      </select>
    </label>
    {project.active ? <span className="project-version">{t("version", { version: project.active.plan_version })}</span> : null}
    <details><summary>{t("create")}</summary><form onSubmit={(event) => { event.preventDefault(); if (name.trim()) void projectStore.create(name.trim(), project.active ? undefined : project.draft?.plan); }}>
      <label>{t("name")}<input value={name} maxLength={120} onChange={(event) => setName(event.target.value)} /></label>
      <Button type="submit" disabled={!name.trim()}>{t("create")}</Button>
    </form></details>
    {project.error ? <div className="project-error" role="alert" data-status="error"><span>{project.error}</span><Button onClick={() => void projectStore.refresh()}>{t("retry")}</Button></div> : null}
  </div>;
}
