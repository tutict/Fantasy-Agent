"""Mutation check for the frontend guards -- the vitest half of the promise
`scripts/mutation_check_all_guards.py` keeps for the pytest half.

    python scripts/mutation_check_frontend_guards.py [--only SUBSTRING] [--list]

Why a second harness instead of a second backend in the first one: that script
drives ``scripts/run_tests.py`` and reads a junit report, which is a pytest
runner. The frontend guards are vitest tests and their subject is TSX. Folding
them in would mean one script with two runners and two verdict formats, and the
pytest one is load-bearing for release checks. Two scripts with one idea each.

Same idea, though: a green suite says the guards pass, never that they would
*fail* if the behaviour they describe were removed. Each mutation below is the
shape the code had before F4, or the plausible mistake a later edit would make.

Three things this harness does that a naive loop does not:

- **It proves the baseline is green first.** Each distinct guard file is run
  once, unmutated, and has to pass. Without that, a file that was already red
  would "catch" every mutation, and the report would read as five proofs.
- **It checks *which* test failed.** A mutation that turns a different test in
  the same file red is reported as ``OTHER`` (unproven), not as the named guard
  having teeth -- otherwise a syntactic accident would look like coverage.
- **It proves the restore with a hash.** Files are read and written as bytes and
  compared by sha256, because ``read_text``/``write_text`` normalise line endings
  (this repo is ``core.autocrlf=true`` + ``* text=auto``, so the working tree is
  CRLF and the index is LF) and a text-mode round trip is not a restore.

Verdicts, printed per case: ``caught`` / ``MISSED`` / ``OTHER`` / ``SKIP`` /
``NO RUN``. The last three are unproven and fail the run.

Mutants have to stay *parseable*: one that breaks the file proves the file is
broken, not that the guard has teeth. Where a mutant could not be written in a
legal shape it says so in a comment.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import NamedTuple

ROOT = Path(__file__).resolve().parents[1]

#: Vitest's own entry point, run through ``node``.
#:
#: Not ``node_modules/.bin/vitest``: npm writes that shim as an extensionless
#: shell script on POSIX and as ``vitest.cmd`` on Windows, so a path naming
#: ``vitest.cmd`` is a Windows-only path -- the existence check in ``run`` would
#: abort this script on the ubuntu runner, which is why it could not be wired
#: into CI while it named one. ``vitest.mjs`` is the same file on every platform.
#: Going through ``node`` also skips the shim's own subshell, which is a second
#: process per case.
VITEST = ROOT / "node_modules" / "vitest" / "vitest.mjs"

#: (label, file, needle, mutant, test file, test title)
#:
#: `test file` is relative to vitest's root (``apps/frontend``); `test title` is
#: the `it(...)` name, which has to appear in the output for the case to count.
CASES: tuple[tuple[str, str, bytes, bytes, str, str], ...] = (
    (
        # The console writing the document element for itself. Harmless across
        # three documents with three <html> elements; a race in one, decided by
        # mount order.
        "FE4-1 the console writes the document language itself",
        "apps/frontend/src/console/FlowConsole.tsx",
        b"  const { locale, theme, setLocale, setTheme } = useLocaleTheme();\n",
        (
            b"  const { locale, theme, setLocale, setTheme } = useLocaleTheme();\n"
            b"  document.documentElement.lang = locale;\n"
        ),
        "src/shared/localeOwnership.test.ts",
        "writes the document language and theme only from the provider",
    ),
    (
        # The `?locale=&theme=` protocol, back. The comment directly above this
        # line explains why it went away, so the needle keeps its whole shape.
        "FE4-2 the console passes locale through the URL again",
        "apps/frontend/src/console/FlowConsole.tsx",
        b'      window.open("/workbench", "_blank", "noopener");\n',
        (
            b'      window.open(`/workbench?${new URLSearchParams({ locale, theme })}`, '
            b'"_blank", "noopener");\n'
        ),
        "src/shared/localeOwnership.test.ts",
        "does not pass locale or theme through a query string",
    ),
    (
        # The flag that only ever trimmed padding for a frame.
        "FE4-3 the workbench reads the embed flag again",
        "apps/frontend/src/workbench/PlanningWorkbench.tsx",
        b"  const { locale, theme, setLocale, setTheme } = useLocaleTheme();\n",
        (
            b"  const { locale, theme, setLocale, setTheme } = useLocaleTheme();\n"
            b'  const embedded = new URLSearchParams(window.location.search).has("embed");\n'
        ),
        "src/shared/localeOwnership.test.ts",
        "does not read or send an embed flag",
    ),
    (
        # `selectedEngineVersion`'s second implementation, restored in full: a
        # local no-argument copy, and the call site that used to reach it. The
        # old one answered from a substring match on stage ids, which is looser
        # about a corrupt handoff than the planModel check.
        "FE4-4 the shell grows a second engine-version implementation",
        "apps/frontend/src/studio/StudioShell.tsx",
        (
            b"function handedOffEngineVersion(): string {\n"
            b"  return selectedEngineVersion(readHandoffPlan());\n"
            b"}\n"
        ),
        (
            b'function selectedEngineVersion(): string {\n'
            b'  return "godot";\n'
            b"}\n"
            b"\n"
            b"function handedOffEngineVersion(): string {\n"
            b"  return selectedEngineVersion();\n"
            b"}\n"
        ),
        "src/shared/localeOwnership.test.ts",
        "answers the engine version from one implementation",
    ),
    (
        # `visitedPanels` back to `activePanel`: the console unmounts on a panel
        # switch, abandoning an in-flight job's polling. This is the one F4 risk
        # the plan called out as a decision rather than an implementation detail.
        "FE4-5 switching away unmounts the console again",
        "apps/frontend/src/studio/StudioShell.tsx",
        b'          {visitedPanels.includes("console") && (\n',
        b'          {activePanel === "console" && (\n',
        "src/studio/StudioShell.test.tsx",
        "keeps a visited view mounted once the user switches away",
    ),
    (
        # The base prefix applied unconditionally, which is the bug this branch
        # exists to prevent: FastAPI serves the routes at the root, so
        # `/frontend/web-console` is a 404. `import.meta.env.DEV` is substituted
        # at build time, so no test could reach this branch before it became a
        # parameter.
        "FE4-6 the panel URL keeps the base prefix in production",
        "apps/frontend/src/studio/StudioShell.tsx",
        b"  return dev && base ? `${base}${route}` : route;\n",
        b"  return `${base}${route}`;\n",
        "src/studio/StudioShell.test.tsx",
        "carries the dev server's base, and drops it in production",
    ),
    (
        # A fallback instead of a throw. The test asserts the *message*, so this
        # is caught by the error text rather than by any throw: the shell would
        # still blow up destructuring `null`, but as an anonymous TypeError that
        # names nothing about the provider.
        "FE4-7 a locale falls back instead of failing loudly",
        "apps/frontend/src/shared/localeTheme.tsx",
        b"  if (!value) {\n",
        b"  if (false) {\n",
        "src/studio/StudioShell.test.tsx",
        "refuses to render a view outside the provider",
    ),
    (
        # The entry point stops wrapping. A `<StrictMode>` around a bare shell is
        # valid JSX, so the mutant parses -- and the app would die at
        # `useLocaleTheme` on the first render. Nothing behavioural reads
        # main.tsx, which is why this guard is a source scan.
        #
        # The needle is the opening/closing provider pair rather than the whole
        # `render` tree: a journey provider was nested inside it later, and
        # pinning the full tree turned this case into a silent SKIP the first
        # time anything inside the tree changed. The guard it serves only cares
        # that the locale provider wraps the entry.
        "FE4-8 the entry point stops mounting the provider",
        "apps/frontend/src/main.tsx",
        (
            b"  <StrictMode>\n"
            b"    <LocaleThemeProvider>\n"
            b"      <JourneyProvider>\n"
            b"        <StudioShell />\n"
            b"      </JourneyProvider>\n"
            b"    </LocaleThemeProvider>\n"
            b"  </StrictMode>\n"
        ),
        (
            b"  <StrictMode>\n"
            b"    <JourneyProvider>\n"
            b"      <StudioShell />\n"
            b"    </JourneyProvider>\n"
            b"  </StrictMode>\n"
        ),
        "src/shared/localeOwnership.test.ts",
        "mounts the provider at the one entry point",
    ),
    (
        # A playtest launches an engine, so the confirm block is the only thing
        # standing between a click and a subprocess. The plausible regression is
        # "proceed also tears down", which reads as harmless cleanup and quietly
        # cancels the run the human just approved.
        "FE5-1 the playtest confirm block also cancels on proceed",
        "apps/frontend/src/console/playtest/PlaytestConfirmBlock.tsx",
        b'        <button className="primary-action" type="button" id="playtest-proceed" onClick={onProceed}>\n',
        (
            b'        <button className="primary-action" type="button" id="playtest-proceed" '
            b'onClick={() => { onProceed(); onCancel(); }}>\n'
        ),
        "src/console/playtestPanel.test.tsx",
        "runs the playtest only after the human accepts",
    ),
    (
        # `rework_target` and `resume_stage` are two vocabularies: the first says
        # what to change, the second which node to run from, and for `spec` they
        # resolve to different stages. Swapping them sends the operator to the
        # wrong node -- and the type accepts both because both are strings.
        "FE5-2 a playtest finding resumes from the rework target",
        "apps/frontend/src/console/playtest/PlaytestReportCard.tsx",
        b"onClick={() => onResume(finding.resume_stage || \"\")}",
        b"onClick={() => onResume(finding.rework_target || \"\")}",
        "src/console/playtestPanel.test.tsx",
        "resumes from the stage the backend translated, not one the panel made up",
    ),
    (
        # The card was renamed from .mcp-status-card to .stage-card because the
        # console's copy renders an ExecuteStage, not an MCP tool status -- the
        # old name coupled it to a parent it has nothing to do with. Renaming
        # both sides was invisible: nothing compared the class a component
        # emits against the sheet that styles it, so renaming the stylesheet and
        # forgetting the JSX rendered an unstyled card with every test still
        # green. The mutation renames one side only.
        "FE6-1 a renamed class is only half renamed",
        "apps/frontend/src/console/executionStage/ExecutionStageCard.tsx",
        b'className="stage-card"',
        b'className="mcp-status-card"',
        "src/shared/cssHygiene.test.ts",
        "styles the base class a component hangs its modifiers on",
    ),
    (
        # The other half of a rename, in the direction the forward check cannot
        # see: the sheet still styles `.stage-card` and `.stage-top`, but the
        # component has stopped rendering them -- so the rules are dead, and the
        # next person to reuse the name inherits styling nobody chose.
        #
        # A whole-sheet reverse sweep was tried and abandoned: 66 of
        # `console.css`'s classes are emitted from `rendering.tsx` or from the
        # inline components below the main function, so "no emitter in this one
        # file" is a statement about where markup lives, not about dead CSS.
        # This pair is checked by name because their ownership is unambiguous.
        "FE6-2 a card is unrendered and its rules become dead",
        "apps/frontend/src/console/executionStage/ExecutionStageCard.tsx",
        b'<div className="stage-top">',
        b'<div className="stage-top-unused">',
        "src/shared/cssHygiene.test.ts",
        "does not leave a stage-card rule behind after the card is renamed",
    ),
    (
        # A hardcoded color slipping back into a stylesheet. The value layer
        # removed 12 of them; `visualSystem.test.ts` only ever checked .tsx and
        # `ui.css`, so all four non-token sheets were unguarded. This is the
        # check that says they are not any more.
        "FE6-3 a stylesheet grows a hardcoded color again",
        "apps/frontend/src/styles/console.css",
        b".rework-status {\n",
        b'.rework-status {\n  color: #ff0000;\n',
        "src/shared/cssHygiene.test.ts",
        "keeps colors in tokens; a fallback in var() is not an exemption",
    ),
    (
        # A `var(--x, #hex)` fallback reads as "already tokenised" to anyone
        # skimming the file, but the hex never renders -- the variable is always
        # defined, which is exactly why the fallback is there and wrong. Five of
        # these lived in studio.css.
        "FE6-4 a dead color fallback comes back",
        "apps/frontend/src/styles/studio.css",
        b"  --sidebar-width: 282px;\n  display: grid;\n",
        b"  --sidebar-width: 282px;\n  color: var(--nonexistent-token, #6ea8fe);\n  display: grid;\n",
        "src/shared/cssHygiene.test.ts",
        "keeps colors in tokens; a fallback in var() is not an exemption",
    ),
    (
        # An off-scale value: the whole reason 12px and 13px coexisted for
        # months, rendering one screen at two font qualities.
        "FE6-5 a value lands off the token scale",
        "apps/frontend/src/styles/console.css",
        b".rework-status {\n  color: var(--muted);\n",
        b".rework-status {\n  color: var(--muted);\n  font-size: 13.7px;\n",
        "src/shared/cssHygiene.test.ts",
        "keeps font sizes, spacing and radii on the token scale",
    ),
    (
        # A token nobody reads. `--size-sidebar` sat at 292px for months while
        # the components hardcoded 282px and 82px; nothing noticed because
        # nothing checked. A design system's credibility is the sum of its
        # claims, and an unread token is a claim nobody kept.
        "FE6-6 a token nothing reads joins the file",
        "apps/frontend/src/styles/tokens.css",
        b"  --radius-pill: 999px;\n",
        b"  --radius-pill: 999px;\n  --nobody-reads-this: 4px;\n",
        "src/shared/cssHygiene.test.ts",
        "does not accumulate tokens nothing reads",
    ),
    (
        # Breakpoint drift: six of them once, with 900 and 860 forty pixels apart
        # applying to unrelated panels. They cannot be tokens -- `@media` does
        # not take `var()` -- so the grid is a convention, and a convention with
        # no check is a suggestion.
        "FE6-7 a breakpoint joins the grid from outside it",
        "apps/frontend/src/styles/console.css",
        b"@media (max-width: 1100px) {\n",
        b"@media (max-width: 1150px) {\n",
        "src/shared/cssHygiene.test.ts",
        "keeps breakpoints on the documented four-step grid",
    ),
    (
        # High-contrast mode drops box-shadow, so without this the focus ring --
        # the only cue a keyboard user has -- disappears exactly where it is
        # needed most.
        "FE6-8 high-contrast focus fallback is removed",
        "apps/frontend/src/styles/ui.css",
        b"@media (forced-colors: active) {",
        b"@media (forced-colors: inactive) {",
        "src/shared/ui/accessibility.test.ts",
        "keeps a focus ring in high-contrast mode",
    ),
    (
        # The shared focus rule dropping one selector. A ring that skips `select`
        # leaves it reachable and invisible, which is worse than no ring at all:
        # the operator cannot tell they are on the control.
        "FE6-9 the shared focus rule drops a focusable element",
        "apps/frontend/src/styles/ui.css",
        b"textarea:focus-visible,\nsummary:focus-visible,\niframe:focus-visible {",
        b"textarea:focus-visible,\nsummary:focus-visible {",
        "src/shared/ui/accessibility.test.ts",
        "gives every focusable element the ring, not just some of them",
    ),
)

#: vitest's `Tests` line. Absent means the run died before reporting.
#:
#: `[ \t]` rather than `\s`: in multiline mode `\s` matches newlines too, so
#: `^\s*Tests` can start matching on an earlier line and swallow it. The line is
#: indented with spaces and nothing else.
_SUMMARY = re.compile(r"^[ \t]*Tests[ \t]+(.+?)[ \t]*$", re.MULTILINE)

#: Colour escapes. vitest colours the counts, and the escape lands *between*
#: "Tests" and the numbers -- so a plain `\s+` never bridges them and a regex
#: written against `npm run frontend:test` output matches nothing here. Stripped
#: rather than merely disabled, because the reader of a saved log is not the only
#: consumer: `_classify` has to work on whatever comes back.
_ANSI = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")

OUTCOMES: dict[str, str] = {
    "caught": "RED (caught)",
    "missed": "GREEN (MISSED!)",
    "other": "OTHER TEST (unproven)",
    "skipped": "SKIP (unproven)",
    "no-run": "NO RUN (unproven)",
}


class Verdict(NamedTuple):
    """What one guard run actually proved."""

    outcome: str
    detail: str


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _as_eol(needle: bytes, eol: bytes) -> bytes:
    """Rewrite a needle's line endings to the ones the file on disk has.

    Same reason as the pytest harness: the working tree is CRLF for tracked files
    and LF for files a tool wrote directly, and a byte-exact needle would then
    match nothing and be reported as an unproven case.
    """

    return needle.replace(b"\r\n", b"\n").replace(b"\n", eol)


def _node() -> str:
    """The node binary, resolved so a missing toolchain names itself."""

    found = shutil.which("node")
    if not found:
        raise SystemExit("node is not on PATH; the frontend guards need Node 22+")
    return found


def run(relative_test: str) -> tuple[int, str]:
    """Run one guard file through vitest and report (exit code, its output)."""

    if not VITEST.exists():
        raise SystemExit(f"vitest is not installed at {VITEST}; run `npm install` first")

    # check=False: the guard is *supposed* to exit non-zero here, and letting the
    # call raise would abort the case with the mutated file still on disk.
    #
    # No `--reporter` flag: `basic` was removed in Vitest 5 and is now treated as
    # the name of a custom reporter module, which fails at startup with "Failed
    # to load custom Reporter from basic" -- and startup failures produce no
    # summary, so every case would be reported as unproven.
    completed = subprocess.run(
        [_node(), str(VITEST), "run", relative_test],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
        env={**os.environ, "NO_COLOR": "1", "FORCE_COLOR": "0"},
    )
    return completed.returncode, _ANSI.sub("", completed.stdout + completed.stderr)


def _classify(status: int, output: str, title: str) -> Verdict:
    """Read the verdict out of vitest's own report, never out of its exit code."""

    output = _ANSI.sub("", output)

    if "No test files found" in output:
        return Verdict("no-run", "the filter collected no test file")

    match = _SUMMARY.search(output)
    if match is None:
        # A transform or import error kills the file before any test reports.
        # That is the mutant being unloadable, not a guard with teeth.
        return Verdict("no-run", f"no test summary in the output (vitest exited {status})")

    counts = match.group(1).strip()
    if "no tests" in counts:
        return Verdict("no-run", "vitest reported 'no tests' for this filter")

    if status == 0:
        return Verdict("missed", counts)

    if title not in output:
        # Something else in the file went red. The named guard was not what
        # caught it, so this proves nothing about the named guard.
        return Verdict("other", f"{counts} -- but '{title}' was not among the failures")

    return Verdict("caught", counts)


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Prove each frontend guard goes red when the behaviour it describes is removed."
    )
    parser.add_argument(
        "--only",
        action="append",
        default=[],
        metavar="SUBSTRING",
        help="run only the cases whose label contains SUBSTRING (repeatable, case-insensitive).",
    )
    parser.add_argument("--list", action="store_true", help="print every case and exit")
    parser.add_argument(
        "--skip-baseline",
        action="store_true",
        help=(
            "skip the green-baseline run. Only for iterating: without it a case can "
            "be reported as caught by a file that was already failing."
        ),
    )
    return parser.parse_args(argv)


def _baseline(guards: list[str]) -> list[str]:
    """Run every distinct guard file unmutated and return the ones not green."""

    red: list[str] = []
    for relative_test in sorted(set(guards)):
        status, output = run(relative_test)
        verdict = _classify(status, output, "")
        if status != 0 or verdict.outcome != "missed":
            # `_classify` reads "green" as `missed` because in the loop that is
            # the interesting word; here it is exactly what we want.
            red.append(f"{relative_test} ({verdict.outcome}: {verdict.detail})")
        else:
            print(f"baseline {relative_test:44} {verdict.detail}")
    return red


def main(argv: list[str] | None = None) -> int:
    options = _parse_args(sys.argv[1:] if argv is None else argv)

    if options.list:
        for label, relative, _needle, _mutant, test, title in CASES:
            print(f"{label:48} {relative} :: {test} :: {title}")
        return 0

    selected = [
        case
        for case in CASES
        if not options.only or any(token.casefold() in case[0].casefold() for token in options.only)
    ]
    if not selected:
        # Silently running nothing would exit 0 and read as "all proven".
        print(f"no case label matches {options.only}; try --list")
        return 1

    if not options.skip_baseline:
        broken = _baseline([case[4] for case in selected])
        if broken:
            print()
            print(f"BASELINE IS RED, so a mutation's red would prove nothing: {broken}")
            return 1
        print()

    failures: list[str] = []
    caught = 0

    for label, relative, needle, mutant, relative_test, title in selected:
        target = ROOT / relative
        original = target.read_bytes()
        before = _sha256(original)
        eol = b"\r\n" if b"\r\n" in original else b"\n"
        needle, mutant = _as_eol(needle, eol), _as_eol(mutant, eol)

        if original.count(needle) != 1:
            print(f"{label:48} {OUTCOMES['skipped']:24} needle appears {original.count(needle)}x in {relative}")
            print(f"{'':49}0 matches is a rename, or residue of a run killed mid-case;")
            print(f"{'':49}check `git diff {relative}` before touching the needle.")
            failures.append(label)
            continue

        try:
            target.write_bytes(original.replace(needle, mutant))
            verdict = _classify(*run(relative_test), title)
            print(f"{label:48} {OUTCOMES[verdict.outcome]:24} {verdict.detail}")
            if verdict.outcome == "caught":
                caught += 1
            else:
                failures.append(label)
        finally:
            target.write_bytes(original)
            if _sha256(target.read_bytes()) != before:
                print(f"{label:48} RESTORE FAILED for {relative}")
                failures.append(label)

    print()
    if failures:
        print(f"UNPROVEN OR FAILED: {failures}")
        return 1

    proven = f"{caught}/{len(selected)} mutations caught"
    if len(selected) != len(CASES):
        proven += f" (--only: {len(CASES) - len(selected)} of {len(CASES)} cases not run)"
    print(f"{proven}; every source restored byte-identically (sha256)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
