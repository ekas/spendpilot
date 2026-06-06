import {
  Upload,
  FileCheck,
  Bot,
  GitMerge,
  Scale,
  Gavel,
  UserCheck,
  CheckCircle2,
} from "lucide-react";
import { cn } from "@/lib/utils";
import type { AnalysisResult } from "@/lib/types";

const stages = [
  { id: "upload", label: "Upload", icon: Upload },
  { id: "validation", label: "Validation", icon: FileCheck },
  { id: "agent-analysis", label: "Agent Analysis", icon: Bot },
  { id: "aggregation", label: "Aggregation", icon: GitMerge },
  { id: "conflict-detection", label: "Conflicts", icon: Scale },
  { id: "policy-validation", label: "Policy", icon: Gavel },
  { id: "decision", label: "Decision", icon: CheckCircle2 },
  { id: "human-review", label: "Human Review", icon: UserCheck },
  { id: "complete", label: "Complete", icon: CheckCircle2 },
] as const;

interface AgentPipelineProps {
  currentStage: AnalysisResult["pipelineStage"];
}

export function AgentPipeline({ currentStage }: AgentPipelineProps) {
  const currentIndex = stages.findIndex((s) => s.id === currentStage);

  return (
    <div className="overflow-x-auto pb-2">
      <div className="flex items-center min-w-max gap-0">
        {stages.map((stage, i) => {
          const Icon = stage.icon;
          const isComplete = i < currentIndex;
          const isCurrent = i === currentIndex;
          const isPending = i > currentIndex;

          return (
            <div key={stage.id} className="flex items-center">
              <div className="flex flex-col items-center gap-1.5 px-2">
                <div
                  className={cn(
                    "flex h-8 w-8 items-center justify-center rounded-full border transition-colors",
                    isComplete && "bg-emerald-500/20 border-emerald-500/40 text-emerald-400",
                    isCurrent && "bg-cyan-500/20 border-cyan-500/40 text-cyan-400 ring-2 ring-cyan-500/20",
                    isPending && "bg-zinc-900 border-zinc-800 text-zinc-600"
                  )}
                >
                  <Icon className="h-3.5 w-3.5" />
                </div>
                <span
                  className={cn(
                    "text-[10px] font-medium whitespace-nowrap",
                    isComplete && "text-emerald-400",
                    isCurrent && "text-cyan-400",
                    isPending && "text-zinc-600"
                  )}
                >
                  {stage.label}
                </span>
              </div>
              {i < stages.length - 1 && (
                <div
                  className={cn(
                    "h-px w-6 sm:w-10",
                    i < currentIndex ? "bg-emerald-500/40" : "bg-zinc-800"
                  )}
                />
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
