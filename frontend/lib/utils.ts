import { clsx, type ClassValue } from "clsx";
import type { AgentId, DecisionOutcome, RiskLevel } from "./types";

export function cn(...inputs: ClassValue[]) {
  return clsx(inputs);
}

export function formatCurrency(amount: number): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(amount);
}

export function formatPercent(value: number, decimals = 1): string {
  return `${value.toFixed(decimals)}%`;
}

export function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function formatDate(iso: string): string {
  return new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(iso));
}

export function getRiskColor(risk: RiskLevel): string {
  const map: Record<RiskLevel, string> = {
    low: "text-emerald-400",
    medium: "text-amber-400",
    high: "text-orange-400",
    critical: "text-red-400",
  };
  return map[risk];
}

export function getRiskBg(risk: RiskLevel): string {
  const map: Record<RiskLevel, string> = {
    low: "bg-emerald-500/10 border-emerald-500/30",
    medium: "bg-amber-500/10 border-amber-500/30",
    high: "bg-orange-500/10 border-orange-500/30",
    critical: "bg-red-500/10 border-red-500/30",
  };
  return map[risk];
}

export function getDecisionColor(outcome: DecisionOutcome): string {
  const map: Record<DecisionOutcome, string> = {
    approved: "text-emerald-400",
    "approved-with-conditions": "text-amber-400",
    "review-required": "text-orange-400",
    declined: "text-red-400",
    pending: "text-zinc-400",
  };
  return map[outcome];
}

export function getAgentLabel(id: AgentId): string {
  const map: Record<AgentId, string> = {
    evidence: "Evidence Agent",
    affordability: "Affordability Agent",
    "credit-risk": "Credit Risk Agent",
    manager: "Manager Agent",
  };
  return map[id];
}

export function getAgentColor(id: AgentId): string {
  const map: Record<AgentId, string> = {
    evidence: "text-blue-400",
    affordability: "text-violet-400",
    "credit-risk": "text-rose-400",
    manager: "text-cyan-400",
  };
  return map[id];
}

export function getScoreColor(score: number): string {
  if (score >= 80) return "text-emerald-400";
  if (score >= 60) return "text-amber-400";
  if (score >= 40) return "text-orange-400";
  return "text-red-400";
}

export function delay(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}
