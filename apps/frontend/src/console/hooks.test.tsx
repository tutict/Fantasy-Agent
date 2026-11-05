import { cleanup, renderHook, waitFor } from "@testing-library/react";
import { useMemo } from "react";
import { afterEach, describe, expect, it } from "vitest";
import { consoleI18n, makeTranslator } from "../shared/i18n";
import type { Locale } from "../shared/types";
import { usePlanningHandoff } from "./hooks";

afterEach(() => { cleanup(); localStorage.clear(); });
const addActivity = () => undefined;
const setStatus = () => undefined;

describe("localized planning handoff", () => {
  it("preserves an English handoff name in the English interface", async () => {
    localStorage.setItem("fantasy-agent-planning-handoff", JSON.stringify({ title: "QA prototype", plan: { gameplay_spec: { title: "Rooftop Parkour Chase Across Neon" } } }));
    const t = makeTranslator("en", consoleI18n);
    const { result } = renderHook(() => usePlanningHandoff({ active: true, locale: "en", t, addActivity, setStatus }));
    await waitFor(() => expect(result.current.currentHandoff).not.toBeNull());
    expect(result.current.renderHandoffTitle(result.current.currentHandoff)).toBe("QA prototype");
  });

  it("uses the current locale instead of the title saved under another language", async () => {
    localStorage.setItem("fantasy-agent-planning-handoff", JSON.stringify({
      title: "Rooftop Parkour Chase Across Neon",
      plan: { gameplay_spec: { title: "Rooftop Parkour Chase Across Neon", i18n: { field_translations: { title: { "zh-CN": "屋顶跑酷追逐" } } } } }
    }));
    const { result, rerender } = renderHook(({ locale }: { locale: Locale }) => {
      const t = useMemo(() => makeTranslator(locale, consoleI18n), [locale]);
      return usePlanningHandoff({ active: true, locale, t, addActivity, setStatus });
    }, { initialProps: { locale: "zh-CN" as Locale } });
    await waitFor(() => expect(result.current.currentHandoff).not.toBeNull());
    expect(result.current.renderHandoffTitle(result.current.currentHandoff)).toBe("屋顶跑酷追逐");
    rerender({ locale: "en" });
    expect(result.current.renderHandoffTitle(result.current.currentHandoff)).toBe("Rooftop Parkour Chase Across Neon");
    rerender({ locale: "zh-CN" });
    expect(result.current.renderHandoffTitle(result.current.currentHandoff)).toBe("屋顶跑酷追逐");
  });
});
