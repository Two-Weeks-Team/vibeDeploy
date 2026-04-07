/**
 * Authenticated fetch wrapper for API calls to the vibeDeploy backend.
 *
 * The API key is injected server-side via VIBEDEPLOY_API_KEY env var.
 * This key must NEVER be exposed to the browser (no NEXT_PUBLIC_ prefix).
 */

const API_KEY = process.env.VIBEDEPLOY_API_KEY ?? "";

export function authHeaders(extra?: Record<string, string>): Record<string, string> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...extra,
  };
  if (API_KEY) {
    headers["X-API-Key"] = API_KEY;
  }
  return headers;
}

export async function authenticatedFetch(url: string, init?: RequestInit): Promise<Response> {
  const merged: RequestInit = {
    ...init,
    headers: {
      ...authHeaders(),
      ...(init?.headers as Record<string, string> | undefined),
    },
  };
  return fetch(url, merged);
}

export function appendApiKey(url: string): string {
  if (!API_KEY) return url;
  const separator = url.includes("?") ? "&" : "?";
  return `${url}${separator}api_key=${encodeURIComponent(API_KEY)}`;
}
