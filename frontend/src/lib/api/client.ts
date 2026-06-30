export const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL ?? "").replace(/\/$/, "");
const DEFAULT_TIMEOUT_MS = 360000;

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

async function post<TResponse>(path: string, body: unknown): Promise<TResponse> {
  const token = localStorage.getItem("access_token");
  const response = await withTimeout(
    (signal) =>
      fetch(`${API_BASE_URL}${path}`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
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
  const token = localStorage.getItem("access_token");
  const response = await withTimeout(
    (signal) =>
      fetch(`${API_BASE_URL}${path}`, {
        method: "GET",
        headers: {
          "Content-Type": "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
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
