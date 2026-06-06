import { Card, CardHeader } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { formatCurrency } from "@/lib/utils";
import type { SpendCategory } from "@/lib/types";

interface SpendBreakdownProps {
  categories: SpendCategory[];
}

export function SpendBreakdown({ categories }: SpendBreakdownProps) {
  const total = categories.reduce((sum, c) => sum + c.amount, 0);

  return (
    <Card>
      <CardHeader
        title="Spend Breakdown"
        subtitle={`Total monthly spend: ${formatCurrency(total)}`}
      />

      <div className="space-y-3">
        {categories.map((cat) => (
          <div key={cat.name}>
            <div className="flex items-center justify-between mb-1">
              <div className="flex items-center gap-2">
                <span className="text-sm text-foreground/90">{cat.name}</span>
                {cat.riskFlag && (
                  <Badge variant="warning">Risk Flag</Badge>
                )}
                {cat.trend === "up" && (
                  <span className="text-[10px] text-amber-500">↑</span>
                )}
                {cat.trend === "down" && (
                  <span className="text-[10px] text-emerald-500">↓</span>
                )}
              </div>
              <div className="text-right">
                <span className="text-sm font-mono text-foreground">
                  {formatCurrency(cat.amount)}
                </span>
                <span className="text-xs text-muted-foreground/80 ml-2">
                  {cat.percentage.toFixed(1)}%
                </span>
              </div>
            </div>
            <div className="h-1.5 rounded-full bg-muted overflow-hidden">
              <div
                className={`h-full rounded-full transition-all ${
                  cat.riskFlag ? "bg-amber-500" : "bg-cyan-600"
                }`}
                style={{ width: `${cat.percentage}%` }}
              />
            </div>
          </div>
        ))}
      </div>
    </Card>
  );
}
