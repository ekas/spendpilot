import { CheckCircle2, FileWarning, ShieldCheck } from "lucide-react";
import { ChartSection } from "./ChartSection";
import type { AnalysisResult } from "@/lib/types";

export function EvidencePanel({
  analysis,
}: {
  analysis: AnalysisResult;
}) {
  const evidence = analysis.evidence;
  return (
    <ChartSection
      title="Evidence And Verification"
      subtitle="Privacy-safe references only; document contents are excluded"
    >
      <div className="grid grid-cols-2 gap-3 mb-4">
        <Stat label="Evidence items" value={String(evidence.documentCount)} />
        <Stat
          label="Coverage"
          value={
            evidence.coverageScore === null
              ? "Not provided"
              : `${(evidence.coverageScore * 100).toFixed(1)}%`
          }
        />
        <Stat
          label="Verification"
          value={
            evidence.verificationState === "verified"
              ? "Verified"
              : "Not verified"
          }
        />
        <Stat
          label="Consistency findings"
          value={String(evidence.consistencyFlagCount)}
        />
      </div>

      <EvidenceList
        icon={FileWarning}
        label="Missing evidence"
        values={evidence.missingDocuments.map(humanize)}
        empty="No required evidence is missing"
      />
      <EvidenceList
        icon={ShieldCheck}
        label="Consistency findings"
        values={evidence.consistencyFindings}
        empty="No consistency finding was reported"
      />
      <EvidenceList
        icon={CheckCircle2}
        label="Hashed evidence references"
        values={evidence.evidenceRefs}
        empty="No evidence references were provided"
        mono
      />
    </ChartSection>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md bg-muted/50 p-3">
      <p className="text-[10px] text-muted-foreground">{label}</p>
      <p className="mt-1 text-sm font-semibold text-foreground">{value}</p>
    </div>
  );
}

function EvidenceList({
  icon: Icon,
  label,
  values,
  empty,
  mono = false,
}: {
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  values: string[];
  empty: string;
  mono?: boolean;
}) {
  return (
    <div className="border-t border-border py-3">
      <div className="mb-2 flex items-center gap-2 text-xs font-semibold text-foreground">
        <Icon className="h-3.5 w-3.5 text-muted-foreground" />
        {label}
      </div>
      <div className="flex flex-wrap gap-1.5">
        {(values.length ? values : [empty]).map((value) => (
          <span
            key={value}
            className={`rounded-md bg-muted px-2 py-1 text-[10px] text-muted-foreground ${mono ? "font-mono" : ""}`}
          >
            {value}
          </span>
        ))}
      </div>
    </div>
  );
}

function humanize(value: string): string {
  return value.replaceAll("_", " ");
}
