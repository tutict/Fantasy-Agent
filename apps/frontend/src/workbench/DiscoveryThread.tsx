/**
 * The interview transcript. Rendering only -- every string is inserted as a
 * text node, so backend content cannot inject markup.
 */

import { useEffect, useRef } from "react";

export interface ThreadEntry {
  kind: "ai" | "user";
  title: string;
  body?: string;
}

export function DiscoveryThread({ entries }: { entries: ThreadEntry[] }) {
  const scroller = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const node = scroller.current;
    if (node) node.scrollTop = node.scrollHeight;
  }, [entries.length]);

  return (
    <div className="wb-thread" ref={scroller} data-testid="discovery-thread" aria-live="polite">
      {entries.map((entry, index) => (
        <article className={`wb-bubble ${entry.kind}`} key={`${entry.kind}-${index}`}>
          <strong>{entry.title}</strong>
          <span>{entry.body}</span>
        </article>
      ))}
    </div>
  );
}
