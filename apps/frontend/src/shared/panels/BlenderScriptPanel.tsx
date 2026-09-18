/**
 * Blender script preview.
 *
 * **Why this exists.** The console's execution panel lists planned side effects
 * before a run, and one of them is `Deletes the active Blender scene before
 * generation.` An operator confirms that without ever seeing the Python that
 * does it: the script is generated inside the Blender worker at run time and the
 * console only ever gets back a log line. `POST /api/blender/script` returns the
 * artifact instead, which is what makes the confirmation meaningful.
 *
 * **Generated, not executed.** `build_blender_script_artifact` formats a string
 * and returns; it does not import `bpy`, spawn Blender, or touch the scene. That
 * distinction is the panel's whole risk, so the not-executed marker is part of
 * the layout rather than a footnote -- the `side_effects` list below is what a
 * later confirmed run *would* do, not what already happened.
 *
 * **Read-only, so no confirm gate.** Fetching this cannot delete anything, which
 * is why the button here has no `window.confirm` while the execution panel's
 * buttons do.
 *
 * **It emits `wb-*`, not the console's action classes.** This mounts inside the
 * shared `BuildPanel`, so it renders on `/workbench` as well as `/web-console`,
 * and `/workbench` only loads `workbench.css`. The console's `secondary-action`
 * / `ghost-action` / `status-chip` / `handoff-note` live in `console.css`, so
 * using them here would render bare HTML on the workbench route.
 * `shared/panelStyles.test.ts` fails if that happens.
 */

import { useCallback, useState } from "react";

import { previewBlenderScript } from "../api";
import type { BlenderPlan, BlenderScriptArtifact } from "../types";
import { Pill } from "./primitives";

/** The shared panels' translator shape; `args` fills `{placeholder}` pairs. */
type Translator = (key: string, args?: Record<string, unknown>) => string;

export function BlenderScriptPanel({
  plan,
  t
}: {
  plan?: BlenderPlan | null;
  t: Translator;
}) {
  const [artifact, setArtifact] = useState<BlenderScriptArtifact | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const jobCount = plan?.jobs?.length ?? 0;

  const load = useCallback(async () => {
    if (!plan) return;
    setLoading(true);
    try {
      setArtifact(await previewBlenderScript(plan));
      setError(null);
    } catch (failure) {
      setArtifact(null);
      setError(String(failure));
    } finally {
      setLoading(false);
    }
  }, [plan]);

  return (
    <section className="wb-script" id="blender-script">
      <div className="wb-script-head">
        <div>
          <h3>{t("blenderScriptTitle")}</h3>
          <p>{t("blenderScriptHint")}</p>
        </div>
        {artifact ? <Pill>{t("blenderScriptNotExecuted")}</Pill> : null}
      </div>

      {jobCount ? (
        <div className="wb-script-actions">
          <button
            className="wb-button"
            type="button"
            id="blender-script-button"
            disabled={loading}
            onClick={() => void load()}
          >
            {loading ? t("blenderScriptRunning") : t("blenderScriptButton")}
          </button>
          {artifact ? (
            <button
              className="wb-button ghost"
              type="button"
              id="blender-script-clear"
              onClick={() => {
                setArtifact(null);
                setError(null);
              }}
            >
              {t("blenderScriptClear")}
            </button>
          ) : null}
          <span className="wb-script-count">{t("blenderScriptJobs", { count: String(jobCount) })}</span>
        </div>
      ) : (
        <p className="wb-empty" id="blender-script-empty">
          {t("blenderScriptNoJobs")}
        </p>
      )}

      {error ? (
        <p className="wb-script-error" id="blender-script-error">
          {t("blenderScriptFailed")}: {error}
        </p>
      ) : null}

      {artifact ? (
        <>
          <dl className="wb-script-meta">
            {artifact.plan_name ? (
              <div>
                <dt>{t("blenderScriptPlanName")}</dt>
                <dd>{artifact.plan_name}</dd>
              </div>
            ) : null}
            {artifact.script_path ? (
              <div>
                <dt>{t("blenderScriptPath")}</dt>
                <dd>
                  <code>{artifact.script_path}</code>
                </dd>
              </div>
            ) : null}
            {artifact.import_manifest_path ? (
              <div>
                <dt>{t("blenderScriptManifest")}</dt>
                <dd>
                  <code>{artifact.import_manifest_path}</code>
                </dd>
              </div>
            ) : null}
          </dl>

          {/* The side effects come first: they are what an operator has to weigh
              before confirming a run, and the code below is long. */}
          {artifact.side_effects?.length ? (
            <section className="wb-script-section">
              <h4>{t("blenderScriptSideEffects")}</h4>
              <ul className="wb-script-effects">
                {artifact.side_effects.map((effect) => (
                  <li key={effect}>{effect}</li>
                ))}
              </ul>
            </section>
          ) : null}

          {artifact.import_manifest?.assets?.length ? (
            <section className="wb-script-section">
              <h4>{t("blenderScriptManifestAssets")}</h4>
              <div className="wb-script-assets">
                {artifact.import_manifest.assets.map((asset, index) => (
                  <div className="wb-script-asset" key={`${asset.asset_name || "asset"}-${index}`}>
                    <strong>{asset.asset_name}</strong>
                    {/* `source_file`, matching `UnrealImportAsset`. This read
                        `source_path` until a review caught it: every row
                        rendered a blank cell, and a blank cell reads as "the
                        backend did not send a path" rather than "wrong key". */}
                    <code>{asset.source_file}</code>
                    <span aria-hidden="true">-&gt;</span>
                    <code>{asset.destination_path}</code>
                  </div>
                ))}
              </div>
            </section>
          ) : null}

          {artifact.execution_notes?.length ? (
            <section className="wb-script-section">
              <h4>{t("blenderScriptNotes")}</h4>
              <ul className="wb-script-notes">
                {artifact.execution_notes.map((note) => (
                  <li key={note}>{note}</li>
                ))}
              </ul>
            </section>
          ) : null}

          {artifact.script ? (
            <section className="wb-script-section">
              <h4>{t("blenderScriptCode")}</h4>
              {/* A <pre>, matching `.wb-pre`. React escapes the interpolated
                  text, so no markup in the generated Python reaches the DOM as
                  elements. */}
              <pre className="wb-pre" id="blender-script-code">
                {artifact.script}
              </pre>
            </section>
          ) : null}
        </>
      ) : null}
    </section>
  );
}
