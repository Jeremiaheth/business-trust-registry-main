import { ConfidenceMeter } from "./ConfidenceMeter";
import { formatPercent } from "../lib/filters";

interface ScoreCardProps {
  score: number;
  confidence: number;
  band: string;
  headline?: string;
}

export function ScoreCard({ score, confidence, band, headline = "Trust score" }: ScoreCardProps) {
  return (
    <article className="score-card">
      <p className="eyebrow">{headline}</p>
      <div className="score-card__value">{formatPercent(score)}</div>
      <p className="score-card__band">{band.replace("_", " ")} band</p>
      <ConfidenceMeter confidence={confidence} />
    </article>
  );
}
