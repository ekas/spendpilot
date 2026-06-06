import { Lightbulb, ArrowRight } from "lucide-react";
import { Card, CardHeader } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { formatCurrency } from "@/lib/utils";
import type { SavingsOpportunity } from "@/lib/types";

interface SavingsOpportunitiesProps {
  opportunities: SavingsOpportunity[];
}

export function SavingsOpportunities({ opportunities }: SavingsOpportunitiesProps) {
  const totalSavings = opportunities.reduce(
    (sum, o) => sum + o.potentialSavings,
    0
  );

  return (
    <Card>
      <CardHeader
        title="Savings Opportunities"
        subtitle={`Potential savings: ${formatCurrency(totalSavings)}/mo`}
        action={
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-amber-500/10">
            <Lightbulb className="h-4 w-4 text-amber-400" />
          </div>
        }
      />

      <div className="space-y-3">
        {opportunities.map((opp) => (
          <div
            key={opp.id}
            className="rounded-lg border border-zinc-800 bg-zinc-900/30 p-3"
          >
            <div className="flex items-center gap-2 mb-1.5">
              <span className="text-sm font-medium text-zinc-200">
                {opp.title}
              </span>
              <Badge variant="success" className="ml-auto">
                {formatCurrency(opp.potentialSavings)}/mo
              </Badge>
            </div>
            <div className="flex items-center gap-2 mb-2">
              <Badge variant="muted">{opp.category}</Badge>
              <span className="text-[10px] text-zinc-600 font-mono">
                {(opp.confidence * 100).toFixed(0)}% confidence
              </span>
            </div>
            <div className="flex items-start gap-1.5 text-xs text-zinc-500">
              <ArrowRight className="h-3 w-3 mt-0.5 shrink-0 text-zinc-600" />
              {opp.action}
            </div>
          </div>
        ))}
      </div>
    </Card>
  );
}
