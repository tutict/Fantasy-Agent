/**
 * Idea seed inspector: the extracted fields plus the configuration that shapes
 * every downstream payload.
 *
 * The retired static page kept `must_keep`, `can_cut`, `reference_feel` and
 * `playable_loop` in hidden textareas, so they could only ever come from the
 * backend. They are real `IdeaSeed` fields and they change the generated plan,
 * so they are editable here.
 */

import type { Locale, WorkbenchConfig } from "../shared/types";
import { MAX_TARGET_MINUTES, MIN_TARGET_MINUTES, type SeedEditorFields } from "./workbenchModel";

export interface SeedInspectorProps {
  t: (key: string, args?: Record<string, unknown>) => string;
  locale: Locale;
  fields: SeedEditorFields;
  config: WorkbenchConfig;
  seedConfirmed: boolean;
  busy: boolean;
  canConfirm: boolean;
  canExtract: boolean;
  openQuestions: string[];
  onFieldChange: (patch: Partial<SeedEditorFields>) => void;
  onConfigChange: (patch: Partial<WorkbenchConfig>) => void;
  onConfirm: () => void;
  onExtract: () => void;
}

const ENGINES = ["UE5", "UE4", "Godot 4"];
const PLATFORMS = ["Windows", "Linux", "macOS", "Android"];

export function SeedInspector({
  t,
  locale,
  fields,
  config,
  seedConfirmed,
  busy,
  canConfirm,
  canExtract,
  openQuestions,
  onFieldChange,
  onConfigChange,
  onConfirm,
  onExtract
}: SeedInspectorProps) {
  return (
    <section className="wb-card" aria-label={t("seedPreviewTitle")}>
      <header className="wb-card-head">
        <div>
          <h2>{t("seedPreviewTitle")}</h2>
          <p>{t("seedPreviewSubtitle")}</p>
        </div>
        <span className={`wb-chip ${seedConfirmed ? "ready" : ""}`}>
          {seedConfirmed ? t("seedConfirmed") : t("seedDraft")}
        </span>
      </header>

      <div className="wb-card-body">
        <h3 className="wb-block-title">{t("extractedFields")}</h3>

        <div className="wb-field">
          <label htmlFor="wb-player-fantasy">{t("playerFantasy")}</label>
          <textarea
            id="wb-player-fantasy"
            rows={2}
            value={fields.playerFantasy}
            onChange={(event) => onFieldChange({ playerFantasy: event.target.value })}
          />
        </div>

        <div className="wb-field">
          <label htmlFor="wb-core-action">{t("coreAction")}</label>
          <textarea
            id="wb-core-action"
            rows={2}
            value={fields.coreAction}
            onChange={(event) => onFieldChange({ coreAction: event.target.value })}
          />
        </div>

        <div className="wb-field-row">
          <div className="wb-field">
            <label htmlFor="wb-emotional-target">{t("emotionalTarget")}</label>
            <textarea
              id="wb-emotional-target"
              rows={2}
              value={fields.emotionalTarget}
              onChange={(event) => onFieldChange({ emotionalTarget: event.target.value })}
            />
          </div>
          <div className="wb-field">
            <label htmlFor="wb-tension-source">{t("tensionSource")}</label>
            <textarea
              id="wb-tension-source"
              rows={2}
              value={fields.tensionSource}
              onChange={(event) => onFieldChange({ tensionSource: event.target.value })}
            />
          </div>
        </div>

        <div className="wb-field">
          <label htmlFor="wb-must-keep">{t("mustKeep")}</label>
          <textarea
            id="wb-must-keep"
            rows={2}
            value={fields.mustKeep}
            onChange={(event) => onFieldChange({ mustKeep: event.target.value })}
          />
        </div>

        <div className="wb-field">
          <label htmlFor="wb-can-cut">{t("canCut")}</label>
          <textarea
            id="wb-can-cut"
            rows={2}
            value={fields.canCut}
            onChange={(event) => onFieldChange({ canCut: event.target.value })}
          />
        </div>

        <div className="wb-field">
          <label htmlFor="wb-reference-feel">{t("referenceFeel")}</label>
          <textarea
            id="wb-reference-feel"
            rows={2}
            value={fields.referenceFeel}
            onChange={(event) => onFieldChange({ referenceFeel: event.target.value })}
          />
        </div>

        <div className="wb-field">
          <label htmlFor="wb-playable-loop">{t("playableLoop")}</label>
          <textarea
            id="wb-playable-loop"
            rows={2}
            value={fields.playableLoop}
            onChange={(event) => onFieldChange({ playableLoop: event.target.value })}
          />
        </div>

        {openQuestions.length ? (
          <div className="wb-field">
            <label>{t("openQuestions")}</label>
            <ul>
              {openQuestions.map((question) => (
                <li key={question}>{question}</li>
              ))}
            </ul>
          </div>
        ) : null}

        <h3 className="wb-block-title">{t("configuration")}</h3>

        <div className="wb-field-row">
          <div className="wb-field">
            <label htmlFor="wb-minutes">{t("minutes")}</label>
            <input
              id="wb-minutes"
              type="number"
              min={MIN_TARGET_MINUTES}
              max={MAX_TARGET_MINUTES}
              value={config.targetMinutes}
              onChange={(event) => onConfigChange({ targetMinutes: Number(event.target.value) })}
            />
          </div>
          <div className="wb-field">
            <label htmlFor="wb-engine">{t("engine")}</label>
            <select
              id="wb-engine"
              value={config.engineVersion}
              onChange={(event) => onConfigChange({ engineVersion: event.target.value })}
            >
              {ENGINES.includes(config.engineVersion) ? null : (
                <option value={config.engineVersion}>{config.engineVersion}</option>
              )}
              {ENGINES.map((engine) => (
                <option key={engine} value={engine}>
                  {engine}
                </option>
              ))}
            </select>
          </div>
          <div className="wb-field">
            <label htmlFor="wb-platform">{t("platform")}</label>
            <select
              id="wb-platform"
              value={config.platform}
              onChange={(event) => onConfigChange({ platform: event.target.value })}
            >
              {PLATFORMS.includes(config.platform) ? null : (
                <option value={config.platform}>{config.platform}</option>
              )}
              {PLATFORMS.map((platform) => (
                <option key={platform} value={platform}>
                  {platform}
                </option>
              ))}
            </select>
          </div>
          <div className="wb-field">
            <label htmlFor="wb-source-locale">{t("inputLanguage")}</label>
            <select
              id="wb-source-locale"
              value={config.sourceLocale}
              onChange={(event) =>
                onConfigChange({ sourceLocale: event.target.value as Locale })
              }
            >
              <option value="en">English</option>
              <option value="zh-CN">中文</option>
            </select>
          </div>
        </div>

        <div className="wb-field">
          <label htmlFor="wb-constraints">{t("constraints")}</label>
          <textarea
            id="wb-constraints"
            rows={2}
            placeholder={t("constraintsPlaceholder")}
            value={config.constraints.join(", ")}
            onChange={(event) =>
              onConfigChange({
                constraints: event.target.value
                  .split(/[\n,，;；]/)
                  .map((part) => part.trim())
                  .filter(Boolean)
              })
            }
          />
        </div>

        <div className="wb-actions">
          <button
            type="button"
            className="wb-button ghost"
            onClick={onExtract}
            disabled={busy || !canExtract}
          >
            {t("extractSeed")}
          </button>
          <button
            type="button"
            className="wb-button primary"
            onClick={onConfirm}
            disabled={busy || !canConfirm}
          >
            {t("confirmSeed")}
          </button>
        </div>
      </div>
    </section>
  );
}
