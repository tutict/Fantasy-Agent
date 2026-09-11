import { describe, expect, it } from "vitest";

import { consoleI18n, makeTranslator, studioI18n, workbenchI18n } from "./i18n";

const DICTIONARIES = { consoleI18n, studioI18n, workbenchI18n };

/**
 * The dictionaries are hand-maintained per locale, so a key added to `en` and
 * forgotten in `zh-CN` silently shows the English string in a Chinese UI. This
 * is the guard for exactly that (it caught nothing yet -- it is here so the
 * next key addition cannot drift).
 */
describe.each(Object.entries(DICTIONARIES))("%s", (_name, dictionary) => {
  const locales = Object.keys(dictionary);

  it("ships both zh-CN and en", () => {
    expect(locales).toContain("zh-CN");
    expect(locales).toContain("en");
  });

  it("has identical key sets across locales", () => {
    const en = Object.keys(dictionary.en).sort();
    for (const locale of locales.filter((entry) => entry !== "en")) {
      expect(Object.keys(dictionary[locale as keyof typeof dictionary]).sort(), `${locale} keys`).toEqual(en);
    }
  });

  it("has no empty translations", () => {
    for (const [locale, entries] of Object.entries(dictionary)) {
      for (const [key, value] of Object.entries(entries)) {
        expect(value.trim(), `${locale}.${key}`).not.toBe("");
      }
    }
  });
});

describe("makeTranslator", () => {
  const dictionary = {
    en: { greeting: "Hello {name}", plain: "Plain" },
    "zh-CN": { greeting: "你好 {name}", plain: "朴素" }
  } as never;

  it("interpolates named arguments", () => {
    const t = makeTranslator("en", dictionary);
    expect(t("greeting", { name: "engineer" })).toBe("Hello engineer");
  });

  it("uses the locale dictionary and falls back to en for a missing key", () => {
    expect(makeTranslator("zh-CN", dictionary)("greeting", { name: "工程师" })).toBe("你好 工程师");
    expect(makeTranslator("zh-CN", { en: { only: "English" }, "zh-CN": {} } as never)("only")).toBe("English");
  });

  it("leaves unknown placeholders untouched rather than rendering 'undefined'", () => {
    const t = makeTranslator("en", dictionary);
    expect(t("greeting", {})).toBe("Hello {name}");
  });
});
