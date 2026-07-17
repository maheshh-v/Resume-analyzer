import { ApiError } from "./api-client";

/** Single place that turns any thrown error into copy fit for the UI. Raw fetch/stack
 * messages must never reach a user. */
export function friendlyError(error: unknown, fallback = "Something went wrong. Please try again."): string {
  if (error instanceof ApiError) {
    if (error.status === 0) return error.message; // already friendly (connectivity)
    if (error.status === 503)
      return error.message || "The AI model is temporarily overloaded. Please try again in a minute.";
    if (error.status === 401) return "Your session has expired. Please sign in again.";
    if (error.status === 403) return "You don't have access to this.";
    if (error.status === 404) return "We couldn't find that — it may have been deleted.";
    if (error.message && !/failed to fetch/i.test(error.message)) return error.message;
    return fallback;
  }
  if (error instanceof Error && error.message && !/failed to fetch|networkerror|load failed/i.test(error.message)) {
    return error.message;
  }
  return fallback;
}
