export function PlaytestConfirmBlock({
  effects,
  t,
  onProceed,
  onCancel
}: {
  effects: string[];
  t: (key: string, args?: Record<string, unknown>) => string;
  onProceed: () => void;
  onCancel: () => void;
}) {
  // The engine really launches on proceed, so the block lists the effects the
  // *backend* reported and wires proceed to the caller's confirmed run. It has
  // no way to start a run itself -- that is the point of the split.
  return (
    <div id="playtest-confirm" className="generate-confirm">
      <strong>{t("playtestConfirmTitle")}</strong>
      <p>{t("playtestConfirmIntro")}</p>
      <ul>{effects.map((effect) => <li key={effect}>{effect}</li>)}</ul>
      <div className="handoff-actions">
        <button className="primary-action" type="button" id="playtest-proceed" onClick={onProceed}>
          {t("generateConfirmProceed")}
        </button>
        <button className="ghost-action" type="button" id="playtest-cancel" onClick={onCancel}>
          {t("generateConfirmCancel")}
        </button>
      </div>
    </div>
  );
}
