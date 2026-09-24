import { forwardRef, useEffect, useRef, type ButtonHTMLAttributes, type ReactNode } from "react";
import { JOURNEY_STATE_KEYS, JOURNEY_STEP_KEYS, type JourneySnapshot } from "../productionJourney";

type Translator = (key: string, args?: Record<string, unknown>) => string;

export function JourneyHeader({ snapshot, t }: { snapshot: JourneySnapshot; t: Translator }) {
  return (
    <header className="journey-header" data-current={snapshot.currentStep}>
      <p className="journey-kicker">{t("journeyLabel")}</p>
      <div className="journey-heading">
        <h2>{snapshot.projectTitle || t("journeyNoProject")}</h2>
        <dl>
          <div><dt>{t("journeyEngine")}</dt><dd>{snapshot.engineLabel || t("journeyUnknown")}</dd></div>
          <div><dt>{t("journeyDuration")}</dt><dd>{snapshot.targetMinutes ? t("journeyMinutes", { count: snapshot.targetMinutes }) : t("journeyUnknown")}</dd></div>
        </dl>
      </div>
      <ol className="journey-steps" aria-label={t("journeyLabel")}>
        {snapshot.steps.map((step, index) => (
          <li key={step.id} data-state={step.state}>
            <span className="journey-mark" aria-hidden="true"><span>{index + 1}</span></span>
            <strong>{t(JOURNEY_STEP_KEYS[step.id])}</strong>
            <span className="journey-state">{t(JOURNEY_STATE_KEYS[step.state])}</span>
          </li>
        ))}
      </ol>
      <p className="journey-next" role="status"><strong>{t("journeyNext")}</strong><span>{t(snapshot.nextActionKey)}</span>{snapshot.blocker ? <em>{snapshot.blocker}</em> : null}</p>
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

export function Disclosure({ title, children, className = "" }: { title: string; children: ReactNode; className?: string }) {
  return <details className={`ui-disclosure ${className}`.trim()}><summary>{title}</summary><div>{children}</div></details>;
}

export function ConfirmDialog({ open, title, body, confirmLabel, cancelLabel, onConfirm, onCancel }: { open: boolean; title: string; body: string; confirmLabel: string; cancelLabel: string; onConfirm: () => void; onCancel: () => void }) {
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
      <div>
        <Button type="button" onClick={onCancel}>{cancelLabel}</Button>
        <Button ref={confirmRef} type="button" tone="danger" onClick={onConfirm}>{confirmLabel}</Button>
      </div>
    </div>
  );
}