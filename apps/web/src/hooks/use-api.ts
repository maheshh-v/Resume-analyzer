"use client";

import { useMemo } from "react";
import { createApiClient } from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";

/** Recruiter-side API client bound to the current Supabase access token. Memoized so
 * TanStack Query keys built from the returned functions stay stable across renders. */
export function useApi() {
  const { session } = useAuth();
  return useMemo(() => createApiClient(session?.access_token ?? null), [session?.access_token]);
}
