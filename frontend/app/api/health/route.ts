import { NextResponse } from "next/server";
import { isDatabaseConfigured, prisma } from "@/lib/prisma";
import { isStorageConfigured } from "@/lib/supabase/storage";
import { getModelingHealth } from "@/lib/backend/modeling-client";

export async function GET() {
  let database: "connected" | "configured" | "memory-fallback" = "memory-fallback";

  if (isDatabaseConfigured()) {
    try {
      await prisma.$queryRaw`SELECT 1`;
      database = "connected";
    } catch {
      database = "configured";
    }
  }

  let modeling: Record<string, unknown> = { status: "unavailable" };
  try {
    modeling = await getModelingHealth();
  } catch {
    // Health remains useful for the UI even while the Python service is down.
  }

  return NextResponse.json({
    status: "ok",
    service: "SpendPilot API",
    orm: "prisma",
    database,
    storage: isStorageConfigured() ? "supabase" : "disabled",
    modeling,
  });
}
