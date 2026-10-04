import type { ReactNode } from "react";

import type { Locale } from "../shared/types";

/**
 * The console's own small pieces, in one place because they are not pieces of
 * the console's logic: they have no state, no async and no route knowledge.
 *
 * They live beside `FlowConsole.tsx` rather than inside it because that file was
 * over 1200 lines and these are the least interesting part of it.
 *
 * **They are exported, and other files import them**: `ExecutionStageCard`
 * takes `AssetList`, `PlaytestReportCard` takes `Metric`, `parts.test.tsx`
 * covers all six. An earlier version of this comment said "NOT exported --
 * nothing else uses them", which had been true when the file was written and
 * stopped being true the moment the first card was extracted. Comments that
 * describe who uses a thing go stale silently; this one had to be corrected by
 * a reviewer, not by anything failing.
 *
 * One file rather than one component each is deliberate: the split criterion is
 * in `docs/ui/architecture.md` §5, and its action is "out of FlowConsole.tsx",
 * not "one component per file". Note that "has a test" is explicitly not on it.
 */

export type TabKey = "review" | "specs";

export function AssetList({ title, items }: { title: string; items: string[] }) {
  return (
    <div className="approval-assets">
      <strong>{title}</strong>
      <ul>{items.slice(0, 6).map((item) => <li key={item}>{item}</li>)}</ul>
      {items.length > 6 ? <span>+{items.length - 6}</span> : null}
    </div>
  );
}

export function SegmentedControl({
  label,
  value,
  options,
  onChange,
  className = "locale-switch",
  buttonClassName = "locale-option"
}: {
  label: string;
  value: string;
  options: Array<[string, string]>;
  onChange: (value: string) => void;
  className?: string;
  buttonClassName?: string;
}) {
  return (
    <div className={className} aria-label={label}>
      {options.map(([optionValue, optionLabel]) => (
        <button className={`${buttonClassName} ${value === optionValue ? "active" : ""}`} type="button" key={optionValue} onClick={() => onChange(optionValue)}>
          {optionLabel}
        </button>
      ))}
    </div>
  );
}

export function formatSavedAt(savedAt: string | null | undefined, locale: Locale) {
  if (!savedAt) return "-";
  const parsed = new Date(savedAt);
  if (Number.isNaN(parsed.getTime())) return savedAt;
  return parsed.toLocaleString(locale, { month: "short", day: "2-digit", hour: "2-digit", minute: "2-digit" });
}

export function manualStatusLabel(status: string | undefined, t: (key: string) => string) {
  if (status === "ready") return t("manualStatusReady");
  if (status === "degraded") return t("manualStatusDegraded");
  return t("manualStatusUnavailable");
}

export function Metric({ label, value, id }: { label: string; value: string; id: string }) {
  return (
    <div className="metric">
      <span>{label}</span>
      <strong id={id}>{value}</strong>
    </div>
  );
}

export function Panel({ tab, activeTab, children }: { tab: TabKey; activeTab: TabKey; children: ReactNode }) {
  return (
    <section className={`panel ${activeTab === tab ? "active" : ""}`} id={`${tab}-panel`} data-panel={tab}>
      {children}
    </section>
  );
}
