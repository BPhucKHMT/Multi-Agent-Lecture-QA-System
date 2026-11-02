import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { apiClient } from "./client";
import { streamChat } from "./chat";

const refreshedTokens = { access_token: "access-new", refresh_token: "refresh-new", token_type: "bearer" };
let storage: Map<string, string>;
let events: EventTarget;

function authHeader(init?: RequestInit): string | null {
  return new Headers(init?.headers).get("Authorization");
}

function deferred<T>() {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((done) => { resolve = done; });
  return { promise, resolve };
}

async function readStream(): Promise<string[]> {
  const tokens: string[] = [];
  await streamChat(
    { conversation_id: "c1", user_message: "Giải thích" },
    (token) => tokens.push(token),
    () => {},
    () => {},
    () => {},
    (error) => { throw error; },
  );
  return tokens;
}

beforeEach(() => {
  storage = new Map([["access_token", "access-old"], ["refresh_token", "refresh-old"]]);
  events = new EventTarget();
  vi.stubGlobal("window", events);
  vi.stubGlobal("localStorage", {
    getItem: (key: string) => storage.get(key) ?? null,
    setItem: (key: string, value: string) => { storage.set(key, value); },
    removeItem: (key: string) => { storage.delete(key); },
  });
});

afterEach(() => {
  vi.useRealTimers();
  vi.unstubAllEnvs();
  vi.unstubAllGlobals();
});

describe("automatic token refresh", () => {
  it("rotates both tokens and retries the original POST with the new access token", async () => {
    const fetchMock = vi.fn(async (url: string, init?: RequestInit) => {
      if (url.endsWith("/auth/refresh")) {
        expect(JSON.parse(init!.body as string)).toEqual({ refresh_token: "refresh-old" });
        return Response.json(refreshedTokens);
      }
      expect(init?.body).toBe(JSON.stringify({ video_id: "v1" }));
      return authHeader(init) === "Bearer access-new"
        ? Response.json({ summary: "Nội dung" })
        : new Response(null, { status: 401 });
    });
    vi.stubGlobal("fetch", fetchMock);

    await expect(apiClient.post("/api/v1/videos/summary", { video_id: "v1" }))
      .resolves.toEqual({ summary: "Nội dung" });
    expect(storage.get("access_token")).toBe("access-new");
    expect(storage.get("refresh_token")).toBe("refresh-new");
    expect(fetchMock.mock.calls.map(([url]) => url)).toEqual([
      "/api/v1/videos/summary", "/api/v1/auth/refresh", "/api/v1/videos/summary",
    ]);
  });

  it.each(["rejected", "forbidden", "invalid response", "invalid JSON", "missing token"])(
    "clears credentials and triggers logout when the session cannot be refreshed: %s",
    async (failure) => {
      if (failure === "missing token") storage.delete("refresh_token");
      const logout = vi.fn();
      events.addEventListener("auth:expired", logout);
      const fetchMock = vi.fn(async (url: string) => {
        if (url.endsWith("/auth/refresh")) {
          if (failure === "forbidden") return new Response(null, { status: 403 });
          if (failure === "invalid JSON") return new Response("invalid JSON");
          if (failure === "invalid response") return Response.json({ access_token: "access-new" });
          return new Response(null, { status: 401 });
        }
        return new Response(null, { status: 401 });
      });
      vi.stubGlobal("fetch", fetchMock);

      await expect(apiClient.get("/api/v1/chat/history")).rejects.toThrow();
      expect(storage.has("access_token")).toBe(false);
      expect(storage.has("refresh_token")).toBe(false);
      expect(logout).toHaveBeenCalledTimes(1);
      expect(fetchMock.mock.calls.filter(([url]) => url.endsWith("/auth/refresh")))
        .toHaveLength(failure === "missing token" ? 0 : 1);
    },
  );

  it.each(["network", "abort", "server error"])(
    "preserves credentials without logging out on a transient refresh failure: %s",
    async (failure) => {
      const logout = vi.fn();
      events.addEventListener("auth:expired", logout);
      const fetchMock = vi.fn(async (url: string) => {
        if (url.endsWith("/auth/refresh")) {
          if (failure === "network") throw new TypeError("Failed to fetch");
          if (failure === "abort") throw new DOMException("Aborted", "AbortError");
          return new Response(null, { status: 503 });
        }
        return new Response(null, { status: 401 });
      });
      vi.stubGlobal("fetch", fetchMock);

      await expect(apiClient.get("/api/v1/chat/history")).rejects.toThrow();
      expect(storage.get("access_token")).toBe("access-old");
      expect(storage.get("refresh_token")).toBe("refresh-old");
      expect(logout).not.toHaveBeenCalled();
      expect(fetchMock).toHaveBeenCalledTimes(2);
    },
  );

  it("preserves credentials when the refresh request times out", async () => {
    vi.useFakeTimers();
    vi.stubEnv("VITE_API_TIMEOUT_MS", "1000");
    const logout = vi.fn();
    events.addEventListener("auth:expired", logout);
    vi.stubGlobal("fetch", vi.fn(async (url: string, init?: RequestInit) => {
      if (!url.endsWith("/auth/refresh")) return new Response(null, { status: 401 });
      return new Promise<Response>((_, reject) => {
        init?.signal?.addEventListener("abort", () => reject(new DOMException("Aborted", "AbortError")));
      });
    }));
    const rejection = expect(apiClient.get("/api/v1/chat/history")).rejects.toThrow("timed out");

    await vi.advanceTimersByTimeAsync(1000);
    await rejection;
    expect(storage.get("access_token")).toBe("access-old");
    expect(storage.get("refresh_token")).toBe("refresh-old");
    expect(logout).not.toHaveBeenCalled();
  });

  it("shares one in-flight refresh between two concurrent API 401s", async () => {
    const refresh = deferred<Response>();
    const started = deferred<void>();
    const fetchMock = vi.fn(async (url: string, init?: RequestInit) => {
      if (url.endsWith("/auth/refresh")) {
        started.resolve();
        return refresh.promise;
      }
      return authHeader(init) === "Bearer access-new"
        ? Response.json({ path: url })
        : new Response(null, { status: 401 });
    });
    vi.stubGlobal("fetch", fetchMock);
    const first = apiClient.get("/api/v1/chat/history");
    const second = apiClient.get("/api/v1/chat/sessions");
    await started.promise;
    refresh.resolve(Response.json(refreshedTokens));

    await expect(Promise.all([first, second])).resolves.toEqual([
      { path: "/api/v1/chat/history" }, { path: "/api/v1/chat/sessions" },
    ]);
    expect(fetchMock.mock.calls.filter(([url]) => url.endsWith("/auth/refresh"))).toHaveLength(1);
  });

  it("retries a late 401 with the already rotated access token without refreshing again", async () => {
    const late = deferred<Response>();
    const fetchMock = vi.fn(async (url: string, init?: RequestInit) => {
      if (url.endsWith("/auth/refresh")) return Response.json(refreshedTokens);
      if (authHeader(init) === "Bearer access-new") return Response.json({ path: url });
      if (url.endsWith("/sessions")) return late.promise;
      return new Response(null, { status: 401 });
    });
    vi.stubGlobal("fetch", fetchMock);
    const delayed = apiClient.get("/api/v1/chat/sessions");
    await apiClient.get("/api/v1/chat/history");
    late.resolve(new Response(null, { status: 401 }));

    await expect(delayed).resolves.toEqual({ path: "/api/v1/chat/sessions" });
    expect(fetchMock.mock.calls.filter(([url]) => url.endsWith("/auth/refresh"))).toHaveLength(1);
  });

  it("refreshes the SSE request and consumes tokens from the retried stream", async () => {
    const fetchMock = vi.fn(async (url: string, init?: RequestInit) => {
      if (url.endsWith("/auth/refresh")) return Response.json(refreshedTokens);
      return authHeader(init) === "Bearer access-new"
        ? new Response('data: {"type":"token","content":"Xin chào"}\n\ndata: [DONE]\n\n')
        : new Response(null, { status: 401 });
    });
    vi.stubGlobal("fetch", fetchMock);

    await expect(readStream()).resolves.toEqual(["Xin chào"]);
    expect(fetchMock.mock.calls.map(([url]) => url)).toEqual([
      "/api/v1/chat/stream", "/api/v1/auth/refresh", "/api/v1/chat/stream",
    ]);
  });

  it("logs out and reports the SSE error when refresh is rejected", async () => {
    const logout = vi.fn();
    events.addEventListener("auth:expired", logout);
    const fetchMock = vi.fn(async () => new Response(null, { status: 401 }));
    vi.stubGlobal("fetch", fetchMock);

    await expect(readStream()).rejects.toThrow("401");
    expect(storage.has("access_token")).toBe(false);
    expect(storage.has("refresh_token")).toBe(false);
    expect(logout).toHaveBeenCalledTimes(1);
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });

  it("shares the refresh between concurrent SSE and API requests", async () => {
    const refresh = deferred<Response>();
    const started = deferred<void>();
    const fetchMock = vi.fn(async (url: string, init?: RequestInit) => {
      if (url.endsWith("/auth/refresh")) {
        started.resolve();
        return refresh.promise;
      }
      if (authHeader(init) !== "Bearer access-new") return new Response(null, { status: 401 });
      return url.endsWith("/stream")
        ? new Response('data: {"type":"token","content":"Kết quả"}\n\n')
        : Response.json(["session-1"]);
    });
    vi.stubGlobal("fetch", fetchMock);
    const stream = readStream();
    const sessions = apiClient.get("/api/v1/chat/sessions");
    await started.promise;
    refresh.resolve(Response.json(refreshedTokens));

    await expect(Promise.all([stream, sessions])).resolves.toEqual([["Kết quả"], ["session-1"]]);
    expect(fetchMock.mock.calls.filter(([url]) => url.endsWith("/auth/refresh"))).toHaveLength(1);
  });

  it("does not retry an original request more than once", async () => {
    const fetchMock = vi.fn(async (url: string) => url.endsWith("/auth/refresh")
      ? Response.json(refreshedTokens)
      : new Response(null, { status: 401 }));
    vi.stubGlobal("fetch", fetchMock);

    await expect(apiClient.get("/api/v1/chat/history")).rejects.toThrow("Request failed with status 401");
    expect(fetchMock).toHaveBeenCalledTimes(3);
  });

  it.each(["login", "register", "refresh"])("does not refresh or retry auth/%s", async (endpoint) => {
    const fetchMock = vi.fn(async () => new Response(null, { status: 401 }));
    vi.stubGlobal("fetch", fetchMock);

    await expect(apiClient.post(`/api/v1/auth/${endpoint}`, {})).rejects.toThrow("401");
    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(storage.get("refresh_token")).toBe("refresh-old");
  });

  it("does not restore credentials if logout occurs during refresh", async () => {
    const refresh = deferred<Response>();
    const started = deferred<void>();
    vi.stubGlobal("fetch", vi.fn(async (url: string) => {
      if (url.endsWith("/auth/refresh")) {
        started.resolve();
        return refresh.promise;
      }
      return new Response(null, { status: 401 });
    }));
    const request = apiClient.get("/api/v1/chat/history");
    await started.promise;
    storage.clear();
    refresh.resolve(Response.json(refreshedTokens));

    await expect(request).rejects.toThrow();
    expect(storage.size).toBe(0);
  });
});
