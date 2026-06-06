import { TrendingUp, TrendingDown } from "lucide-react";
import { cn } from "@/lib/utils";

interface MetricCardProps {
  label: string;
  value: string;
  icon?: React.ComponentType<{ className?: string }>;
  accent?: "violet" | "emerald" | "blue" | "amber" | "rose";
  trendPercent?: string;
  trendLabel?: string;
  trend?: "up" | "down";
  progress?: number;
  progressSubtext?: string;
}

const iconStyles = {
  violet: {
    bg: "bg-violet-100 dark:bg-violet-500/15",
    icon: "text-violet-600 dark:text-violet-400",
    bar: "bg-violet-500",
  },
  emerald: {
    bg: "bg-emerald-100 dark:bg-emerald-500/15",
    icon: "text-emerald-600 dark:text-emerald-400",
    bar: "bg-emerald-500",
  },
  blue: {
    bg: "bg-blue-100 dark:bg-blue-500/15",
    icon: "text-blue-600 dark:text-blue-400",
    bar: "bg-blue-500",
  },
  amber: {
    bg: "bg-amber-100 dark:bg-amber-500/15",
    icon: "text-amber-600 dark:text-amber-400",
    bar: "bg-amber-500",
  },
  rose: {
    bg: "bg-rose-100 dark:bg-rose-500/15",
    icon: "text-rose-600 dark:text-rose-400",
    bar: "bg-rose-500",
  },
};

export function MetricCard({
  label,
  value,
  icon: Icon,
  accent = "violet",
  trendPercent,
  trendLabel,
  trend = "up",
  progress,
  progressSubtext,
}: MetricCardProps) {
  const styles = iconStyles[accent];
  const TrendIcon = trend === "up" ? TrendingUp : TrendingDown;
  const trendColor =
    trend === "up"
      ? "text-emerald-600 dark:text-emerald-500"
      : "text-red-600 dark:text-red-500";

  return (
    <div className="rounded-2xl border border-border bg-card p-5 shadow-sm">
      <div className="flex items-start justify-between gap-3 mb-4">
        <p className="text-sm font-medium text-muted-foreground">{label}</p>
        {Icon && (
          <div
            className={cn(
              "flex h-10 w-10 shrink-0 items-center justify-center rounded-full",
              styles.bg
            )}
          >
            <Icon className={cn("h-5 w-5", styles.icon)} />
          </div>
        )}
      </div>

      <p className="text-2xl sm:text-[1.75rem] font-bold text-foreground tracking-tight leading-none mb-4">
        {value}
      </p>

      {progress !== undefined && (
        <div className="mb-3">
          <div className="h-2 rounded-full bg-muted overflow-hidden">
            <div
              className={cn("h-full rounded-full transition-all", styles.bar)}
              style={{ width: `${Math.min(100, Math.max(0, progress))}%` }}
            />
          </div>
          {progressSubtext && (
            <p className="text-xs text-muted-foreground mt-1.5">
              {progressSubtext}
            </p>
          )}
        </div>
      )}

      {trendPercent && (
        <div className="flex items-center gap-1 flex-wrap text-xs">
          <TrendIcon className={cn("h-3.5 w-3.5", trendColor)} />
          <span className={cn("font-semibold", trendColor)}>{trendPercent}</span>
          {trendLabel && (
            <span className="text-muted-foreground">{trendLabel}</span>
          )}
        </div>
      )}
    </div>
  );
}
