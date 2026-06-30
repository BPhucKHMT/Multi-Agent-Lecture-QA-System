import { describe, expect, it, vi } from "vitest";
import { withTimeout } from "./client";

describe("withTimeout", () => {
  it("rejects when request exceeds timeout", async () => {
    vi.useFakeTimers();
    const request = withTimeout(
      (signal) =>
        new Promise<never>((_, reject) => {
          signal.addEventListener("abort", () => reject(new DOMException("Aborted", "AbortError")));
        }),
      1000,
    );
    const rejection = expect(request).rejects.toThrow("Request timed out after 1000ms");

    await vi.advanceTimersByTimeAsync(1000);
    await rejection;
    vi.useRealTimers();
  });
});
