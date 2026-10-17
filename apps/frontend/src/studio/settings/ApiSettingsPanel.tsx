import { useCallback, useEffect, useState } from "react";

import {
  deleteLlmSettings,
  getLlmSettings,
  putLlmSettings,
  testLlmSettings
} from "../../shared/api";
import type { LlmApiSettings } from "../../shared/types";
import type { Translator } from "../../shared/i18n";

/**
 * The LLM connection form: what provider the run talks to, whether it is on,
 * and whether the key on file actually works.
 *
 * Moved out of `StudioShell.tsx` because it meets the split criteria in
 * `docs/ui/architecture.md` §5 on three counts -- over 50 lines, its own
 * `api-*` class prefix, and 27 dedicated i18n keys. Behaviour is unchanged,
 * including that it loads its settings on mount rather than when the panel is
 * first shown.
 */
export function ApiSettingsPanel({ t }: { t: Translator }) {
  const [settings, setSettings] = useState<LlmApiSettings | null>(null);
  const [enabled, setEnabled] = useState(false);
  const [provider, setProvider] = useState("anthropic");
  const [baseUrl, setBaseUrl] = useState("");
  const [model, setModel] = useState("");
  const [apiKey, setApiKey] = useState("");
  const [timeoutSeconds, setTimeoutSeconds] = useState(60);
  const [busy, setBusy] = useState(false);
  const [summary, setSummary] = useState("");
  const [failed, setFailed] = useState(false);

  const apply = useCallback((payload: LlmApiSettings) => {
    setSettings(payload);
    setEnabled(Boolean(payload.enabled));
    setProvider(payload.provider || "anthropic");
    setBaseUrl(payload.base_url || "");
    setModel(payload.model || "");
    // The backend only ever returns a masked key, so never echo it into the field.
    setApiKey("");
    setTimeoutSeconds(Math.round(payload.timeout_seconds ?? 60));
  }, []);

  const load = useCallback(async () => {
    setBusy(true);
    try {
      apply(await getLlmSettings());
      setFailed(false);
    } catch (error) {
      setSummary(`${t("apiLoadFailed")} ${error}`);
      setFailed(true);
    } finally {
      setBusy(false);
    }
  }, [apply, t]);

  useEffect(() => {
    void load();
  }, [load]);

  const collect = () => ({
    enabled,
    provider,
    base_url: baseUrl,
    model,
    api_key: apiKey,
    timeout_seconds: timeoutSeconds
  });

  const save = async (testAfter: boolean) => {
    setBusy(true);
    try {
      const payload = await putLlmSettings(collect());
      if (payload.error) {
        setSummary(`${t("apiSaveFailed")} ${payload.error}`);
        setFailed(true);
        return;
      }
      apply(payload);
      setSummary(t("apiSaveOk"));
      setFailed(false);
      if (testAfter) await runTest();
    } catch (error) {
      setSummary(`${t("apiSaveFailed")} ${error}`);
      setFailed(true);
    } finally {
      setBusy(false);
    }
  };

  const runTest = async () => {
    setBusy(true);
    setSummary(t("apiTesting"));
    try {
      const payload = await testLlmSettings(collect());
      if (payload.settings) apply(payload.settings);
      const message = payload.detail_key ? t(payload.detail_key, { ms: payload.latency_ms ?? 0, detail: payload.detail }) : payload.detail || "";
      setSummary(payload.ok ? `${t("apiStateReady")} · ${message}` : message || t("apiSaveFailed"));
      setFailed(!payload.ok);
    } catch (error) {
      setSummary(`${t("apiSaveFailed")} ${error}`);
      setFailed(true);
    } finally {
      setBusy(false);
    }
  };

  const clear = async () => {
    setBusy(true);
    try {
      apply(await deleteLlmSettings());
      setSummary(t("apiClearOk"));
      setFailed(false);
    } catch (error) {
      setSummary(`${t("apiSaveFailed")} ${error}`);
      setFailed(true);
    } finally {
      setBusy(false);
    }
  };

  const keyLabel = settings?.api_key_configured
    ? `${settings.api_key_masked || ""} (${settings.api_key_source === "environment" ? t("apiKeyEnv") : t("apiKeyStored")})`
    : t("apiKeyNone");

  return (
    <>
      <div className="api-header">
        <div>
          <h3>{t("apiTitle")}</h3>
          <p>{t("apiHint")}</p>
        </div>
        <button className="primary-action" type="button" id="api-refresh" onClick={() => void load()} disabled={busy}>
          {t("apiRefresh")}
        </button>
      </div>

      <form
        className="api-form"
        id="api-form"
        autoComplete="off"
        onSubmit={(event) => {
          event.preventDefault();
          void save(false);
        }}
      >
        <label className="api-toggle">
          <input type="checkbox" id="api-enabled" checked={enabled} onChange={(event) => setEnabled(event.target.checked)} />
          <span>{t("apiEnabled")}</span>
        </label>

        <div className="api-field">
          <label htmlFor="api-provider">{t("apiProvider")}</label>
          <select id="api-provider" value={provider} onChange={(event) => setProvider(event.target.value)}>
            <option value="anthropic">anthropic</option>
            <option value="openai_compatible">openai_compatible</option>
            <option value="openai_responses">openai_responses (GPT-6 Astra)</option>
          </select>
        </div>

        <div className="api-field">
          <label htmlFor="api-base-url">{t("apiBaseUrl")}</label>
          <input id="api-base-url" type="text" spellCheck={false} placeholder="https://api.anthropic.com" value={baseUrl} onChange={(event) => setBaseUrl(event.target.value)} />
        </div>

        <div className="api-field">
          <label htmlFor="api-model">{t("apiModel")}</label>
          <input id="api-model" type="text" spellCheck={false} placeholder="claude-opus-4-8" value={model} onChange={(event) => setModel(event.target.value)} />
        </div>

        <div className="api-field">
          <label htmlFor="api-key">{t("apiKey")}</label>
          <input id="api-key" type="password" autoComplete="off" spellCheck={false} placeholder={t("apiKeyPlaceholder")} value={apiKey} onChange={(event) => setApiKey(event.target.value)} />
        </div>

        <div className="api-field">
          <label htmlFor="api-timeout">{t("apiTimeout")}</label>
          <input id="api-timeout" type="number" min={5} max={600} step={1} value={timeoutSeconds} onChange={(event) => setTimeoutSeconds(Number(event.target.value))} />
        </div>

        <div className="api-actions">
          <button className="primary-action" type="button" id="api-save" disabled={busy} onClick={() => void save(false)}>
            {t("apiSave")}
          </button>
          <button className="primary-action" type="button" id="api-test" disabled={busy} onClick={() => void runTest()}>
            {t("apiTest")}
          </button>
          <button className="primary-action" type="button" id="api-clear" disabled={busy} onClick={() => void clear()}>
            {t("apiClear")}
          </button>
        </div>
      </form>

      <p className="api-summary" id="api-summary" data-state={failed ? "error" : "ok"}>
        {summary || (settings ? (settings.ready ? t("apiStateReady") : t("apiStateDisabled")) : t("apiStateIdle"))}
      </p>

      <div className="api-state-grid" id="api-state-grid" aria-live="polite">
        <article className="api-state-card">
          <span>{t("apiStatusReady")}</span>
          <strong>{settings?.ready ? t("apiStateReady") : t("apiStateDisabled")}</strong>
        </article>
        <article className="api-state-card">
          <span>{t("apiStatusKey")}</span>
          <code>{keyLabel}</code>
        </article>
        <article className="api-state-card">
          <span>{t("apiStatusEndpoint")}</span>
          <code>{settings?.base_url || "-"}</code>
        </article>
        <article className="api-state-card">
          <span>{t("apiConfigPath")}</span>
          <code>{settings?.config_path || "-"}</code>
        </article>
      </div>
    </>
  );
}
