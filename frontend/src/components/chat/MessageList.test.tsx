import { describe, expect, it } from "vitest";
import { getMessageAnimationDelay } from "./MessageList";

describe("getMessageAnimationDelay", () => {
  it("does not delay new chat bubbles based on history length", () => {
    expect(getMessageAnimationDelay()).toBe("0ms");
  });
});
