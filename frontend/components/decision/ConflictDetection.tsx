import { Scale, CheckCircle2, AlertTriangle } from "lucide-react";
import { Card, CardHeader } from "@/components/ui/Card";
import { Badge, RiskBadge } from "@/components/ui/Badge";
import { getAgentLabel } from "@/lib/utils";
import type { ConflictItem } from "@/lib/types";

interface ConflictDetectionProps {
  conflicts: ConflictItem[];
}

export function ConflictDetection({ conflicts }: ConflictDetectionProps) {
  const resolved = conflicts.filter((c) => c.resolved).length;

  return (
    <Card>
      <CardHeader
        title="Conflict Detection"
        subtitle={`${resolved}/${conflicts.length} conflicts resolved`}
        action={
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-amber-500/10">
            <Scale className="h-4 w-4 text-amber-400" />
          </div>
        }
      />

      {conflicts.length === 0 ? (
        <div className="flex items-center gap-2 text-sm text-emerald-400 py-4">
          <CheckCircle2 className="h-4 w-4" />
          No agent conflicts detected
        </div>
      ) : (
        <div className="space-y-3">
          {conflicts.map((conflict) => (
            <div
              key={conflict.id}
              className="rounded-lg border border-border bg-surface p-4"
            >
              <div className="flex items-center gap-2 mb-2 flex-wrap">
                <RiskBadge level={conflict.severity} />
                {conflict.agents.map((agent) => (
                  <Badge key={agent} variant="info">
                    {getAgentLabel(agent)}
                  </Badge>
                ))}
                {conflict.resolved ? (
                  <Badge variant="success" className="ml-auto">
                    <CheckCircle2 className="h-3 w-3 mr-1" />
                    Resolved
                  </Badge>
                ) : (
                  <Badge variant="danger" className="ml-auto">
                    <AlertTriangle className="h-3 w-3 mr-1" />
                    Unresolved
                  </Badge>
                )}
              </div>
              <p className="text-sm font-medium text-foreground mb-1">
                {conflict.topic}
              </p>
              <p className="text-xs text-muted-foreground mb-2">{conflict.description}</p>
              {conflict.resolution && (
                <div className="rounded-md bg-emerald-500/5 border border-emerald-500/20 px-3 py-2">
                  <p className="text-xs text-emerald-400">{conflict.resolution}</p>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </Card>
  );
}
