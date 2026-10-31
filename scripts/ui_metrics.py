"""Measure the frontend's style + information surface. Read-only; prints a report.

Every number this prints can be recomputed by re-running it, so the docs that
cite them do not have to be kept in sync by hand:

    python scripts/ui_metrics.py
    python scripts/ui_metrics.py --json     # machine-readable, for CI diffs
    python scripts/ui_metrics.py --check   # exit 1 if any budget in BUDGETS is blown

It parses CSS by brace matching, not with a CSS library: the point is to count
what is written, and a real parser would normalise away the very duplication
this is meant to surface.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STYLES = ROOT / "apps/frontend/src/styles"
SRC = ROOT / "apps/frontend/src"

SPACING_PROPS = ("padding", "margin", "gap", "row-gap", "column-gap", "inset")
COLOR_PROPS = (
    "color",
    "background",
    "background-color",
    "border-color",
    "border-top-color",
    "border-right-color",
    "border-bottom-color",
    "border-left-color",
    "outline-color",
    "fill",
    "stroke",
    "box-shadow",
    "border",
)
RADIUS_PROPS = (
    "border-radius",
    "border-top-left-radius",
    "border-top-right-radius",
    "border-bottom-left-radius",
    "border-bottom-right-radius",
)

# States emitted from template literals, e.g. `playtest-${status}`; a static
# grep sees them as dead. css-conventions.md §5 says why.
DYNAMIC_CLASS_HINTS = ("${",)

# The 2026-10-19 measured values are the *starting* budgets, not targets:
# --check exists to fail when a change makes one of them worse, and it passes
# today by construction. The four added last are the ones the refactoring plan
# in docs/superpowers/plans/2026-10-19-frontend-interface-refactor.md moves.
BUDGETS = [
    # (metric key, limit, direction)  direction "max": value must be <= limit
    # Ratchet, not aspiration: each of these was the measured value on the day
    # it was written, so a budget that fails today is a regression and not a
    # todo list. `css_lines` rose 4534 -> 4611 during the 2026-10-19 pass while
    # `rules_total` fell 720 -> 714: the sheets grew explanations, not rules,
    # which is the trade this refactor is making on purpose.
    # The low-density step workflow adds explicit disclosure and responsive
    # state rules. The visual surface is smaller, but the CSS budget grows to
    # hold those states without inline styles or selector duplication.
    ("css_lines", 5000, "max"),
    ("selectors_total", 900, "max"),
    ("selector_dup_rate_pct", 15.2, "max"),
    ("class_selectors", 620, "max"),
    ("token_coverage_pct", 85.6, "min"),
    ("distinct_font_sizes", 4, "max"),
    ("dead_class_selectors", 40, "max"),
    ("inline_style_props", 30, "max"),
    ("grid_templates_unique", 26, "max"),
    ("colour_alias_refs", 119, "max"),
    ("cross_sheet_collisions", 1, "max"),
    ("shared_classes_multi_file", 33, "max"),
    # Ratchet: 27 measured on 2026-10-19 before the vocabulary existed, 2 after.
    # The 2 are the affordances -- a button that OFFERS a decision is not the
    # thing that decision reports -- and they are named in the sheets. Anything
    # above 2 is a mapping that forgot where mappings live.
    ("state_mappings_outside_vocabulary", 2, "max"),
]


# --------------------------------------------------------------------------
# CSS parsing
# --------------------------------------------------------------------------


def parse_blocks(text: str) -> list[tuple[str, str, str]]:
    """Split into ('rule', prelude, body) and ('text', content, '') items."""
    items: list[tuple[str, str, str]] = []
    buf: list[str] = []
    i, n = 0, len(text)
    while i < n:
        c = text[i]
        if c == "{":
            depth, j = 1, i + 1
            while j < n:
                if text[j] == "{":
                    depth += 1
                elif text[j] == "}":
                    depth -= 1
                    if depth == 0:
                        break
                j += 1
            items.append(("rule", "".join(buf).strip(), text[i + 1 : j]))
            buf = []
            i = j + 1
        else:
            buf.append(c)
            i += 1
    if buf:
        items.append(("text", "".join(buf), ""))
    return items


def split_selectors(prelude: str) -> list[str]:
    """Split a selector list on top-level commas."""
    out, buf, depth = [], [], 0
    for c in prelude:
        if c in "([":
            depth += 1
        elif c in ")]":
            depth -= 1
        if c == "," and depth == 0:
            out.append("".join(buf).strip())
            buf = []
        else:
            buf.append(c)
    if buf:
        out.append("".join(buf).strip())
    return [s for s in out if s]


def strip_comments(text: str) -> str:
    return re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)


def _standalone_in(selector: str) -> str | None:
    """The class a PLAIN `.name` rule owns, or None.

    Rewritten 2026-10-19 to match `cssHygiene.test.ts`'s `baseClasses`, because
    two counts of the same thing that disagree are worse than one count. The
    old rule asked "is this class the only simple selector here", which counts
    two things that are not the hazard:

        `.review-pill[data-status="human"]`  0,2,0 -- the attribute wins
        `.recovery-actions .ghost-action`    0,2,0 -- the combinator does
        `:where(.review-pill)`               0,0,0 -- zero on purpose, it is
                                                     how the vocabulary lists
                                                     its readers

    None of those can tie with another sheet's base rule on import order, which
    is the thing being counted. So: exactly `.name`, nothing attached.
    """
    s = selector.strip()
    if not s or re.search(r"\s", s):
        return None
    if re.fullmatch(r"\.[a-zA-Z][a-zA-Z0-9_-]*", s):
        return s[1:]
    return None


def standalone_classes(css: str) -> set[str]:
    """Classes this sheet gives a plain `.name` rule.

    Comments are stripped by the caller -- a prose mention of `.foo` is not a
    rule, and every sheet in this repo mentions other sheets' classes in its
    comments.

    A rule whose prelude contains `:where(` is skipped whole: a multi-line
    `:where(...)` splits on commas into members that no longer start with
    `:where(`, so checking each member for the prefix lets all but the first
    one through.
    """
    found: set[str] = set()
    for _kind, a, b in parse_blocks(css):
        if a.startswith("@") or ":where(" in a:
            continue
        for sel in split_selectors(a):
            name = _standalone_in(sel)
            if name:
                found.add(name)
        for kind2, a2, _b2 in parse_blocks(b):
            if kind2 == "rule" and not a2.startswith("@") and ":where(" not in a2:
                for sel in split_selectors(a2):
                    name = _standalone_in(sel)
                    if name:
                        found.add(name)
    return found


COLOUR_TOKEN = re.compile(r"var\(--(?:status|brand|tone)[a-z_-]*")
_STATE_ATTR = re.compile(r"^\[data-[a-z_-]+=\"[^\"]+\"\]$")
_STATE_CLASS = re.compile(r"^\.[A-Za-z0-9_-]+(?:\.[A-Za-z0-9_-]+)+(?:\[[^\]]*\])?$")
_ATTR_QUALIFIED = re.compile(r"^\.[A-Za-z0-9_-]+(?:\[[^\]]*\])+$")
# A rule that reads the vocabulary rather than restating it: it has no colour of
# its own, it asks `ui.css` for one.
_READER = re.compile(r"var\(--tone")
# Selection and affordance modifiers, NOT states. The shape sweep cannot tell
# "the tab that is selected" from "the run that failed" -- both are a compound
# class with a colour in the body -- so they are named, one by one, with the
# reason each one is not a state:
#
#   active / is-on  which control is the chosen one, a fact about the widget
#   primary         which button is the main one, likewise
#
# What makes those different from `.wb-chip.running` is the question the value
# answers: "is this the one" rather than "what happened to this". The first is
# decided by the user's last click and lives in the control; the second is a
# lifecycle fact and has to come from one place.
SELECTION_MODIFIERS = {"active", "is-on", "primary"}


def state_mappings_outside_vocabulary(files: dict[str, str]) -> list[str]:
    """Every rule outside `ui.css` that maps a state to a colour itself.

    Two sweeps during this refactor each found a shape and missed the rest: the
    one keyed on attribute names missed `data-state`, and the one keyed on
    attribute shapes missed `.wb-chip.ready`, because a compound class is not an
    attribute selector at all. Every one of them undercounted, so this looks
    for the SHAPE of a mapping rather than for names: a rule more specific than
    the component it belongs to, whose body paints a colour and does not read
    one.

    What is left is the two affordances documented in the sheets themselves --
    a button you press to approve is not itself an approved thing.
    """
    out: list[str] = []
    for name, text in sorted(files.items()):
        if name == "ui.css":
            continue
        css = strip_comments(text)
        for kind, prelude, body in parse_blocks(css):
            if kind != "rule" or prelude.startswith("@") or ":where(" in prelude:
                continue
            if not COLOUR_TOKEN.search(body) or _READER.search(body):
                continue
            for sel in split_selectors(prelude):
                s = sel.strip()
                if _STATE_ATTR.match(s) or _ATTR_QUALIFIED.match(s):
                    out.append(f"{name}: {s}")
                    continue
                if not _STATE_CLASS.match(s):
                    continue
                # `.foo.active` and `.foo.bar.active`: a mapping only if the
                # modifier is a state and not a selection.
                modifiers = re.findall(r"\.([A-Za-z0-9_-]+)", s)[1:]
                if modifiers and not (set(modifiers) & SELECTION_MODIFIERS):
                    out.append(f"{name}: {s}")
    return out


def walk(text: str, rules: list, decls: list, at_stack: tuple = ()) -> None:
    for kind, a, b in parse_blocks(text):
        if kind == "text":
            for d in a.split(";"):
                d = d.strip()
                if d and ":" in d and not d.startswith("@"):
                    decls.append((at_stack, d))
        elif a.startswith("@"):
            if re.match(r"@(media|supports|container)\b", a):
                walk(b, rules, decls, at_stack + (a,))
        else:
            for sel in split_selectors(a):
                rules.append((a, sel, at_stack))
            walk(b, rules, decls, at_stack)


# --------------------------------------------------------------------------
# Decoration extraction
# --------------------------------------------------------------------------

HEX = re.compile(r"#[0-9a-fA-F]{3,8}\b")
VAR = re.compile(r"var\(\s*(--[A-Za-z0-9_-]+)")
FUNC = re.compile(r"\b(rgba?|hsla?)\s*\(")
NUM = re.compile(r"^\d+(\.\d+)?px$")


def tokens_in(value: str) -> list[str]:
    return VAR.findall(value)


def is_decorative(prop: str) -> bool:
    """A property the token *scale* governs -- as opposed to a dimension.

    `min-height`, `max-width`, `line-height` and `z-index` are deliberately
    not in here. Counting them as untokenised produced a coverage number of
    85.4% whose missing 178 were 43 `min-height: 28px` on a badge, 19
    `max-width`, and 17 `line-height: 1.15`. Those are a component's own
    proportions and its type ratio; putting them on the spacing ladder would
    be worse than leaving them alone. A metric that is 100% of the wrong
    things is worse than one that is 85% of the right ones.
    """
    p = prop.strip()
    if p.startswith("--"):
        return False
    return (
        p == "font-size"
        or p in RADIUS_PROPS
        or p in COLOR_PROPS
        or p in SPACING_PROPS
        or p.startswith(("padding-", "margin-"))
        or p
        in {
            "box-shadow",
            "transition-duration",
            "duration",
        }
    )


RESET_VALUES = {
    "0",
    "auto",
    "none",
    "inherit",
    "initial",
    "unset",
    "50%",
    "100%",
    "currentColor",
    "transparent",
}


def is_reset(value: str) -> bool:
    """A value the scale has nothing to say about: `margin: 0` is not spacing.

    67 of the 178 "violations" were `margin: 0`. There is no `--space-0`, and
    inventing one to move the number would be the anti-pattern the conventions
    file warns about in its own voice.
    """
    return value.strip() in RESET_VALUES


def collect_css() -> dict:
    files = sorted(STYLES.glob("*.css"))
    rules_all: list[tuple[str, str, tuple]] = []
    decls_all: list[tuple[tuple, str]] = []
    per_file: dict[str, dict] = {}
    media_values: Counter = Counter()

    for f in files:
        raw = f.read_text(encoding="utf-8")
        text = strip_comments(raw)
        rules: list = []
        decls: list = []
        walk(text, rules, decls)
        rules_all.extend((f.name, s, at) for _, s, at in rules)
        decls_all.extend(decls)
        for at, _d in decls:
            for a in at:
                for m in re.finditer(r"(max|min)-width:\s*(\d+)px", a):
                    media_values[m.group(0)] += 1
        per_file[f.name] = {
            "lines": raw.count("\n") + 1,
            "rules": len(rules),
            "selectors": len([1 for _, s, _ in rules for _x in [s]]),
        }
    return {
        "files": per_file,
        "rules": rules_all,
        "decls": decls_all,
        "media": media_values,
    }


def analyse_decls(decls: list) -> dict:
    font_sizes: Counter = Counter()
    spacings: Counter = Counter()
    radii: Counter = Counter()
    colors: Counter = Counter()
    tokenised = 0
    decorative = 0
    bare_hex = 0
    bare_rgb = 0
    var_refs: Counter = Counter()

    for _at, d in decls:
        prop, _, value = d.partition(":")
        prop, value = prop.strip(), value.strip()
        if not prop or prop.startswith("--"):
            continue
        if not is_decorative(prop):
            continue
        if is_reset(value):
            continue

        tokens = tokens_in(value)
        for t in tokens:
            var_refs[t] += 1
        has_token = bool(tokens)
        if has_token:
            tokenised += 1
        decorative += 1

        if HEX.search(value) and not FUNC.search(value):
            bare_hex += 1
        if FUNC.search(value):
            bare_rgb += 1

        for part in value.split():
            p = part.strip()
            if p in ("0", "auto", "inherit", "initial", "unset", "none", "50%", "100%"):
                continue
            if p.startswith(("calc", "var(")) or "(" in p:
                continue
            if prop == "font-size":
                font_sizes[p] += 1
            elif prop in RADIUS_PROPS:
                radii[p] += 1
            elif prop in SPACING_PROPS or prop.startswith(("padding-", "margin-")):
                spacings[p] += 1
        for h in HEX.findall(value):
            colors[h.lower()] += 1

    return {
        "decorative_decls": decorative,
        "tokenised_decls": tokenised,
        "token_coverage_pct": round(100.0 * tokenised / decorative, 1) if decorative else 0.0,
        "bare_hex": bare_hex,
        "bare_rgb": bare_rgb,
        "font_sizes": font_sizes,
        "spacings": spacings,
        "radii": radii,
        "colors": colors,
        "var_refs": var_refs,
    }


# --------------------------------------------------------------------------
# TSX side
# --------------------------------------------------------------------------

INLINE_STYLE_RE = re.compile(r"style=\{\{([^}]*)\}\}")
HEX_TSX = re.compile(r"#[0-9a-fA-F]{6}\b")

# `className` plus the variants that pass a class into a child:
# `buttonClassName`, `panelClassName`, `inputClassName`... A class handed to a
# shared component is still a usage; counting only `className=` reported every
# segmented control's buttons as dead CSS.
ATTR_RE = re.compile(r"[A-Za-z]*[Cc]lassName\s*=\s*")
LITERAL_RE = re.compile(r'"([^"]*)"|\'([^\']*)\'|`([^`]*)`')
INTERP_RE = re.compile(r"\$\{[^}]*\}")


def _read_value(raw: str, i: int) -> tuple[str, int]:
    """Return the raw source slice of the attribute value, delimiters included.

    The delimiters have to survive: they are what tells a literal
    (`"wb-tab active"`) apart from an expression (`cond ? "a" : "b"`), and
    `_literals` keys off them.
    """
    while i < len(raw) and raw[i] in " \n\t":
        i += 1
    if i >= len(raw):
        return "", i
    start = i
    c = raw[i]
    if c in "\"'`":
        j = i + 1
        while j < len(raw):
            if raw[j] == "\\":
                j += 2
                continue
            if raw[j] == c:
                break
            j += 1
        return raw[start : j + 1], j + 1
    if c == "{":
        depth, j = 1, i + 1
        while j < len(raw):
            if raw[j] == "{":
                depth += 1
            elif raw[j] == "}":
                depth -= 1
                if depth == 0:
                    break
            j += 1
        return raw[start : j + 1], j + 1
    return "", i


# `activePanel === "workbench" ? "active" : ""` -- the first literal is a
# comparison, not a class name. Conditions precede their `?`, so drop them
# before collecting; otherwise every view key and locale code in the app is
# reported as a class that has no CSS rule.
_COND_RE = re.compile(r"""[\w.)\]]+\s*[!=]==?\s*(?:"[^"]*"|'[^']*'|`[^`]*`)""")
_INCLUDES_RE = re.compile(r"""\.includes\(\s*(?:"[^"]*"|'[^']*'|`[^`]*`)\s*\)""")


def _strip_conditions(expr: str) -> str:
    expr = _INCLUDES_RE.sub(" ", expr)
    return _COND_RE.sub(" ", expr)


def _literals(expr: str) -> list[str]:
    """Literal text inside an expression. `${status}` is not a class name.

    Two passes, because one is not enough: scanning the raw expression finds
    the outer template literal, and that match swallows the literals nested in
    its interpolations -- `` `or-button${approved ? " is-on" : ""}` `` would
    yield only `or-button` and lose the `is-on` that is the entire point.
    """
    cands: set[str] = set()
    expr = _strip_conditions(expr)
    # (a) interpolations blanked, so the outer template literal reads clean.
    for a, b, c in LITERAL_RE.findall(INTERP_RE.sub(" ", expr)):
        cands.add(a or b or c)
    # (b) template delimiters removed, so literals inside ${...} surface.
    for a, b, c in LITERAL_RE.findall(expr.replace("`", " ")):
        cands.add(a or b or c)
    out = []
    for s in cands:
        s = INTERP_RE.sub(" ", s).strip()
        if s:
            out.append(s)
    return out


def collect_tsx() -> dict:
    files = [p for p in SRC.rglob("*.tsx") if ".test." not in p.name]
    used_classes: Counter = Counter()
    class_files: dict[str, set[str]] = {}
    dynamic_prefixes: set[str] = set()
    inline_props = 0
    inline_files: Counter = Counter()
    hard_hex = 0
    big_files = []
    jsx_elements = 0

    for p in files:
        raw = p.read_text(encoding="utf-8")
        rel = re.sub(r"^.*?src[\\/]", "", str(p)).replace("\\", "/")
        for m in ATTR_RE.finditer(raw):
            val, _end = _read_value(raw, m.end())
            for lit in _literals(val):
                for tok in re.finditer(r"[\w-]+", lit):
                    name = tok.group(0)
                    used_classes[name] += 1
                    class_files.setdefault(name, set()).add(rel)
                # `playtest-${status}` leaves the literal fragment `playtest-`;
                # remember it as a wildcard so the concrete states written in
                # CSS are not reported dead. css-conventions.md §5.
                for piece in lit.split():
                    if piece.endswith("-"):
                        dynamic_prefixes.add(piece)
        for m in INLINE_STYLE_RE.finditer(raw):
            props = [x for x in m.group(1).split(",") if ":" in x]
            inline_props += len(props)
            if props:
                inline_files[str(p.relative_to(ROOT))] += len(props)
        hard_hex += len(HEX_TSX.findall(raw))
        lines = raw.count("\n") + 1
        jsx_elements += len(re.findall(r"<[A-Za-z][\w.]*", raw))
        if lines >= 300:
            big_files.append((str(p.relative_to(ROOT)), lines))

    return {
        "files": len(files),
        "used_classes": used_classes,
        "class_files": class_files,
        "dynamic_prefixes": dynamic_prefixes,
        "inline_style_props": inline_props,
        "inline_style_files": inline_files,
        "hard_coded_hex": hard_hex,
        "files_over_300_lines": sorted(big_files, key=lambda x: -x[1]),
        "jsx_elements": jsx_elements,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()

    css = collect_css()
    decl = analyse_decls(css["decls"])
    tsx = collect_tsx()

    selectors = [s for _f, s, _a in css["rules"]]
    sel_counter = Counter(selectors)

    # class selectors: leaf classes mentioned in a selector
    class_sel: Counter = Counter()
    for s in selectors:
        for m in re.finditer(r"\.([A-Za-z_][\w-]*)", s):
            class_sel[m.group(1)] += 1
    # selector-group duplicates: identical selector text written more than once
    group_dups = {k: v for k, v in sel_counter.items() if v > 1}
    dup_extra = sum(v - 1 for v in group_dups.values())

    used = set(tsx["used_classes"])
    prefixes = tuple(tsx["dynamic_prefixes"])

    # A state modifier (`.review-pill.approved`, `.or-button.is-on`) is applied
    # by a variable, so no static scan can see it applied. It is structurally
    # identifiable instead: it only ever appears glued to another class. That
    # is a shape, not a name pattern, so it does not need a hand-kept list.
    # `.hidden { display: none }` stands alone -- and is therefore still
    # reported when nothing references it.
    modifier_only: set[str] = set()
    for s in selectors:
        for m in re.finditer(r"\.([A-Za-z_][\w-]*)\.([A-Za-z_][\w-]*)", s):
            modifier_only.add(m.group(2))

    def is_used(c: str) -> bool:
        if c in used:
            return True
        return bool(prefixes) and c.startswith(prefixes)

    dead = sorted(c for c in class_sel if not is_used(c) and c not in modifier_only)
    # classes used in TSX with no CSS definition
    orphan = sorted(c for c in used if c not in class_sel and not c.endswith("-") and len(c) > 2)

    # Component families: classes sharing a trailing token, e.g. `.task-pill`
    # / `.review-pill` / `.wb-pill` / `.status-badge`. Four near-identical
    # members is the duplication that matters; four unrelated `.foo-pill` are
    # not, so the metric counts families, not raw classes.
    families: dict[str, list[str]] = {}
    for c in class_sel:
        fam = c.rsplit("-", 1)[-1]
        families.setdefault(fam, []).append(c)
    notable = {fam: sorted(members) for fam, members in families.items() if len(members) >= 3}

    # A name two sheets both define is dressed by import order, not by
    # decision. `cssHygiene.test.ts` guards this across every pair now and
    # carries a KNOWN_SHARED registry, so this metric is the guard's number
    # recomputed from the other side: if the two ever disagree, the definition
    # drifted in one of them and both are wrong.
    per_sheet = {
        f.name: standalone_classes(strip_comments(f.read_text(encoding="utf-8")))
        for f in STYLES.glob("*.css")
    }
    raw_sheets = {f.name: f.read_text(encoding="utf-8") for f in STYLES.glob("*.css")}
    stray_mappings = state_mappings_outside_vocabulary(raw_sheets)
    collisions: Counter = Counter()
    names = sorted(per_sheet)
    for i, a in enumerate(names):
        for b in names[i + 1 :]:
            for c in sorted(per_sheet[a] & per_sheet[b]):
                collisions[(a, b, c)] += 1

    # Layout scattering: every `grid-template-columns` value in the stylesheets.
    # 26 shapes that differ by a few dozen pixels is the thing a per-panel
    # "tweak the columns" habit produces, and no single file shows it.
    grid_total = 0
    grid_values: Counter = Counter()
    for f in STYLES.glob("*.css"):
        text = strip_comments(f.read_text(encoding="utf-8"))
        for m in re.finditer(r"grid-template-columns:\s*([^;}]+)", text):
            grid_total += 1
            grid_values[m.group(1).strip()] += 1

    # Two colour vocabularies for the same tokens. `--accent` is an alias of
    # `--brand` and `--danger` of `--status-danger`; tokens.css carries both so
    # old files keep compiling. Counting each side shows whether the migration
    # is finished or merely started.
    alias_refs = Counter()
    status_refs = Counter()
    for f in STYLES.glob("*.css"):
        if f.name == "tokens.css":
            continue
        text = strip_comments(f.read_text(encoding="utf-8"))
        for m in re.finditer(
            r"var\(--(accent|accent-deep|accent-soft|amber|amber-soft|"
            r"danger|danger-soft|blue|blue-soft)\b",
            text,
        ):
            alias_refs[m.group(1)] += 1
        for m in re.finditer(r"var\(--status-([a-z]+)", text):
            status_refs[m.group(1)] += 1

    # Classes used by more than one view file: these are the de-facto shared
    # components, whatever their names say. `.handoff-note` is the exhibit: it
    # is the app's hint paragraph and it is named after one panel.
    shared_across_files = sorted(
        (c, sorted(fs)) for c, fs in tsx["class_files"].items() if len(fs) >= 2
    )

    metrics = {
        "css_files": len(css["files"]),
        "css_lines": sum(v["lines"] for v in css["files"].values()),
        "rules_total": sum(v["rules"] for v in css["files"].values()),
        "selectors_total": len(selectors),
        "selectors_unique": len(sel_counter),
        "selector_dup_rate_pct": round(100.0 * dup_extra / len(selectors), 1) if selectors else 0.0,
        "class_selectors": len(class_sel),
        "dead_class_selectors": len(dead),
        "orphan_classes_in_tsx": len(orphan),
        "distinct_font_sizes": len(decl["font_sizes"]),
        "distinct_spacings": len(decl["spacings"]),
        "distinct_radii": len(decl["radii"]),
        "distinct_raw_colors": len(decl["colors"]),
        "token_coverage_pct": decl["token_coverage_pct"],
        "decorative_decls": decl["decorative_decls"],
        "tokenised_decls": decl["tokenised_decls"],
        "bare_hex": decl["bare_hex"],
        "bare_rgb": decl["bare_rgb"],
        "media_breakpoints": dict(css["media"]),
        "tsx_files": tsx["files"],
        "jsx_elements": tsx["jsx_elements"],
        "inline_style_props": tsx["inline_style_props"],
        "hard_coded_hex_in_tsx": tsx["hard_coded_hex"],
        "files_over_300_lines": len(tsx["files_over_300_lines"]),
        "class_families_ge3": len(notable),
        "grid_templates_total": grid_total,
        "grid_templates_unique": len(grid_values),
        "colour_alias_refs": sum(alias_refs.values()),
        "colour_status_refs": sum(status_refs.values()),
        "shared_classes_multi_file": len(shared_across_files),
        "cross_sheet_collisions": len(collisions),
        "state_mappings_outside_vocabulary": len(stray_mappings),
    }

    if args.json:
        print(
            json.dumps(
                {
                    "metrics": metrics,
                    "per_file": css["files"],
                    "duplicated_selectors": dict(
                        sorted(group_dups.items(), key=lambda x: -x[1])[:40]
                    ),
                    "top_spacings": decl["spacings"].most_common(20),
                    "top_font_sizes": decl["font_sizes"].most_common(10),
                    "top_radii": decl["radii"].most_common(10),
                    "top_colors": decl["colors"].most_common(15),
                    "inline_style_files": tsx["inline_style_files"].most_common(15),
                    "big_tsx_files": tsx["files_over_300_lines"],
                    "dead_classes": dead,
                    "orphan_classes": orphan,
                    "modifier_only_classes": sorted(modifier_only),
                    "class_families_ge3": notable,
                    "shared_classes_multi_file": shared_across_files,
                    "cross_sheet_collisions": [list(k) for k in sorted(collisions)],
                    "state_mappings_outside_vocabulary": stray_mappings,
                    "grid_template_values": dict(
                        sorted(grid_values.items(), key=lambda x: -x[1])[:30]
                    ),
                    "colour_aliases": dict(alias_refs),
                    "colour_status": dict(status_refs),
                },
                indent=2,
                ensure_ascii=False,
            )
        )
        return 0

    w = sys.stdout.write
    w("=" * 72 + "\n")
    w("Fantasy-Agent 前端现状实测\n")
    w("=" * 72 + "\n\n")
    w("## 规模\n\n")
    w(
        f"  CSS 文件 {metrics['css_files']} 个 / {metrics['css_lines']} 行 / "
        f"{metrics['rules_total']} 条规则 / {metrics['selectors_total']} 个选择器\n"
    )
    w(f"  TSX 文件 {metrics['tsx_files']} 个 / JSX 元素 {metrics['jsx_elements']} 个\n\n")
    w("  每个样式表:\n")
    for name, v in sorted(css["files"].items(), key=lambda x: -x[1]["lines"]):
        w(f"    {name:<20} {v['lines']:>5} 行  {v['rules']:>4} 规则  {v['selectors']:>4} 选择器\n")

    w("\n## 样式复用\n\n")
    w(
        f"  选择器去重后 {metrics['selectors_unique']} 个（重复率 {metrics['selector_dup_rate_pct']}%）\n"
    )
    w(
        f"  类选择器 {metrics['class_selectors']} 个，其中 TSX 里查不到引用的 {metrics['dead_class_selectors']} 个\n"
    )
    w(f"  TSX 里用了但 CSS 无定义的类 {metrics['orphan_classes_in_tsx']} 个\n")
    w(
        f"  token 覆盖率 {metrics['token_coverage_pct']}%"
        f"（装饰性声明共 {metrics['decorative_decls']} 条，"
        f"其中 {metrics['decorative_decls'] - metrics['tokenised_decls']} 条不引用 token）\n"
    )
    w(f"  装饰性声明中裸 hex {metrics['bare_hex']} 处、rgb()/hsl() {metrics['bare_rgb']} 处\n")
    w(
        f"  取值离散度：字号 {metrics['distinct_font_sizes']} 种 / 间距 {metrics['distinct_spacings']} 种"
        f" / 圆角 {metrics['distinct_radii']} 种 / 裸颜色 {metrics['distinct_raw_colors']} 种\n"
    )

    w("\n  出现最多的重复选择器:\n")
    for k, v in sorted(group_dups.items(), key=lambda x: -x[1])[:15]:
        w(f"    x{v}  {k[:70]}\n")

    w("\n  间距取值频次（前 12）:\n")
    for k, v in decl["spacings"].most_common(12):
        w(f"    {k:<12} {v}\n")

    w("\n  组件族（同一后缀的类 ≥3 个，是近亲实现，不是孤立类名）:\n")
    for fam, members in sorted(notable.items(), key=lambda x: -len(x[1]))[:14]:
        w(
            f"    -{fam}  ({len(members)}): {', '.join('.' + m for m in members[:8])}"
            f"{' …' if len(members) > 8 else ''}\n"
        )

    w("\n## 排版与色彩\n\n")
    w(
        f"  grid-template-columns {metrics['grid_templates_total']} 处 / "
        f"{metrics['grid_templates_unique']} 种不同取值\n"
    )
    w(
        f"  颜色两套词汇：旧名(--accent/--amber/--danger/--blue) "
        f"{metrics['colour_alias_refs']} 处 vs 语义名(--status-*) "
        f"{metrics['colour_status_refs']} 处\n"
    )
    w(f"  跨文件共用的类 {metrics['shared_classes_multi_file']} 个（事实上的共享组件）\n")
    w(
        f"  两张表同时定义的类 {metrics['cross_sheet_collisions']} 个"
        f"（样式由导入顺序决定，不由决定决定）\n"
    )
    for a, b, c in sorted(collisions)[:12]:
        w(f"    .{c:<28} {a} x {b}\n")

    # The number that says whether the vocabulary is actually the only mapping.
    # It is printed with its contents and not just its count, because the two
    # entries that survive are deliberate and a reader has to be able to see
    # which two they are.
    w(
        f"\n  ui.css 之外自己映射状态到颜色的规则 "
        f"{metrics['state_mappings_outside_vocabulary']} 条\n"
    )
    for line in stray_mappings[:14]:
        w(f"    {line}\n")
    if not stray_mappings:
        w("    （无：颜色映射只在 ui.css 一处）\n")

    w("\n## TSX 侧\n\n")
    w(f"  内联 style 属性 {metrics['inline_style_props']} 处\n")
    w(f"  硬编码 hex {metrics['hard_coded_hex_in_tsx']} 处\n")
    w(f"  超过 300 行的文件 {metrics['files_over_300_lines']} 个\n")
    for name, lines in tsx["files_over_300_lines"][:12]:
        w(f"    {name:<60} {lines}\n")
    w("\n  内联 style 最多的文件:\n")
    for name, n in tsx["inline_style_files"].most_common(8):
        w(f"    {name:<60} {n}\n")

    if args.check:
        failures = []
        for key, limit, direction in BUDGETS:
            val = metrics.get(key)
            if val is None:
                continue
            if direction == "max" and val > limit:
                failures.append(f"{key} = {val} > {limit}")
            if direction == "min" and val < limit:
                failures.append(f"{key} = {val} < {limit}")
        w("\n## 预算检查\n\n")
        if failures:
            for f in failures:
                w(f"  FAIL  {f}\n")
            return 1
        w("  全部通过\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
