import { createClient } from "@supabase/supabase-js";

export function createStorageClient() {
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const key = process.env.SUPABASE_SERVICE_ROLE_KEY;

  if (!url || !key) return null;

  return createClient(url, key, {
    auth: { persistSession: false, autoRefreshToken: false },
  });
}

export function isStorageConfigured(): boolean {
  return Boolean(
    process.env.NEXT_PUBLIC_SUPABASE_URL &&
      process.env.SUPABASE_SERVICE_ROLE_KEY
  );
}

export async function uploadToStorage(
  caseId: string,
  filename: string,
  buffer: Buffer
): Promise<string | null> {
  if (!isStorageConfigured()) return null;

  const supabase = createStorageClient();
  if (!supabase) return null;

  const safeName = `${crypto.randomUUID().slice(0, 8)}_${filename}`;
  const path = `${caseId}/${safeName}`;

  const { error } = await supabase.storage
    .from("documents")
    .upload(path, buffer, { upsert: false });

  if (error) {
    console.error("Supabase storage upload error:", error.message);
    return null;
  }

  return path;
}
