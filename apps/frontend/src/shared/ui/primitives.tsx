import { forwardRef, useEffect, useRef, type ButtonHTMLAttributes, type ReactNode } from "react";
import { JOURNEY_STATE_KEYS, JOURNEY_STEP_KEYS, type JourneySnapshot } from "../productionJourney";
import { planningText } from "../planModel";
import type { Locale } from "../types";

type Translator = (key: string, args?: Record<string, unknown>) => string;

export function JourneyHeader({ snapshot, locale = "en", t }: { snapshot: JourneySnapshot; locale?: Locale; t: Translator }) {
  return (
    <header className="journey-header" data-current={snapshot.currentStep}>
      <p className="journey-kicker">{t("journeyLabel")}</p>
      <div className="journey-heading">
        <h2>{snapshot.projectTitleByLocale?.[locale] || snapshot.projectTitle || t("journeyNoProject")}</h2>
        <dl>
          <div><dt>{t("journeyEngine")}</dt><dd>{snapshot.engineLabel || t("journeyUnknown")}</dd></div>
          <div><dt>{t("journeyDuration")}</dt><dd>{snapshot.targetMinutes ? t("journeyMinutes", { count: snapshot.targetMinutes }) : t("journeyUnknown")}</dd></div>
        </dl>
      </div>
      <p className="journey-focus" role="status">
        <span className="journey-focus-label">{t("journeyNext")}</span>
        <span>{t(JOURNEY_STEP_KEYS[snapshot.currentStep])}</span>
        <span>{t(JOURNEY_STATE_KEYS[snapshot.steps.find((step) => step.id === snapshot.currentStep)?.state ?? "upcoming"])}</span>
        <strong>{t(snapshot.nextActionKey)}</strong>
        {snapshot.blocker ? <em>{planningText(snapshot.blocker, locale)}</em> : null}
      </p>
    </header>
  );
}

export const Button = forwardRef<HTMLButtonElement, { children: ReactNode; tone?: "neutral" | "primary" | "danger"; className?: string } & ButtonHTMLAttributes<HTMLButtonElement>>(
  function Button({ children, tone = "neutral", className = "", ...props }, ref) {
    return <button {...props} ref={ref} data-tone={tone} className={`ui-button ${className}`.trim()}>{children}</button>;
  }
);

export function StatusBadge({ status, label }: { status: string; label: string }) {
  return <span className="status-badge" data-status={status}>{label}</span>;
}

export function EmptyState({ title, body, action }: { title: string; body: string; action?: ReactNode }) {
  return <section className="empty-state"><p className="empty-title">{title}</p><p>{body}</p>{action}</section>;
}

export function LogBlock({ title, lines }: { title: string; lines: string[] }) {
  return <section className="log-block"><p className="empty-title">{title}</p><pre>{lines.join("\n") || "-"}</pre></section>;
}

export function ConfirmDialog({ open, title, body, confirmLabel, cancelLabel, onConfirm, onCancel, children }: { open: boolean; title: string; body: string; confirmLabel: string; cancelLabel: string; onConfirm: (confirmedByUser: boolean) => void; onCancel: () => void; children?: ReactNode }) {
  const confirmRef = useRef<HTMLButtonElement>(null);
  useEffect(() => {
    if (open) confirmRef.current?.focus();
  }, [open]);
  if (!open) return null;
  return (
    <div
      className="confirm-dialog"
      role="dialog"
      aria-modal="true"
      aria-labelledby="confirm-title"
      onKeyDown={(event) => {
        if (event.key === "Escape") onCancel();
      }}
    >
      <p className="empty-title" id="confirm-title">{title}</p>
      <p>{body}</p>
      {children}
      <div>
        <Button type="button" onClick={onCancel}>{cancelLabel}</Button>
        <Button ref={confirmRef} type="button" tone="danger" value="approved" onClick={(event) => onConfirm(event.currentTarget.value === "approved")}>{confirmLabel}</Button>
      </div>
    </div>
  );
}
