import { describe, expect, it } from "vitest";
import {
  buildFailedPromptState,
  hasVisibleStreamToken,
  rollbackOptimisticMessage,
  type ConversationMessage,
} from "./conversationStore";

describe("rollbackOptimisticMessage", () => {
  it("removes only the failed optimistic user message", () => {
    const messages: ConversationMessage[] = [
      { id: "user-1", role: "user", content: "first" },
      { id: "assistant-1", role: "assistant", content: "reply" },
      { id: "user-2", role: "user", content: "failed" },
    ];

    expect(rollbackOptimisticMessage(messages, "user-2")).toEqual([
      { id: "user-1", role: "user", content: "first" },
      { id: "assistant-1", role: "assistant", content: "reply" },
    ]);
  });
});

describe("buildFailedPromptState", () => {
  it("preserves failed prompt and payload for retry", () => {
    const failed = buildFailedPromptState("Cau hoi", {
      conversation_id: "conv-1",
      user_message: "Cau hoi",
      messages: [{ role: "user", content: "Cau hoi" }],
    });

    expect(failed).toEqual({
      prompt: "Cau hoi",
      payload: {
        conversation_id: "conv-1",
        user_message: "Cau hoi",
        messages: [{ role: "user", content: "Cau hoi" }],
      },
    });
  });
});

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
