import type { McpService } from "../../shared/types";
import type { Translator } from "../../shared/i18n";

/**
 * One MCP service's readiness: what it is, whether the run needs it, and what
 * to do about it when it is not there.
 *
 * Moved out of `StudioShell.tsx` under the `docs/ui/architecture.md` §5
 * criteria -- it carries the `mcp-*` class prefix, which is the criterion that
 * fires regardless of length. It is under 50 lines and has no test of its own,
 * so it is the weakest of the four splits; it moved because the shell used to
 * render it in a loop -- that loop is `McpServiceGrid` below now -- and the
 * prefix is what ties its styles to `studio.css`.
 *
 * The `detail`/`next_action` fallbacks compare the translated string against
 * the key: when the dictionary has no entry, `makeTranslator` returns the key
 * itself, and showing "mcpNextAction" to an operator would be worse than
 * showing the backend's raw text.
 */
export function McpCard({ service, t }: { service: McpService; t: Translator }) {
  const state = service.status === "ready" || service.status === "degraded" ? service.status : "unavailable";
  const detail = service.detail_key ? t(service.detail_key, service.detail_args) : service.detail;
  const nextAction = service.next_action_key ? t(service.next_action_key, service.next_action_args) : service.next_action;
  return (
    <article className="mcp-status-card" data-state={state}>
      <div className="mcp-status-top">
        <div>
          <h4>{service.label}</h4>
          <p>{service.required ? t("mcpRequired") : t("mcpOptional")}</p>
        </div>
        <span className="mcp-state">{state === "ready" ? t("mcpReady") : state === "degraded" ? t("mcpDegraded") : t("mcpUnavailable")}</span>
      </div>
      <div className="mcp-target">
        <span>{t("mcpTarget")}</span>
        <code>{service.target || "-"}</code>
      </div>
      <p>{detail === service.detail_key ? service.detail : detail}</p>
      <p>
        <strong>{t("mcpNextAction")}:</strong> {nextAction === service.next_action_key ? service.next_action : nextAction}
      </p>
    </article>
  );
}

/**
 * The card list, as a component rather than an inline `.map()` in the shell.
 *
 * This exists because of what an error boundary can and cannot catch. A
 * boundary replaces the render of its *descendants*; it has no reach into the
 * component that renders it. Written as `services.map(...)` inside
 * `StudioShell`, the list's one crash surface -- `key={service.id}` against a
 * payload that promised an object and sent `null`, which every field being
 * optional does not forbid -- is evaluated in the shell's own render, above
 * every boundary in the tree, so the boundary around the grid is decorative:
 * the crash escapes and takes the shell with it.
 *
 * Moving the map one level down puts that expression inside the boundary, which
 * is the only place a boundary can help. Verified by mutation: with the map
 * back in the shell, the malformed-payload test white-screens instead of
 * showing the fallback.
 */
export function McpServiceGrid({ services, t }: { services?: McpService[]; t: Translator }) {
  return (
    <>
      {(services || []).map((service) => (
        <McpCard key={service.id} service={service} t={t} />
      ))}
    </>
  );
}
