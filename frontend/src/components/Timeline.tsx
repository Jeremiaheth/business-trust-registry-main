import { formatDate } from "../lib/filters";
import type { TimelineEvent } from "../lib/types";

interface TimelineProps {
  items: TimelineEvent[];
}

export function Timeline({ items }: TimelineProps) {
  return (
    <ol className="timeline">
      {items.map((item) => (
        <li className="timeline__item" key={`${item.timestamp}-${item.type}-${item.label}`}>
          <div className="timeline__marker" aria-hidden="true" />
          <div className="timeline__content">
            <p className="eyebrow">{item.type.replaceAll("_", " ")}</p>
            <h4>{item.label}</h4>
            <p>{item.description}</p>
            <div className="timeline__meta">
              <span>{formatDate(item.timestamp)}</span>
              <span>{item.status.replaceAll("_", " ")}</span>
              {item.source_url ? (
                <a href={item.source_url} rel="noreferrer" target="_blank">
                  Source
                </a>
              ) : null}
            </div>
          </div>
        </li>
      ))}
    </ol>
  );
}
