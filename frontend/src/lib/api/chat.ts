import { apiClient, API_BASE_URL } from "./client";
import type { ChatRequest, ChatResponseEnvelope, NormalizedChatResponse, ChatStreamEvent } from "../../types/api";
import type { RagConfidence, RagResponse, RagResponseType } from "../../types/rag";

const VALID_TYPES: RagResponseType[] = ["rag", "direct", "quiz", "math", "coding", "error"];
const VALID_CONFIDENCE: RagConfidence[] = ["high", "medium", "low", "zero"];

function normalizeString(value: unknown): string {
  return typeof value === "string" ? value : "";
}

function normalizeStringArray(value: unknown): string[] {
  return Array.isArray(value) && value.every((item) => typeof item === "string") ? value : [];
}

function normalizeConfidenceArray(value: unknown): RagConfidence[] {
  return Array.isArray(value) && value.every((item) => VALID_CONFIDENCE.includes(item as RagConfidence))
    ? (value as RagConfidence[])
    : [];
}

function normalizeType(value: unknown): RagResponseType {
  return VALID_TYPES.includes(value as RagResponseType) ? (value as RagResponseType) : "error";
}

export function normalizeRagResponse(response: Partial<RagResponse>): RagResponse {
  return {
    text: normalizeString(response.text),
    video_url: normalizeStringArray(response.video_url),
    title: normalizeStringArray(response.title),
    filename: normalizeStringArray(response.filename),
    start_timestamp: normalizeStringArray(response.start_timestamp),
    end_timestamp: normalizeStringArray(response.end_timestamp),
    confidence: normalizeConfidenceArray(response.confidence),
    type: normalizeType(response.type),
    quizzes: Array.isArray(response.quizzes) ? response.quizzes : undefined,
    math_data: response.math_data || undefined,
    coding_data: response.coding_data || undefined,
  };
}

export function normalizeChatResponse(payload: ChatResponseEnvelope): NormalizedChatResponse {
  return {
    conversation_id: payload.conversation_id,
    updated_at: payload.updated_at,
    response: normalizeRagResponse(payload.response ?? {}),
  };
}

export async function postChat(payload: ChatRequest): Promise<NormalizedChatResponse> {
  const response = await apiClient.post<ChatResponseEnvelope>("/api/v1/chat", payload);
  return normalizeChatResponse(response);
}

export async function streamChat(
  payload: ChatRequest,
  onToken: (token: string) => void,
  onMetadata: (metadata: RagResponse, conversationId: string) => void,
  onContext: (docs: any[]) => void,
  onStatus: (status: string) => void,
  onError: (error: Error) => void
): Promise<void> {

  try {
    const token = localStorage.getItem("access_token");
    const response = await fetch(`${API_BASE_URL}/api/v1/chat/stream`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      throw new Error(`Streaming request failed: ${response.status}`);
    }

    const reader = response.body?.getReader();
    if (!reader) throw new Error("No reader available");

    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop() || "";

      for (const line of lines) {
        const trimmed = line.trim();
        if (!trimmed || !trimmed.startsWith("data: ")) continue;

        const dataStr = trimmed.slice(6);
        if (dataStr === "[DONE]") break;

        try {
          const event = JSON.parse(dataStr) as ChatStreamEvent;
          if (event.type === "token") {
            onToken(event.content);
          } else if (event.type === "metadata") {
            onMetadata(normalizeRagResponse(event.response), event.conversation_id);
          } else if (event.type === "context") {
            onContext(event.docs);
          } else if (event.type === "status") {
            onStatus(event.status);
          }

        } catch (e) {
          console.error("Failed to parse SSE data:", dataStr, e);
        }
      }
    }

  } catch (error) {
    onError(error instanceof Error ? error : new Error("Unknown streaming error"));
  }
}

export async function fetchChatHistory(sessionId?: string): Promise<any[]> {
  const path = sessionId ? `/api/v1/chat/history?session_id=${sessionId}` : "/api/v1/chat/history";
  return apiClient.get<any[]>(path);
}

export async function fetchChatSessions(): Promise<any[]> {
  return apiClient.get<any[]>("/api/v1/chat/sessions");
}

