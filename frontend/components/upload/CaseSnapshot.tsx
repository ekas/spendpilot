import {
  User,
  FileCheck,
  DollarSign,
  TrendingUp,
  AlertTriangle,
  CheckCircle2,
} from "lucide-react";
import { Card, CardHeader } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { formatCurrency, formatPercent } from "@/lib/utils";
import type { CaseSnapshot as CaseSnapshotType } from "@/lib/types";

interface CaseSnapshotProps {
  snapshot: CaseSnapshotType;
}

export function CaseSnapshot({ snapshot }: CaseSnapshotProps) {
  const validationVariant =
    snapshot.validationStatus === "valid"
      ? "success"
      : snapshot.validationStatus === "invalid"
        ? "danger"
        : snapshot.validationStatus === "partial"
          ? "warning"
          : "muted";

  return (
    <Card>
      <CardHeader
        title="Case Snapshot"
        subtitle={`${snapshot.id} · Applied ${new Date(snapshot.applicationDate).toLocaleDateString()}`}
        action={
          <Badge variant={validationVariant}>
            {snapshot.validationStatus === "valid" ? (
              <span className="flex items-center gap-1">
                <CheckCircle2 className="h-3 w-3" /> Validated
              </span>
            ) : (
              snapshot.validationStatus
            )}
          </Badge>
        }
      />

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-4">
        <SnapshotMetric
          icon={User}
          label="Applicant"
          value={snapshot.applicantName}
        />
        <SnapshotMetric
          icon={DollarSign}
          label="Monthly Income"
          value={formatCurrency(snapshot.monthlyIncome)}
          mono
        />
        <SnapshotMetric
          icon={TrendingUp}
          label="Savings Rate"
          value={formatPercent(snapshot.savingsRate * 100)}
          mono
        />
        <SnapshotMetric
          icon={FileCheck}
          label="Documents"
          value={`${snapshot.documents.length} uploaded`}
        />
      </div>

      <div className="grid grid-cols-2 gap-4 pt-4 border-t border-border">
        <div>
          <p className="text-xs text-muted-foreground mb-1">Monthly Expenses</p>
          <p className="text-sm font-mono text-foreground">
            {formatCurrency(snapshot.monthlyExpenses)}
          </p>
        </div>
        <div>
          <p className="text-xs text-muted-foreground mb-1">Debt-to-Income</p>
          <p className="text-sm font-mono text-foreground">
            {formatPercent(snapshot.debtToIncome * 100)}
          </p>
        </div>
      </div>

      {snapshot.validationIssues.length > 0 && (
        <div className="mt-4 pt-4 border-t border-border space-y-2">
          {snapshot.validationIssues.map((issue, i) => (
            <div key={i} className="flex items-start gap-2 text-xs text-amber-400">
              <AlertTriangle className="h-3.5 w-3.5 mt-0.5 shrink-0" />
              {issue}
            </div>
          ))}
        </div>
      )}
    </Card>
  );
}

function SnapshotMetric({
  icon: Icon,
  label,
  value,
  mono,
}: {
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  value: string;
  mono?: boolean;
}) {
  return (
    <div>
      <div className="flex items-center gap-1.5 mb-1">
        <Icon className="h-3 w-3 text-muted-foreground/80" />
        <p className="text-xs text-muted-foreground">{label}</p>
      </div>
      <p
        className={`text-sm font-medium text-foreground ${mono ? "font-mono" : ""}`}
      >
        {value}
      </p>
    </div>
  );
}
