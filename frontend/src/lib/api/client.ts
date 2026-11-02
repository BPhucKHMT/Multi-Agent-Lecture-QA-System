export const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL ?? "").replace(/\/$/, "");
const DEFAULT_TIMEOUT_MS = 360000;

export const AUTH_EXPIRED_EVENT = "auth:expired";
let refreshInFlight: Promise<void> | null = null;

function resolveTimeoutMs(): number {
  const value = Number(import.meta.env.VITE_API_TIMEOUT_MS);
  if (!Number.isFinite(value) || value <= 0) {
    return DEFAULT_TIMEOUT_MS;
  }
  return value;
}

export async function withTimeout<TResponse>(
  run: (signal: AbortSignal) => Promise<TResponse>,
  timeoutMs: number,
): Promise<TResponse> {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

  try {
    return await run(controller.signal);
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") {
      throw new Error(`Request timed out after ${timeoutMs}ms`);
    }
    throw error;
  } finally {
    clearTimeout(timeoutId);
  }
}

function refreshAccessToken(): Promise<void> {
  if (refreshInFlight) return refreshInFlight;
  const refreshToken = localStorage.getItem("refresh_token");
  let invalidateSession = !refreshToken;

  refreshInFlight = (async () => {
    try {
      if (!refreshToken) throw new Error("No refresh token available");
      const response = await withTimeout(
        (signal) => fetch(`${API_BASE_URL}/api/v1/auth/refresh`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ refresh_token: refreshToken }),
          signal,
        }),
        resolveTimeoutMs(),
      );
      invalidateSession = response.status === 401 || response.status === 403;
      if (!response.ok) throw new Error(`Token refresh failed with status ${response.status}`);
      invalidateSession = true;
      const tokens = await response.json();
      if (
        typeof tokens.access_token !== "string" || !tokens.access_token ||
        typeof tokens.refresh_token !== "string" || !tokens.refresh_token
      ) {
        throw new Error("Invalid token refresh response");
      }
      if (localStorage.getItem("refresh_token") !== refreshToken) {
        throw new Error("Session changed during token refresh");
      }
      localStorage.setItem("access_token", tokens.access_token);
      localStorage.setItem("refresh_token", tokens.refresh_token);
    } catch (error) {
      if (invalidateSession && localStorage.getItem("refresh_token") === refreshToken) {
        localStorage.removeItem("access_token");
        localStorage.removeItem("refresh_token");
        window.dispatchEvent(new Event(AUTH_EXPIRED_EVENT));
      }
      throw error;
    }
  })().finally(() => {
    refreshInFlight = null;
  });

  return refreshInFlight;
}

export async function authenticatedFetch(path: string, init: RequestInit = {}): Promise<Response> {
  const token = localStorage.getItem("access_token");
  const send = (accessToken: string | null) => {
    const headers = new Headers(init.headers);
    if (accessToken) headers.set("Authorization", `Bearer ${accessToken}`);
    return fetch(`${API_BASE_URL}${path}`, { ...init, headers });
  };
  const response = await send(token);
  if (
    response.status !== 401 ||
    /^\/api\/v1\/auth\/(?:login|register|refresh)\/?(?:\?|$)/.test(path) ||
    (!token && !localStorage.getItem("refresh_token"))
  ) {
    return response;
  }

  await response.body?.cancel();
  if (localStorage.getItem("access_token") === token) {
    await refreshAccessToken();
  }
  const newToken = localStorage.getItem("access_token");
  if (!newToken) throw new Error("Session ended before request retry");
  return send(newToken);
}

async function post<TResponse>(path: string, body: unknown): Promise<TResponse> {
  const response = await withTimeout(
    (signal) =>
      authenticatedFetch(path, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
        signal,
      }),
    resolveTimeoutMs(),
  );

  if (!response.ok) {
    throw new Error(`Request failed with status ${response.status}`);
  }

  return (await response.json()) as TResponse;
}

async function get<TResponse>(path: string): Promise<TResponse> {
  const response = await withTimeout(
    (signal) =>
      authenticatedFetch(path, {
        method: "GET",
        headers: { "Content-Type": "application/json" },
        signal,
      }),
    resolveTimeoutMs(),
  );

  if (!response.ok) {
    throw new Error(`Request failed with status ${response.status}`);
  }

  return (await response.json()) as TResponse;
}

export const apiClient = {
  get,
  post,
};
