import { useCallback, useState } from "react";

import { getToolCatalog } from "../../shared/api";
import type { Translator } from "../../shared/i18n";
import type { ToolCatalog } from "../../shared/types";

/**
 * The tool list an agent is actually offered, with the tier the gate enforces.
 *
 * The Agent panel used to show only what a run *did* (calls, refusals). A run
 * that made no calls looked the same whether the model declined to act or the
 * tools were never available, and nothing showed which of the offered tools
 * needed a grant before they would do anything.
 *
 * Collapsed by default, and loaded only when opened: the catalog is 20 rows and
 * most visits to this panel are to type a goal and press Run. Fetching it
 * eagerly would spend a request on a section nobody opened.
 *
 * Moved out of `StudioShell.tsx` under the `docs/ui/architecture.md` §5
 * criteria -- over 50 lines, 14 dedicated i18n keys, and referenced by its own
 * test file. Exported for that test: it is still only mounted from the Agent
 * panel, and mounting the whole shell to reach it would drag in every other
 * panel's network calls along with it.
 */
export function ToolCatalogPanel({ t }: { t: Translator }) {
  const [open, setOpen] = useState(false);
  const [catalog, setCatalog] = useState<ToolCatalog | null>(null);
  const [busy, setBusy] = useState(false);
  const [failure, setFailure] = useState("");

  const load = useCallback(async () => {
    setBusy(true);
    try {
      setCatalog(await getToolCatalog());
      setFailure("");
    } catch (error) {
      setCatalog(null);
      setFailure(`${t("toolsLoadFailed")} ${error}`);
    } finally {
      setBusy(false);
    }
  }, [t]);

  const toggle = () => {
    const next = !open;
    setOpen(next);
    if (next && !catalog && !busy) void load();
  };

  const tools = catalog?.tools || [];
  const counts = catalog?.permission_counts || {};
  const unimplemented = catalog?.declared_without_implementation || [];
  // Only the engine half derives its tier from MCP annotations; separating the
  // two lists keeps "these four planning tools are always read-only" from
  // reading as a claim about the bridges.
  const planning = tools.filter((tool) => tool.source === "planning");
  const engine = tools.filter((tool) => tool.source !== "planning");

  const renderRow = (tool: (typeof tools)[number]) => (
    <article className="tool-row" data-permission={tool.permission} key={tool.name}>
      <div className="tool-row-top">
        <code>{tool.name}</code>
        <span className="tool-tier">{tool.permission}</span>
      </div>
      {tool.server ? <p className="tool-row-server">{tool.server}</p> : null}
      {tool.description ? <p className="tool-row-desc">{tool.description}</p> : null}
      {tool.confirm_field ? (
        <p className="tool-row-flag">
          {t("toolConfirmField")}: <code>{tool.confirm_field}</code>
        </p>
      ) : null}
      {tool.plan_key ? (
        <p className="tool-row-flag">
          {t("toolPlanKey")}: <code>{tool.plan_key}</code>
        </p>
      ) : null}
      {tool.hidden_args?.length ? (
        <p className="tool-row-flag">
          {t("toolHiddenArgs")}: <code>{tool.hidden_args.join(", ")}</code>
        </p>
      ) : null}
      {tool.executable_args?.length ? (
        <p className="tool-row-flag tool-row-flag-danger">
          {/* Named separately from hidden_args because these are also
              overwritten on every call -- a model that sends one is ignored,
              not trusted. */}
          {t("toolExecutableArgs")}: <code>{tool.executable_args.join(", ")}</code>
        </p>
      ) : null}
    </article>
  );

  return (
    <section className="tool-catalog" id="tool-catalog">
      <header className="tool-catalog-head">
        <div>
          <h3>{t("toolsTitle")}</h3>
          <p>{t("toolsHint")}</p>
        </div>
        <button className="primary-action" type="button" id="tool-catalog-toggle" onClick={toggle}>
          {open ? t("toolsHide") : t("toolsShow")}
        </button>
      </header>

      {failure ? (
        <p className="agent-note agent-note-danger" id="tool-catalog-error">
          {failure}
        </p>
      ) : null}

      {open ? (
        <>
          <p className="tool-catalog-summary" id="tool-catalog-summary">
            {busy
              ? t("toolsLoading")
              : t("toolsSummary", {
                  total: tools.length,
                  readOnly: counts.read_only ?? 0,
                  write: counts.write ?? 0,
                  execute: counts.execute ?? 0
                })}
          </p>

          <div className="tool-catalog-group">
            <h4>{t("toolsPlanningGroup")}</h4>
            {planning.map(renderRow)}
          </div>

          <div className="tool-catalog-group">
            <h4>{t("toolsEngineGroup")}</h4>
            {engine.map(renderRow)}
          </div>

          {unimplemented.length ? (
            <p className="tool-catalog-gap" id="tool-catalog-gap">
              {t("toolsDeclaredOnly")}: <code>{unimplemented.join(", ")}</code>
            </p>
          ) : null}
        </>
      ) : null}
    </section>
  );
}
