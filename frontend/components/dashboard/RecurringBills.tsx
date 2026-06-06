import { RefreshCw, AlertTriangle, CheckCircle2 } from "lucide-react";
import { Card, CardHeader } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { formatCurrency } from "@/lib/utils";
import type { RecurringBill } from "@/lib/types";

interface RecurringBillsProps {
  bills: RecurringBill[];
}

export function RecurringBills({ bills }: RecurringBillsProps) {
  const total = bills.reduce((sum, b) => sum + b.amount, 0);
  const duplicateCount = bills.filter((b) => b.duplicateRisk).length;

  return (
    <Card>
      <CardHeader
        title="Recurring Bills"
        subtitle={`${bills.length} recurring · ${formatCurrency(total)}/mo`}
        action={
          duplicateCount > 0 ? (
            <Badge variant="warning">
              {duplicateCount} duplicate risk
            </Badge>
          ) : undefined
        }
      />

      <div className="space-y-2">
        {bills.map((bill) => (
          <div
            key={bill.vendor}
            className="flex items-center gap-3 rounded-lg border border-border bg-surface px-3 py-2.5"
          >
            <RefreshCw className="h-3.5 w-3.5 text-muted-foreground/80 shrink-0" />
            <div className="flex-1 min-w-0">
              <p className="text-sm text-foreground truncate">{bill.vendor}</p>
              <p className="text-[10px] text-muted-foreground/80">
                {bill.frequency} · next {new Date(bill.nextDue).toLocaleDateString()}
              </p>
            </div>
            <span className="text-sm font-mono text-foreground/90 shrink-0">
              {formatCurrency(bill.amount)}
            </span>
            {bill.duplicateRisk ? (
              <AlertTriangle className="h-3.5 w-3.5 text-amber-400 shrink-0" />
            ) : bill.verified ? (
              <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400 shrink-0" />
            ) : null}
          </div>
        ))}
      </div>
    </Card>
  );
}
