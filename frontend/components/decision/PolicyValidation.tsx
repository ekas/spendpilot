import { Gavel, CheckCircle2, XCircle, AlertTriangle, Clock } from "lucide-react";
import { Card, CardHeader } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import type { PolicyCheck } from "@/lib/types";

const statusConfig = {
  pass: { icon: CheckCircle2, color: "text-emerald-400", variant: "success" as const },
  fail: { icon: XCircle, color: "text-red-400", variant: "danger" as const },
  warning: { icon: AlertTriangle, color: "text-amber-400", variant: "warning" as const },
  pending: { icon: Clock, color: "text-muted-foreground", variant: "muted" as const },
};

interface PolicyValidationProps {
  checks: PolicyCheck[];
}

export function PolicyValidation({ checks }: PolicyValidationProps) {
  const passed = checks.filter((c) => c.status === "pass").length;
  const failed = checks.filter((c) => c.status === "fail").length;

  return (
    <Card>
      <CardHeader
        title="Policy Validation"
        subtitle={`${passed} passed · ${failed} failed · ${checks.length} total`}
        action={
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-violet-500/10">
            <Gavel className="h-4 w-4 text-violet-400" />
          </div>
        }
      />

      <div className="space-y-2">
        {checks.map((check) => {
          const config = statusConfig[check.status];
          const Icon = config.icon;

          return (
            <div
              key={check.id}
              className="flex items-start gap-3 rounded-lg border border-border bg-surface px-3 py-2.5"
            >
              <Icon className={`h-4 w-4 mt-0.5 shrink-0 ${config.color}`} />
              <div className="flex-1 min-w-0">
                <p className="text-sm text-foreground">{check.rule}</p>
                <p className="text-xs text-muted-foreground mt-0.5">{check.details}</p>
              </div>
              <Badge variant={config.variant}>{check.status}</Badge>
            </div>
          );
        })}
      </div>
    </Card>
  );
}
