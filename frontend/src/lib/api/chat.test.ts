import { describe, expect, it, vi } from "vitest";
import { normalizeRagResponse, streamChat } from "./chat";

describe("normalizeRagResponse", () => {
  it("returns strict defaults for missing rag metadata arrays", () => {
    expect(
      normalizeRagResponse({
        text: "hello",
        type: "direct",
      }),
    ).toEqual({
      text: "hello",
      video_url: [],
      title: [],
      filename: [],
      start_timestamp: [],
      end_timestamp: [],
      confidence: [],
      type: "direct",
    });
  });
});

it("reports an error frame from a successful HTTP streaming response", async () => {
  vi.stubGlobal("localStorage", { getItem: () => null });
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue(
    new Response('data: {"type":"error","content":"Agent bị lỗi"}\n\ndata: [DONE]\n\n', {
      status: 200,
      headers: { "Content-Type": "text/event-stream" },
    }),
  ));

  try {
    const errors: Error[] = [];
    await streamChat(
      { conversation_id: "c1", user_message: "Tạo quiz" },
      () => {},
      () => {},
      () => {},
      () => {},
      (error) => { errors.push(error); },
    );

    expect(errors.map((error) => error.message)).toEqual(["Agent bị lỗi"]);
  } finally {
    vi.unstubAllGlobals();
  }
});
