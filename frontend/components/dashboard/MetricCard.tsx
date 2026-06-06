import { TrendingUp, TrendingDown, Minus } from "lucide-react";
import { Card } from "@/components/ui/Card";
import { cn } from "@/lib/utils";

interface MetricCardProps {
  label: string;
  value: string;
  subtext?: string;
  trend?: "up" | "down" | "stable";
  trendLabel?: string;
  icon?: React.ComponentType<{ className?: string }>;
  accent?: "cyan" | "emerald" | "amber" | "rose" | "violet";
}

const accentMap = {
  cyan: "text-cyan-400",
  emerald: "text-emerald-400",
  amber: "text-amber-400",
  rose: "text-rose-400",
  violet: "text-violet-400",
};

export function MetricCard({
  label,
  value,
  subtext,
  trend,
  trendLabel,
  icon: Icon,
  accent = "cyan",
}: MetricCardProps) {
  const TrendIcon =
    trend === "up" ? TrendingUp : trend === "down" ? TrendingDown : Minus;

  return (
    <Card padding="sm">
      <div className="flex items-start justify-between mb-2">
        <p className="text-xs text-zinc-500">{label}</p>
        {Icon && <Icon className={cn("h-4 w-4", accentMap[accent])} />}
      </div>
      <p className={cn("text-xl font-bold font-mono", accentMap[accent])}>
        {value}
      </p>
      {(subtext || trend) && (
        <div className="flex items-center gap-1.5 mt-1.5">
          {trend && (
            <TrendIcon
              className={cn(
                "h-3 w-3",
                trend === "up"
                  ? "text-emerald-400"
                  : trend === "down"
                    ? "text-red-400"
                    : "text-zinc-500"
              )}
            />
          )}
          <p className="text-[11px] text-zinc-500">
            {trendLabel ?? subtext}
          </p>
        </div>
      )}
    </Card>
  );
}
