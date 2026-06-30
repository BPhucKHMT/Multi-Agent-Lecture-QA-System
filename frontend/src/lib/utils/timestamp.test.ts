import { describe, expect, it } from "vitest";
import { timestampToSeconds } from "./timestamp";

describe("timestampToSeconds", () => {
  it("converts HH:MM:SS to seconds", () => {
    expect(timestampToSeconds("01:02:03")).toBe(3723);
  });

  it("converts MM:SS to seconds", () => {
    expect(timestampToSeconds("02:03")).toBe(123);
  });

  it("returns 0 for invalid timestamp", () => {
    expect(timestampToSeconds("not-a-time")).toBe(0);
  });
});
