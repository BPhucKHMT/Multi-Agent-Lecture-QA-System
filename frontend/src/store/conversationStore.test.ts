import { describe, expect, it } from "vitest";
import { hasVisibleStreamToken } from "./conversationStore";

describe("hasVisibleStreamToken", () => {
  it("keeps loading visible for whitespace-only stream tokens", () => {
    expect(hasVisibleStreamToken("")).toBe(false);
    expect(hasVisibleStreamToken(" \n\t")).toBe(false);
  });

  it("detects the first visible token before hiding the loader", () => {
    expect(hasVisibleStreamToken(" attention")).toBe(true);
    expect(hasVisibleStreamToken("$\\theta$")).toBe(true);
  });
});
