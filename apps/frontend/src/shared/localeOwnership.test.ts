import { describe, expect, it } from "vitest";
import { readdirSync, readFileSync } from "node:fs";
import { dirname, join, relative, resolve } from "node:path";
import { fileURLToPath } from "node:url";

/**
 * Guard for "one owner per global", the F4 half of what `tokenOwnership.test.ts`
 * does for CSS custom properties.
 *
 * The console, the workbench and the shell were three documents. Each could own
 * a locale, a theme and a document title without anyone noticing, because
 * "the document" meant three different things. The views are inline now, in one
 * document, so every one of those has to have exactly one writer -- otherwise
 * the winner is whoever's effect runs last, which is decided by mount order.
 *
 * The scan reports the file that owns each global and fails on a second one.
 * Sources are read from disk; see `tokenOwnership.test.ts` for why `?raw` is not
 * used here.
 */
const SRC_DIR = resolve(dirname(fileURLToPath(import.meta.url)), "..");

const LOCALE_THEME_FILE = "shared/localeTheme.tsx";
const STORAGE_FILE = "shared/storage.ts";
const SHELL_FILE = "studio/StudioShell.tsx";
const PLAN_MODEL_FILE = "shared/planModel.ts";
const ENTRY_FILE = "main.tsx";

function sourceFiles(): Array<{ path: string; text: string }> {
  const found: Array<{ path: string; text: string }> = [];

  const walk = (dir: string) => {
    for (const entry of readdirSync(dir, { withFileTypes: true })) {
      const full = join(dir, entry.name);
      if (entry.isDirectory()) {
        walk(full);
        continue;
      }
      if (!/\.tsx?$/.test(entry.name) || /\.test\.tsx?$/.test(entry.name)) continue;
      found.push({ path: relative(SRC_DIR, full).split("\\").join("/"), text: readFileSync(full, "utf8") });
    }
  };

  walk(SRC_DIR);
  return found.sort((a, b) => a.path.localeCompare(b.path));
}

const FILES = sourceFiles();

/** Files whose text matches, sorted so the expectation does not depend on walk order. */
function owners(pattern: RegExp): string[] {
  return FILES.filter((file) => pattern.test(file.text))
    .map((file) => file.path)
    .sort();
}

describe("every document-level global has exactly one writer", () => {
  it("scans the whole source tree", () => {
    // Floor: a wrong root would make every assertion below pass on an empty set.
    // The count is deliberately well under the real one -- what actually pins the
    // root is the required-path check below.
    expect(FILES.length).toBeGreaterThan(10);
    const paths = FILES.map((file) => file.path);
    for (const required of [LOCALE_THEME_FILE, SHELL_FILE, "console/FlowConsole.tsx", "workbench/PlanningWorkbench.tsx"]) {
      expect(paths).toContain(required);
    }
  });

  it("writes the document language and theme only from the provider", () => {
    // Matched as an assignment, not as the member expression: the provider's own
    // docstring names `document.documentElement.lang` while explaining what the
    // three old documents each did, so a bare-name scan would report prose as a
    // writer. The reverse is worse -- a name-only scan also stays green with the
    // assignment deleted, which is how the python-side copy of this check proved
    // vacuous under mutation.
    expect(owners(/documentElement\.lang\s*=/)).toEqual([LOCALE_THEME_FILE]);
    expect(owners(/documentElement\.dataset\.theme\s*=/)).toEqual([LOCALE_THEME_FILE]);
  });

  it("reads the locale storage key only from the provider", () => {
    // `storage.ts` is where the key is defined; nobody else may know it.
    expect(owners(/STUDIO_LOCALE_KEY/)).toEqual([LOCALE_THEME_FILE, STORAGE_FILE].sort());
    expect(owners(/\binitialLocale\(/)).toEqual([LOCALE_THEME_FILE, STORAGE_FILE].sort());
    expect(owners(/\binitialTheme\(/)).toEqual([LOCALE_THEME_FILE, STORAGE_FILE].sort());
  });

  it("sets the document title only from the shell", () => {
    // Three views each setting the title was fine across three documents and is
    // a race in one. The shell owns it now.
    expect(owners(/document\.title\s*=/)).toEqual([SHELL_FILE]);
  });

  it("mounts the provider at the one entry point", () => {
    // Exactly one, and it is the entry. A view that wrapped itself would own a
    // second locale and write the document element with it -- the old shape,
    // rebuilt inside one document, where it is now a race rather than a
    // harmless coincidence. The reverse also has to fail loudly: an entry point
    // that stopped wrapping would take the whole app down at `useLocaleTheme`.
    //
    // The provider's own module is excluded rather than allowed by name: it
    // names itself in the error it throws, which is a message and not a mount
    // point. Everything else is expected to be absent from this list, so a view
    // that grows a provider is reported instead of absorbed.
    const mountPoints = owners(/<LocaleThemeProvider>/).filter((path) => path !== LOCALE_THEME_FILE);
    expect(mountPoints).toEqual([ENTRY_FILE]);
  });

  it("answers the engine version from one implementation", () => {
    expect(owners(/function selectedEngineVersion/)).toEqual([PLAN_MODEL_FILE]);
    // The shell used to call a local no-argument version. A no-argument call
    // anywhere means that second implementation is back.
    expect(owners(/selectedEngineVersion\(\)/)).toEqual([]);
  });
});

describe("the query parameters that only existed for the frames are gone", () => {
  it("does not pass locale or theme through a query string", () => {
    // Two sources used to build `?locale=..&theme=..`: the shell, for each
    // iframe's `src`, and the console, when it opened the workbench in a new tab.
    // Both read the shared key now. `initialLocale`/`initialTheme` still honour
    // those parameters when a person types them, which is why what is checked is
    // the construction of such a string rather than the reading of one.
    expect(owners(/new URLSearchParams\(\{[^}]*\b(locale|theme)\b/)).toEqual([]);
  });

  it("does not read or send an embed flag", () => {
    // The workbench was the only view that read it, and only to trim padding;
    // the console never read it at all.
    expect(owners(/["'`]embed["'`]|embed=1|\bembed:\s*["']1["']/)).toEqual([]);
  });

  it("has no iframe left in the shell", () => {
    const shell = FILES.find((file) => file.path === SHELL_FILE);
    expect(shell, "StudioShell.tsx must exist").toBeTruthy();
    expect(shell?.text).not.toContain("<iframe");
  });
});
