import { describe, expect, it, vi } from "vitest";
import type { ChatRequest } from "../../types/api";
import { normalizeChatResponse, postChat } from "./chat";
import { apiClient } from "./client";

vi.mock("./client", () => ({
  apiClient: {
    post: vi.fn(),
  },
}));

describe("normalizeChatResponse", () => {
  it("returns strict defaults for missing rag metadata arrays", () => {
    expect(
      normalizeChatResponse({
        conversation_id: "c1",
        updated_at: "2026-04-19T00:00:00Z",
        response: { text: "hello", type: "direct" },
      }),
    ).toEqual({
      conversation_id: "c1",
      updated_at: "2026-04-19T00:00:00Z",
      response: {
        text: "hello",
        video_url: [],
        title: [],
        filename: [],
        start_timestamp: [],
        end_timestamp: [],
        confidence: [],
        type: "direct",
      },
    });
  });
});

describe("postChat", () => {
  it("posts to /chat and normalizes nested envelope response", async () => {
    const payload: ChatRequest = {
      conversation_id: "conv-1",
      messages: [{ role: "user", content: "Xin chao" }],
      user_message: "Xin chao",
    };

    vi.mocked(apiClient.post).mockResolvedValue({
      conversation_id: "conv-1",
      updated_at: "2026-04-19T00:00:00Z",
      response: {
        text: "Hello",
        type: "direct",
      },
    });

    const result = await postChat(payload);

    expect(apiClient.post).toHaveBeenCalledWith("/chat", payload);
    expect(result).toEqual({
      conversation_id: "conv-1",
      updated_at: "2026-04-19T00:00:00Z",
      response: {
        text: "Hello",
        video_url: [],
        title: [],
        filename: [],
        start_timestamp: [],
        end_timestamp: [],
        confidence: [],
        type: "direct",
      },
    });
  });
});
