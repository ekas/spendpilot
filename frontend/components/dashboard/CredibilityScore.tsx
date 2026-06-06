import { Card, CardHeader } from "@/components/ui/Card";
import { ScoreRing, Progress } from "@/components/ui/Progress";
import { RiskBadge } from "@/components/ui/Badge";
import type { CredibilityBreakdown } from "@/lib/types";

interface CredibilityScoreProps {
  credibility: CredibilityBreakdown;
}

export function CredibilityScore({ credibility }: CredibilityScoreProps) {
  return (
    <Card>
      <CardHeader
        title="Credibility Score"
        subtitle="Transparent, interpretable multi-agent assessment"
        action={<RiskBadge level={credibility.riskLevel} />}
      />

      <div className="flex flex-col sm:flex-row items-center gap-6">
        <ScoreRing score={credibility.overallScore} label="/ 100" />

        <div className="flex-1 w-full space-y-3">
          <Progress
            value={credibility.evidenceScore}
            label="Evidence Agent"
            size="sm"
          />
          <Progress
            value={credibility.affordabilityScore}
            label="Affordability Agent"
            size="sm"
          />
          <Progress
            value={credibility.creditRiskScore}
            label="Credit Risk Agent"
            size="sm"
          />
          <div className="pt-2 border-t border-zinc-800">
            <p className="text-xs text-zinc-500">
              Aggregate confidence:{" "}
              <span className="font-mono text-zinc-300">
                {(credibility.confidence * 100).toFixed(0)}%
              </span>
            </p>
          </div>
        </div>
      </div>
    </Card>
  );
}
