import { prisma, isDatabaseConfigured } from "@/lib/prisma";
import type { CaseResult, PeriodSummary } from "./schemas";
import type { Prisma } from "@prisma/client";

const memoryStore = new Map<string, CaseResult>();

function rowToCase(row: {
  caseId: string;
  payloadJson: Prisma.JsonValue;
  createdAt: Date;
}): CaseResult {
  const payload = row.payloadJson as unknown as CaseResult;
  return {
    ...payload,
    case_id: row.caseId,
    created_at: row.createdAt.toISOString(),
  };
}

export async function initDb(): Promise<void> {
  if (!isDatabaseConfigured()) return;
  await prisma.$connect();
}

export async function saveCase(caseResult: CaseResult): Promise<void> {
  memoryStore.set(caseResult.case_id, caseResult);

  if (!isDatabaseConfigured()) return;

  try {
    await prisma.case.upsert({
      where: { caseId: caseResult.case_id },
      create: {
        caseId: caseResult.case_id,
        status: caseResult.status,
        requiresHumanReview: caseResult.policy_decision.requires_human_review,
        payloadJson: caseResult as unknown as Prisma.InputJsonValue,
      },
      update: {
        status: caseResult.status,
        requiresHumanReview: caseResult.policy_decision.requires_human_review,
        payloadJson: caseResult as unknown as Prisma.InputJsonValue,
      },
    });
  } catch (err) {
    console.error("Prisma saveCase error:", err);
  }
}

export async function getCase(caseId: string): Promise<CaseResult | null> {
  if (memoryStore.has(caseId)) {
    return memoryStore.get(caseId)!;
  }

  if (!isDatabaseConfigured()) return null;

  try {
    const row = await prisma.case.findUnique({
      where: { caseId },
      select: { caseId: true, payloadJson: true, createdAt: true },
    });

    if (!row) return null;

    const result = rowToCase(row);
    memoryStore.set(caseId, result);
    return result;
  } catch (err) {
    console.error("Prisma getCase error:", err);
    return null;
  }
}

export async function listCases(): Promise<CaseResult[]> {
  if (isDatabaseConfigured()) {
    try {
      const rows = await prisma.case.findMany({
        orderBy: { createdAt: "desc" },
        select: { caseId: true, payloadJson: true, createdAt: true },
      });

      if (rows.length) {
        return rows.map(rowToCase);
      }
    } catch (err) {
      console.error("Prisma listCases error:", err);
    }
  }

  return Array.from(memoryStore.values()).sort(
    (a, b) =>
      new Date(b.created_at ?? 0).getTime() -
      new Date(a.created_at ?? 0).getTime()
  );
}

export async function listReviewQueue(): Promise<CaseResult[]> {
  if (isDatabaseConfigured()) {
    try {
      const rows = await prisma.case.findMany({
        where: { requiresHumanReview: true },
        orderBy: { createdAt: "desc" },
        select: { caseId: true, payloadJson: true, createdAt: true },
      });

      if (rows.length) {
        return rows.map(rowToCase);
      }
    } catch (err) {
      console.error("Prisma listReviewQueue error:", err);
    }
  }

  return Array.from(memoryStore.values()).filter(
    (c) => c.policy_decision.requires_human_review
  );
}

export async function caseCount(): Promise<number> {
  if (isDatabaseConfigured()) {
    try {
      return await prisma.case.count();
    } catch (err) {
      console.error("Prisma caseCount error:", err);
    }
  }

  return memoryStore.size;
}

export async function setHumanDecision(
  caseId: string,
  decision: string
): Promise<CaseResult | null> {
  const existing = await getCase(caseId);
  if (!existing) return null;

  const updated: CaseResult = {
    ...existing,
    status: decision,
    policy_decision: {
      ...existing.policy_decision,
      requires_human_review: false,
      reason: `Human reviewer decision: ${decision}`,
    },
  };

  await saveCase(updated);
  return updated;
}

export async function listCasesBetween(
  startIso: string,
  endIso: string
): Promise<CaseResult[]> {
  if (isDatabaseConfigured()) {
    try {
      const rows = await prisma.case.findMany({
        where: {
          createdAt: {
            gte: new Date(startIso),
            lt: new Date(endIso),
          },
        },
        orderBy: { createdAt: "desc" },
        select: { caseId: true, payloadJson: true, createdAt: true },
      });

      return rows.map(rowToCase);
    } catch (err) {
      console.error("Prisma listCasesBetween error:", err);
    }
  }

  const start = new Date(startIso).getTime();
  const end = new Date(endIso).getTime();
  return Array.from(memoryStore.values()).filter((c) => {
    const t = new Date(c.created_at ?? 0).getTime();
    return t >= start && t < end;
  });
}

function safeRate(part: number, total: number): number {
  if (total === 0) return 0;
  return Math.round((part / total) * 10000) / 10000;
}

export function summarizePeriod(
  cases: CaseResult[],
  startDate: string,
  endDate: string
): PeriodSummary {
  const totals: Record<string, number> = { APPROVE: 0, REFER: 0, REJECT: 0 };
  let humanReviewCount = 0;
  const scoreAcc: Record<string, number> = {};
  const scoreCounts: Record<string, number> = {};

  for (const c of cases) {
    totals[c.status] = (totals[c.status] ?? 0) + 1;
    if (c.policy_decision.requires_human_review) humanReviewCount++;

    for (const report of c.specialist_reports) {
      scoreAcc[report.agent_name] =
        (scoreAcc[report.agent_name] ?? 0) + report.score;
      scoreCounts[report.agent_name] =
        (scoreCounts[report.agent_name] ?? 0) + 1;
    }
  }

  const avgScores: Record<string, number> = {};
  for (const name of Object.keys(scoreAcc).sort()) {
    avgScores[name] =
      Math.round((scoreAcc[name] / scoreCounts[name]) * 10000) / 10000;
  }

  const totalCases = cases.length;

  return {
    start_date: startDate,
    end_date: endDate,
    total_cases: totalCases,
    decision_counts: totals,
    decision_rates: {
      APPROVE: safeRate(totals.APPROVE ?? 0, totalCases),
      REFER: safeRate(totals.REFER ?? 0, totalCases),
      REJECT: safeRate(totals.REJECT ?? 0, totalCases),
    },
    human_review_rate: safeRate(humanReviewCount, totalCases),
    avg_specialist_scores: avgScores,
  };
}

export async function saveDocumentRecord(doc: {
  case_id: string;
  file_name: string;
  file_type: string;
  file_size: number;
  storage_path?: string;
  extracted_text?: string;
  document_signals?: Record<string, unknown>;
}): Promise<void> {
  if (!isDatabaseConfigured()) return;

  try {
    await prisma.document.create({
      data: {
        caseId: doc.case_id,
        fileName: doc.file_name,
        fileType: doc.file_type,
        fileSize: BigInt(doc.file_size),
        storagePath: doc.storage_path,
        extractedText: doc.extracted_text,
        documentSignals: (doc.document_signals ??
          {}) as Prisma.InputJsonValue,
      },
    });
  } catch (err) {
    console.error("Prisma saveDocument error:", err);
  }
}
