import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

/** Only ever redirect to an in-app path. Anything absolute ("https://…", "//evil.com")
 * or pointing back into the auth flow ("/auth/callback", "/login") is replaced with the
 * fallback — the latter is what caused ?next=/auth/callback redirect loops. */
export function safeRedirectPath(raw: string | null, fallback = "/jobs"): string {
  if (!raw || !raw.startsWith("/") || raw.startsWith("//")) return fallback;
  if (raw.startsWith("/auth") || raw.startsWith("/login")) return fallback;
  return raw;
}
