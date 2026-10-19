/**
 * The interview transcript. Rendering only -- every string is inserted as a
 * text node, so backend content cannot inject markup.
 *
 * The retired static page and the first React cut both drew every message as a
 * bordered bubble with an uppercase role title, which made a six-question
 * interview read as a dozen boxes. This is the conversation page the product's
 * own chat surface uses instead: the assistant's messages are plain text (the
 * view header already names the assistant), and the user's are right-aligned
 * bubbles. One visual idea per message, no chrome on the majority of them.
 */

import { useEffect, useRef } from "react";

export interface ThreadEntry {
  kind: "ai" | "user";
  body: string;
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
        <article className={`wb-msg ${entry.kind}`} key={`${entry.kind}-${index}`}>
          <p>{entry.body}</p>
        </article>
      ))}
    </div>
  );
}
