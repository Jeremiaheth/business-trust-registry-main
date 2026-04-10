import { formatPercent } from "../lib/filters";

interface ConfidenceMeterProps {
  label?: string;
  confidence: number;
}

export function ConfidenceMeter({
  label = "Confidence",
  confidence
}: ConfidenceMeterProps) {
  return (
    <div className="confidence-meter" aria-label={`${label} ${formatPercent(confidence)}`}>
      <div className="confidence-meter__header">
        <span>{label}</span>
        <strong>{formatPercent(confidence)}</strong>
      </div>
      <div className="confidence-meter__track">
        <span className="confidence-meter__fill" style={{ width: formatPercent(confidence) }} />
      </div>
    </div>
  );
}
