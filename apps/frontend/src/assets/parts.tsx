import type { Translator } from "../shared/i18n";
import { Button, EmptyState, StatusBadge } from "../shared/ui/primitives";
import type { AssetLibraryEntry, GeneratedAssetRecord } from "../shared/types";

/**
 * The asset library's stateless pieces, in one file because none of them has
 * state, async, or route knowledge -- the same reason `FlowConsole.parts.tsx`
 * exists. `AssetLibrary.tsx` owns the fetch, the form, and the filters.
 *
 * Exported because `AssetLibrary.test.tsx` renders them directly; a test that
 * only mounted the shell would have to stub the whole fetch stack to reach a
 * single badge.
 *
 * Buttons, badges and empty states are the shared primitives
 * (`shared/ui/primitives.tsx`) on purpose: this panel gets the same focus
 * ring, the same status palette and the same disabled semantics as every
 * other view for free, and the status colours stay the seven mutually
 * exclusive ones `visualSystem.test.ts` pins.
 */

export type AssetKind = AssetLibraryEntry["kind"];

const LICENSE_PRESETS = ["CC0", "CC-BY", "CC-BY-SA", "MIT"];

/** Presets only fill the field; the field itself stays free text. */
export function LicensePresets({
  t,
  onPick
}: {
  t: Translator;
  onPick: (license: string) => void;
}) {
  return (
    <div className="as-license-presets">
      {LICENSE_PRESETS.map((preset) => (
        <Button
          className="as-license-preset"
          type="button"
          key={preset}
          onClick={() => onPick(preset)}
        >
          {t("assetsLicensePreset", { license: preset })}
        </Button>
      ))}
    </div>
  );
}

export function formatBytes(size: number): string {
  if (size < 1024) return `${size} B`;
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`;
  return `${(size / (1024 * 1024)).toFixed(1)} MB`;
}

/** The digest is 64 hex; twelve of them identify the file in a list. */
export function shortSha(sha256: string): string {
  return sha256.slice(0, 12);
}

/**
 * Literal `t(...)` calls, not a composed key: the i18n guard reads source
 * text, and `"assetsStatus" + status` would make every status key look
 * uncalled -- the panel would then render raw key names with every test
 * green.
 */
export function statusLabelKey(status: string): string {
  if (status === "approved") return "assetsStatusApproved";
  if (status === "needs_revision") return "assetsStatusNeedsRevision";
  if (status === "rejected") return "assetsStatusRejected";
  if (status === "pending_user_review") return "assetsStatusPending";
  return "assetsStatusUnknown";
}

export function kindLabelKey(kind: AssetKind): string {
  if (kind === "mesh") return "assetsKindMesh";
  if (kind === "texture") return "assetsKindTexture";
  if (kind === "audio") return "assetsKindAudio";
  return "assetsKindOther";
}

export function AssetEntryCard({
  entry,
  t,
  onRemove
}: {
  entry: AssetLibraryEntry;
  t: Translator;
  onRemove: (entry: AssetLibraryEntry) => void;
}) {
  return (
    <article className="as-entry" data-kind={entry.kind} id={`as-entry-${entry.id}`}>
      <div className="as-entry-top">
        <strong>{entry.name}</strong>
        <span className="as-badge">{t(kindLabelKey(entry.kind))}</span>
      </div>
      <dl className="as-entry-facts">
        <dt>{t("assetsSha")}</dt>
        <dd>
          <code title={entry.sha256}>{shortSha(entry.sha256)}</code>
        </dd>
        <dt>{t("assetsSize")}</dt>
        <dd>{formatBytes(entry.size_bytes)}</dd>
        <dt>{t("assetsLicense")}</dt>
        <dd>{entry.license || "-"}</dd>
        <dt>{t("assetsAuthor")}</dt>
        <dd>{entry.author || "-"}</dd>
        <dt>{t("assetsOriginalName")}</dt>
        <dd>{entry.original_name || "-"}</dd>
        <dt>{t("assetsPath")}</dt>
        <dd>
          <code>{entry.path}</code>
        </dd>
        {entry.source_url ? (
          <>
            <dt>{t("assetsSourceUrl")}</dt>
            <dd>
              {/* A link the user recorded, not something the product fetched:
                  it opens in their browser and nothing in the app ever
                  requests it. */}
              <a href={entry.source_url} target="_blank" rel="noreferrer">
                {entry.source_url}
              </a>
            </dd>
          </>
        ) : null}
        {entry.tags.length ? (
          <>
            <dt>{t("assetsTags")}</dt>
            <dd>{entry.tags.join(", ")}</dd>
          </>
        ) : null}
        {entry.notes ? (
          <>
            <dt>{t("assetsNotes")}</dt>
            <dd>{entry.notes}</dd>
          </>
        ) : null}
        <dt>{t("assetsIngestedAt")}</dt>
        <dd>{entry.ingested_at || "-"}</dd>
      </dl>
      <div className="as-entry-actions">
        <Button
          tone="danger"
          type="button"
          id={`as-remove-${entry.id}`}
          onClick={() => onRemove(entry)}
        >
          {t("assetsRemove")}
        </Button>
      </div>
    </article>
  );
}

export function GeneratedAssetCard({
  record,
  t
}: {
  record: GeneratedAssetRecord;
  t: Translator;
}) {
  return (
    <article className="as-entry as-entry-generated" data-status={record.status}>
      <div className="as-entry-top">
        <strong>{record.asset_id}</strong>
        <StatusBadge status={record.status} label={t(statusLabelKey(record.status))} />
      </div>
      <dl className="as-entry-facts">
        <dt>{t("assetsSourceLabel")}</dt>
        <dd>
          {record.source === "blender" ? "Blender" : "ComfyUI"} · {record.gameplay_role || "-"}
        </dd>
        <dt>{t("assetsPath")}</dt>
        <dd>
          <code>{record.asset_path}</code>
        </dd>
        {record.sha256 ? (
          <>
            <dt>{t("assetsSha")}</dt>
            <dd>
              <code title={record.sha256}>{shortSha(record.sha256)}</code>
            </dd>
          </>
        ) : null}
      </dl>
    </article>
  );
}

export function AssetsEmptyState({ t }: { t: Translator }) {
  return <EmptyState title={t("assetsLibraryEmpty")} body={t("assetsIngestHint")} />;
}

export function GeneratedEmptyState({ t }: { t: Translator }) {
  return <EmptyState title={t("assetsGeneratedEmpty")} body={t("assetsGeneratedHint")} />;
}
