"use client";

import { useRouter } from "next/navigation";
import {
  Shield,
  Bot,
  FileSearch,
  Wallet,
  ShieldAlert,
  BrainCircuit,
  ArrowRight,
  Zap,
} from "lucide-react";
import { FileUploadZone } from "@/components/upload/FileUploadZone";
import { AgentPipeline } from "@/components/agents/AgentPipeline";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { useAnalysis } from "@/hooks/useAnalysis";

const agents = [
  {
    icon: FileSearch,
    name: "Evidence Agent",
    desc: "Verifies document authenticity, detects duplicates, extracts structured data",
    color: "text-blue-400 bg-blue-500/10 border-blue-500/30",
  },
  {
    icon: Wallet,
    name: "Affordability Agent",
    desc: "Analyzes income stability, spend patterns, and savings behavior",
    color: "text-violet-400 bg-violet-500/10 border-violet-500/30",
  },
  {
    icon: ShieldAlert,
    name: "Credit Risk Agent",
    desc: "Evaluates payment history, utilization, and debt load indicators",
    color: "text-rose-400 bg-rose-500/10 border-rose-500/30",
  },
  {
    icon: BrainCircuit,
    name: "Manager Agent",
    desc: "Aggregates reports, resolves conflicts, applies policy rules",
    color: "text-cyan-400 bg-cyan-500/10 border-cyan-500/30",
  },
];

export default function ApplicationPage() {
  const router = useRouter();
  const {
    phase,
    documents,
    error,
    addFiles,
    removeDocument,
    startAnalysis,
  } = useAnalysis();

  const isAnalyzing = phase === "analyzing";
  const canAnalyze = documents.length > 0 && !isAnalyzing;

  const handleAnalyze = async () => {
    await startAnalysis();
    router.push("/dashboard");
  };

  return (
    <div className="mx-auto max-w-5xl px-4 sm:px-6 py-8 sm:py-12">
      {/* Hero */}
      <div className="text-center mb-12 animate-fade-in">
        <div className="inline-flex items-center gap-2 rounded-full border border-cyan-500/30 bg-cyan-500/10 px-3 py-1 text-xs text-cyan-400 mb-6">
          <Zap className="h-3 w-3" />
          Multi-Agent Credibility Engine
        </div>
        <h1 className="text-3xl sm:text-4xl font-bold text-zinc-100 mb-4 tracking-tight">
          Explainable Fintech Credibility
        </h1>
        <p className="text-zinc-400 max-w-2xl mx-auto text-sm sm:text-base leading-relaxed">
          Upload your financial documents. Four specialized AI agents analyze
          your data in parallel, communicate findings, and produce a transparent,
          auditable credibility assessment — no black boxes.
        </p>
      </div>

      {/* Agent overview */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mb-10">
        {agents.map((agent) => {
          const Icon = agent.icon;
          return (
            <div
              key={agent.name}
              className={`flex items-start gap-3 rounded-xl border p-4 ${agent.color}`}
            >
              <Icon className="h-5 w-5 shrink-0 mt-0.5" />
              <div>
                <p className="text-sm font-semibold text-zinc-100">
                  {agent.name}
                </p>
                <p className="text-xs text-zinc-500 mt-0.5">{agent.desc}</p>
              </div>
            </div>
          );
        })}
      </div>

      {/* Upload section */}
      <Card className="mb-6 animate-fade-in">
        <div className="flex items-center gap-2 mb-5">
          <Shield className="h-5 w-5 text-cyan-400" />
          <h2 className="text-lg font-semibold text-zinc-100">
            Customer Application
          </h2>
        </div>

        <FileUploadZone
          onFilesSelected={addFiles}
          documents={documents}
          onRemove={removeDocument}
          disabled={isAnalyzing}
        />

        {error && (
          <p className="text-sm text-red-400 mt-3">{error}</p>
        )}

        <div className="flex items-center justify-between mt-6 pt-5 border-t border-zinc-800">
          <p className="text-xs text-zinc-500">
            {documents.length === 0
              ? "Upload at least one document to begin analysis"
              : `${documents.length} document${documents.length > 1 ? "s" : ""} ready for analysis`}
          </p>
          <Button
            onClick={handleAnalyze}
            disabled={!canAnalyze}
            loading={isAnalyzing}
            size="lg"
          >
            {isAnalyzing ? (
              <>
                <Bot className="h-4 w-4" />
                Agents Analyzing...
              </>
            ) : (
              <>
                Run Credibility Analysis
                <ArrowRight className="h-4 w-4" />
              </>
            )}
          </Button>
        </div>
      </Card>

      {/* Pipeline preview */}
      {isAnalyzing && (
        <Card className="animate-fade-in animate-pulse-glow">
          <div className="flex items-center gap-2 mb-4">
            <Bot className="h-4 w-4 text-cyan-400 animate-pulse" />
            <p className="text-sm text-zinc-300">
              Agents processing in parallel...
            </p>
          </div>
          <AgentPipeline currentStage="agent-analysis" />
        </Card>
      )}
    </div>
  );
}
