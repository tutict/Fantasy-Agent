/**
 * Presentation primitives shared by every plan panel.
 *
 * The console and the planning workbench each grew their own copies of these
 * (`.summary-block` there, `.wb-block` here). They are one implementation now,
 * and they emit the `wb-*` class names because that set is the superset: it
 * already carries the block grid the console panels lack.
 *
 * `console.css` keeps the old `.summary-block` / `.stage-pill` selectors as
 * aliases so the panels drop into the console layout without a second stylesheet
 * rewrite. That is deliberate -- the class rename and the panel merge are two
 * changes, and doing them together would make a regression hard to attribute.
 */

import type { ReactNode } from "react";

export function Block({ title, wide, children }: { title: string; wide?: boolean; children: ReactNode }) {
  return (
    <section className={`wb-block${wide ? " wide" : ""}`}>
      <h3>{title}</h3>
      {children}
    </section>
  );
}

/**
 * A titled list. An empty list renders an explicit dash rather than a blank
 * region: the operator has to be able to tell "nothing here" from "the payload
 * never arrived".
 */
export function ListBlock({ title, items, wide }: { title: string; items: string[]; wide?: boolean }) {
  return (
    <Block title={title} wide={wide}>
      {items.length ? (
        <ul>
          {items.map((item, index) => (
            <li key={`${item}-${index}`}>{item}</li>
          ))}
        </ul>
      ) : (
        <p>-</p>
      )}
    </Block>
  );
}

export function TextBlock({ title, body, wide }: { title: string; body?: string; wide?: boolean }) {
  return (
    <Block title={title} wide={wide}>
      <p>{body || "-"}</p>
    </Block>
  );
}

/** One row of gate pills, as the pipeline and task panels build them. */
export function PillRow({ children }: { children: ReactNode }) {
  return <div className="wb-meta">{children}</div>;
}

export function Pill({ children, variant }: { children: ReactNode; variant?: "warn" | "human" }) {
  return <span className={`wb-pill${variant ? ` ${variant}` : ""}`}>{children}</span>;
}
