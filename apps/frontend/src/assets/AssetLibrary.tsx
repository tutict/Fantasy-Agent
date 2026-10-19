import { useCallback, useEffect, useMemo, useState } from "react";

import {
  AssetEntryCard,
  AssetsEmptyState,
  GeneratedAssetCard,
  GeneratedEmptyState,
  LicensePresets,
  type AssetKind
} from "./parts";
import { getAssetLibrary, ingestAsset, removeAsset } from "../shared/api";
import type { Translator } from "../shared/i18n";
import { Button, ConfirmDialog } from "../shared/ui/primitives";
import type { AssetLibraryEntry, AssetLibraryOverview } from "../shared/types";
import "../styles/assets.css";

/**
 * The asset library panel: what this project can build with.
 *
 * Two kinds of record, one screen:
 *
 * - **Ingested** -- open-source files the user copied in from their own
 *   machine, with the provenance (license, author, source URL, sha256) that
 *   makes them usable in a jam without a legal archaeology dig later.
 * - **Generated** -- the Creative Review decisions, read from the same
 *   manifest the ingest gate reads. There is deliberately no second copy of
 *   that list; the manifest is the record.
 *
 * Ingestion is a write with no two-step confirmation, unlike engine
 * execution: it copies one file the user explicitly named, launches no
 * process, and burns no engine time. Deletion does ask, because it destroys
 * the library's copy -- and the dialog says out loud that the user's original
 * download is not what gets deleted.
 */

const KIND_FILTERS: Array<[AssetKind | "all", string]> = [
  ["all", "assetsFilterAll"],
  ["mesh", "assetsKindMesh"],
  ["texture", "assetsKindTexture"],
  ["audio", "assetsKindAudio"],
  ["other", "assetsKindOther"]
];

const STATUS_FILTERS: Array<[string, string]> = [
  ["all", "assetsFilterAll"],
  ["approved", "assetsStatusApproved"],
  ["needs_revision", "assetsStatusNeedsRevision"],
  ["rejected", "assetsStatusRejected"],
  ["pending_user_review", "assetsStatusPending"]
];

export function AssetLibrary({ t }: { t: Translator }) {
  const [overview, setOverview] = useState<AssetLibraryOverview | null>(null);
  const [busy, setBusy] = useState(false);
  const [failure, setFailure] = useState("");
  const [notice, setNotice] = useState("");

  const [name, setName] = useState("");
  const [sourcePath, setSourcePath] = useState("");
  const [license, setLicense] = useState("CC0");
  const [author, setAuthor] = useState("");
  const [sourceUrl, setSourceUrl] = useState("");
  const [notes, setNotes] = useState("");
  const [tags, setTags] = useState("");

  const [kindFilter, setKindFilter] = useState<AssetKind | "all">("all");
  const [statusFilter, setStatusFilter] = useState("all");
  const [pendingRemoval, setPendingRemoval] = useState<AssetLibraryEntry | null>(null);

  const load = useCallback(async () => {
    setBusy(true);
    setFailure("");
    try {
      setOverview(await getAssetLibrary());
    } catch (error) {
      // The last good overview stays put behind the failure. Clearing it would
      // trade a stale list for an empty one, and "nothing is in the library" is
      // exactly the claim a failed read cannot make.
      setFailure(`${t("assetsLoadFailed")} ${error}`);
    } finally {
      setBusy(false);
    }
  }, [t]);

  useEffect(() => {
    void load();
  }, [load]);

  const entries = overview?.entries ?? [];
  const generated = overview?.generated ?? [];
  const visibleEntries = useMemo(
    () => (kindFilter === "all" ? entries : entries.filter((entry) => entry.kind === kindFilter)),
    [entries, kindFilter]
  );
  const visibleGenerated = useMemo(
    () =>
      statusFilter === "all"
        ? generated
        : generated.filter((record) => record.status === statusFilter),
    [generated, statusFilter]
  );

  const submit = async () => {
    if (!name.trim() || !sourcePath.trim()) {
      setFailure(t("assetsIngestFailed"));
      return;
    }
    setBusy(true);
    setFailure("");
    setNotice("");
    try {
      const response = await ingestAsset({
        name: name.trim(),
        source_path: sourcePath.trim(),
        license: license.trim(),
        author: author.trim(),
        source_url: sourceUrl.trim(),
        notes: notes.trim(),
        tags: tags
          .split(",")
          .map((tag) => tag.trim())
          .filter(Boolean)
      });
      setName("");
      setSourcePath("");
      setAuthor("");
      setSourceUrl("");
      setNotes("");
      setTags("");
      setNotice(t("assetsIngested", { name: response.entry.name }));
      await load();
    } catch (error) {
      setFailure(`${t("assetsIngestFailed")} ${error}`);
    } finally {
      setBusy(false);
    }
  };

  const confirmRemoval = async () => {
    const entry = pendingRemoval;
    if (!entry) return;
    setPendingRemoval(null);
    setBusy(true);
    setFailure("");
    setNotice("");
    try {
      await removeAsset(entry.id);
      setNotice(t("assetsRemoved", { name: entry.name }));
      await load();
    } catch (error) {
      setFailure(`${t("assetsRemoveFailed")} ${error}`);
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
      <div className="as-header">
        <div>
          <h3>{t("assetsTitle")}</h3>
          <p>{t("assetsHint")}</p>
        </div>
        <Button className="as-refresh" type="button" id="as-refresh" onClick={() => void load()} disabled={busy}>
          {t("assetsRefresh")}
        </Button>
      </div>

      <p className="as-summary" id="as-summary" data-state={failure ? "error" : "ok"}>
        {/* A count is a claim about what the library holds, so it waits for a
            read that actually came back: zero during the load would be the
            same lie an empty state tells after a failure. */}
        {failure || notice || (overview ? t("assetsCount", { library: entries.length, generated: generated.length }) : "")}
      </p>
      {overview ? (
        <p className="as-path-note">
          {t("assetsLibraryPath")}: <code>{overview.library_path}</code>
        </p>
      ) : null}

      <form
        className="as-form"
        id="as-form"
        autoComplete="off"
        onSubmit={(event) => {
          event.preventDefault();
          void submit();
        }}
      >
        <h4>{t("assetsIngestTitle")}</h4>
        <p>{t("assetsIngestHint")}</p>
        <div className="as-field">
          <label htmlFor="as-name">{t("assetsName")}</label>
          <input
            id="as-name"
            type="text"
            value={name}
            placeholder={t("assetsNamePlaceholder")}
            onChange={(event) => setName(event.target.value)}
          />
        </div>
        <div className="as-field">
          <label htmlFor="as-source-path">{t("assetsSourcePath")}</label>
          <input
            id="as-source-path"
            type="text"
            value={sourcePath}
            placeholder={t("assetsSourcePathPlaceholder")}
            onChange={(event) => setSourcePath(event.target.value)}
          />
        </div>
        <div className="as-field">
          <label htmlFor="as-license">{t("assetsLicense")}</label>
          <input
            id="as-license"
            type="text"
            value={license}
            onChange={(event) => setLicense(event.target.value)}
          />
          <LicensePresets t={t} onPick={setLicense} />
        </div>
        <div className="as-field">
          <label htmlFor="as-author">{t("assetsAuthor")}</label>
          <input
            id="as-author"
            type="text"
            value={author}
            placeholder={t("assetsAuthorPlaceholder")}
            onChange={(event) => setAuthor(event.target.value)}
          />
        </div>
        <div className="as-field">
          <label htmlFor="as-source-url">{t("assetsSourceUrl")}</label>
          <input
            id="as-source-url"
            type="text"
            value={sourceUrl}
            placeholder={t("assetsSourceUrlPlaceholder")}
            onChange={(event) => setSourceUrl(event.target.value)}
          />
        </div>
        <div className="as-field">
          <label htmlFor="as-tags">{t("assetsTags")}</label>
          <input
            id="as-tags"
            type="text"
            value={tags}
            placeholder={t("assetsTagsPlaceholder")}
            onChange={(event) => setTags(event.target.value)}
          />
          <small>{t("assetsTagsHint")}</small>
        </div>
        <div className="as-field">
          <label htmlFor="as-notes">{t("assetsNotes")}</label>
          <textarea id="as-notes" rows={2} value={notes} onChange={(event) => setNotes(event.target.value)} />
        </div>
        <div className="as-actions">
          <Button tone="primary" type="submit" id="as-submit" disabled={busy}>
            {busy ? t("assetsIngesting") : t("assetsSubmit")}
          </Button>
        </div>
      </form>

      <section className="as-section" id="as-library">
        <div className="as-section-head">
          <h4>{t("assetsLibraryTitle")}</h4>
          <div className="as-filters" role="group" aria-label={t("assetsFilterKind")}>
            {KIND_FILTERS.map(([value, labelKey]) => (
              <button
                className={`as-filter ${kindFilter === value ? "active" : ""}`}
                type="button"
                key={value}
                onClick={() => setKindFilter(value)}
              >
                {t(labelKey)}
              </button>
            ))}
          </div>
        </div>
        {visibleEntries.length ? (
          <div className="as-entries">
            {visibleEntries.map((entry) => (
              <AssetEntryCard
                entry={entry}
                t={t}
                key={entry.id}
                onRemove={(target) => setPendingRemoval(target)}
              />
            ))}
          </div>
        ) : overview ? (
          <AssetsEmptyState t={t} />
        ) : null}
      </section>

      <section className="as-section" id="as-generated">
        <div className="as-section-head">
          <h4>{t("assetsGeneratedTitle")}</h4>
          <div className="as-filters" role="group" aria-label={t("assetsFilterStatus")}>
            {STATUS_FILTERS.map(([value, labelKey]) => (
              <button
                className={`as-filter ${statusFilter === value ? "active" : ""}`}
                type="button"
                key={value}
                onClick={() => setStatusFilter(value)}
              >
                {t(labelKey)}
              </button>
            ))}
          </div>
        </div>
        <p className="as-section-hint">{t("assetsGeneratedHint")}</p>
        {visibleGenerated.length ? (
          <div className="as-entries">
            {visibleGenerated.map((record) => (
              <GeneratedAssetCard record={record} t={t} key={`${record.asset_id}-${record.status}`} />
            ))}
          </div>
        ) : overview ? (
          <GeneratedEmptyState t={t} />
        ) : null}
      </section>

      <ConfirmDialog
        open={pendingRemoval !== null}
        title={t("assetsRemoveConfirmTitle")}
        body={t("assetsRemoveConfirmBody")}
        confirmLabel={t("assetsRemoveConfirmYes")}
        cancelLabel={t("assetsRemoveConfirmNo")}
        onConfirm={() => void confirmRemoval()}
        onCancel={() => setPendingRemoval(null)}
      />
    </>
  );
}
