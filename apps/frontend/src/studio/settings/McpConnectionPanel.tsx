import { useCallback, useEffect, useState } from "react";
import { makeTranslator } from "../../shared/i18n";
import { useLocaleTheme } from "../../shared/localeTheme";
import { projectI18n } from "../../shared/projectI18n";
import { useProject } from "../../shared/projectStore";
import { Button, StatusBadge } from "../../shared/ui/primitives";

interface Connection { enabled: boolean; endpoint: string; configured: boolean; recent_activity: Array<{ time: number; operation: string; status: string }> }
async function connectionRequest<T>(path: string, method = "GET"): Promise<T> {
  const response = await fetch(path, { method, cache: "no-store", headers: { Accept: "application/json" } });
  if (!response.ok) throw new Error(`HTTP ${response.status}`);
  return response.json();
}
export function McpConnectionPanel({ active }: { active: boolean }) {
  const { locale } = useLocaleTheme();
  const t = makeTranslator(locale, projectI18n);
  const project = useProject();
  const [connection, setConnection] = useState<Connection | null>(null);
  const [config, setConfig] = useState<{ toml: string; token_env_var: string; workbuddy_json: string } | null>(null);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState(false);
  const refresh = useCallback(async () => {
    try { setConnection(await connectionRequest<Connection>("/api/mcp/connection")); setError(""); }
    catch { setError(locale === "zh-CN" ? "读取失败，请检查 Studio 后重试。" : "Read failed. Check Studio and retry."); }
  }, [locale]);
  useEffect(() => { if (!active) return; void refresh(); const timer = setInterval(() => void refresh(), 3000); return () => clearInterval(timer); }, [active, refresh]);
  async function change(action: "enable" | "disable" | "rotate") {
    setBusy(true); setError("");
    try {
      const path = action === "enable" ? "/api/mcp/connection/enable" : action === "disable" ? "/api/mcp/connection/disable" : "/api/mcp/connection/rotate";
      setConnection(await connectionRequest<Connection>(path, "POST"));
      if (action === "rotate") setNotice(t("rotated"));
    } catch { setError(t("failed")); } finally { setBusy(false); }
  }
  async function copyToken() {
    setBusy(true); setError("");
    try {
      const { token } = await connectionRequest<{ token: string }>("/api/mcp/connection/token", "POST");
      await navigator.clipboard.writeText(token);
      setNotice(t("copied"));
    } catch { setError(t("copyFailed")); } finally { setBusy(false); }
  }
  const grants = project.active?.authorizations?.filter((grant) => grant.active && grant.plan_version === project.active?.plan_version) ?? [];
  const recent = connection?.recent_activity?.at(-1);
  return <div className="mcp-connection" data-testid="mcp-connection">
    <header><h3>{t("service")}</h3><p>{t("serviceHint")}</p></header>
    {error ? <p role="alert" className="ui-hint" data-status="error">{error}<Button onClick={() => void refresh()}>{t("retry")}</Button></p> : null}
    <div className="mcp-connection-row">
      <StatusBadge status={connection?.enabled ? "ready" : "blocked"} label={connection ? t(connection.enabled ? "enabled" : "disabled") : t("loading")} />
      <Button disabled={busy || !connection} onClick={() => void change(connection?.enabled ? "disable" : "enable")}>{t(connection?.enabled ? "disable" : "enable")}</Button>
    </div>
    <dl className="mcp-connection-facts">
      <div><dt>{t("recent")}</dt><dd>{recent ? `${new Date(recent.time * 1000).toLocaleString(locale)} · ${recent.operation}` : t("none")}</dd></div>
      <div><dt>{t("grants")}</dt><dd>{grants.length ? <details><summary>{t("activeGrants", { count: grants.length })}</summary><ul>{grants.map((grant) => <li key={grant.grant_id}>{t("grantRemaining", { seconds: Math.ceil(grant.remaining_seconds) })} · {t("grantScope")}: {grant.actions.map((action) => action.tool_name ?? String(action.tool ?? "")).join(", ")}</li>)}</ul></details> : t("noGrants")}</dd></div>
      <div><dt>{t("endpoint")}</dt><dd><code>{connection?.endpoint ?? "—"}</code></dd></div>
    </dl>
    <div className="mcp-connection-row"><Button disabled={busy || !connection} onClick={() => void copyToken()}>{t("copyToken")}</Button></div>
    {notice ? <p role="status" className="ui-hint">{notice}</p> : null}
    <details onToggle={(event) => { if (event.currentTarget.open && !config) void connectionRequest<{ toml: string; token_env_var: string; workbuddy_json: string }>("/api/mcp/connection/config").then(setConfig).catch(() => setError(t("failed"))); }}>
      <summary>{t("configuration")}</summary><p>{t("steps")}</p>
      {config ? <><code>{config.token_env_var}</code><pre>{config.toml}</pre>
        <h4>{t("workbuddyConfig")}</h4><p>{t("workbuddyHint")}</p><pre>{config.workbuddy_json}</pre></> : null}
      <p>{t("elicitation")}</p><p>{t("rotateHint")}</p><Button disabled={busy || !connection} onClick={() => void change("rotate")}>{t("rotate")}</Button>
    </details>
  </div>;
}
