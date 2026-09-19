/**
 * The one owner of locale and theme.
 *
 * The console, the workbench and the studio shell used to be three separate
 * documents, each with its own `useState<Locale>` / `useState<Theme>` and each
 * writing `document.documentElement.lang` and `dataset.theme` for itself. Three
 * documents meant three `<html>` elements, so three writers never collided --
 * and locale drifted into three unrelated localStorage keys while a locale was
 * actually propagated across the iframe boundary by hand, through `?locale=`
 * and `?theme=` in the frame's `src`.
 *
 * The views are now rendered inline, in one document. Three writers on one
 * `<html>` means the last effect to run wins, which is a race decided by mount
 * order rather than by intent. So the state moves here, the shell and both
 * views read it from here, and only this module touches the document element.
 *
 * `useLocaleTheme` throws outside the provider rather than falling back to a
 * default. A silent default would restore the old behaviour -- two truths about
 * the locale -- and it would do so quietly, in whichever view forgot to mount
 * inside the provider.
 */

import { createContext, useContext, useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";
import { STUDIO_LOCALE_KEY, THEME_KEY, initialLocale, initialTheme } from "./storage";
import type { Locale, Theme } from "./types";

type LocaleThemeValue = {
  locale: Locale;
  theme: Theme;
  setLocale: (next: Locale) => void;
  setTheme: (next: Theme) => void;
};

const LocaleThemeContext = createContext<LocaleThemeValue | null>(null);

export function LocaleThemeProvider({ children }: { children: ReactNode }) {
  const [locale, setLocale] = useState<Locale>(() => initialLocale(STUDIO_LOCALE_KEY));
  const [theme, setTheme] = useState<Theme>(() => initialTheme());

  useEffect(() => {
    document.documentElement.lang = locale;
    localStorage.setItem(STUDIO_LOCALE_KEY, locale);
  }, [locale]);

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    localStorage.setItem(THEME_KEY, theme);
  }, [theme]);

  const value = useMemo(() => ({ locale, theme, setLocale, setTheme }), [locale, theme]);

  return <LocaleThemeContext.Provider value={value}>{children}</LocaleThemeContext.Provider>;
}

export function useLocaleTheme(): LocaleThemeValue {
  const value = useContext(LocaleThemeContext);

  if (!value) {
    throw new Error(
      "useLocaleTheme was called outside <LocaleThemeProvider>. Mount the view " +
        "inside the provider (main.tsx wraps the whole app once) instead of " +
        "keeping a second copy of the locale."
    );
  }

  return value;
}
