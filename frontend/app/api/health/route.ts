import { NextResponse } from "next/server";
import { isDatabaseConfigured, prisma } from "@/lib/prisma";
import { isStorageConfigured } from "@/lib/supabase/storage";

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

  return NextResponse.json({
    status: "ok",
    service: "SpendPilot API",
    orm: "prisma",
    database,
    storage: isStorageConfigured() ? "supabase" : "disabled",
  });
}
