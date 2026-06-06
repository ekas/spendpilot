import { cn, getScoreColor } from "@/lib/utils";

interface ProgressProps {
  value: number;
  max?: number;
  label?: string;
  showValue?: boolean;
  size?: "sm" | "md";
  className?: string;
}

export function Progress({
  value,
  max = 100,
  label,
  showValue = true,
  size = "md",
  className,
}: ProgressProps) {
  const pct = Math.min(100, Math.max(0, (value / max) * 100));

  return (
    <div className={cn("w-full", className)}>
      {(label || showValue) && (
        <div className="flex justify-between items-center mb-1.5">
          {label && <span className="text-xs text-zinc-500">{label}</span>}
          {showValue && (
            <span className={cn("text-xs font-mono font-medium", getScoreColor(value))}>
              {value}
            </span>
          )}
        </div>
      )}
      <div
        className={cn(
          "w-full rounded-full bg-zinc-800 overflow-hidden",
          size === "sm" ? "h-1.5" : "h-2"
        )}
      >
        <div
          className={cn(
            "h-full rounded-full transition-all duration-700",
            pct >= 80
              ? "bg-emerald-500"
              : pct >= 60
                ? "bg-amber-500"
                : pct >= 40
                  ? "bg-orange-500"
                  : "bg-red-500"
          )}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}

export function ScoreRing({
  score,
  size = 120,
  label,
}: {
  score: number;
  size?: number;
  label?: string;
}) {
  const radius = (size - 12) / 2;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (score / 100) * circumference;

  return (
    <div className="relative inline-flex items-center justify-center">
      <svg width={size} height={size} className="-rotate-90">
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke="currentColor"
          strokeWidth={6}
          className="text-zinc-800"
        />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke="currentColor"
          strokeWidth={6}
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          strokeLinecap="round"
          className={cn(
            "transition-all duration-1000",
            score >= 80
              ? "text-emerald-500"
              : score >= 60
                ? "text-amber-500"
                : score >= 40
                  ? "text-orange-500"
                  : "text-red-500"
          )}
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className={cn("text-3xl font-bold font-mono", getScoreColor(score))}>
          {score}
        </span>
        {label && <span className="text-xs text-zinc-500 mt-0.5">{label}</span>}
      </div>
    </div>
  );
}
