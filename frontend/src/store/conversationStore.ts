import { createContext, createElement, useCallback, useContext, useMemo, useRef, useState, useEffect, type ReactNode } from "react";
import { flushSync } from "react-dom";
import { postChat, streamChat, fetchChatHistory, fetchChatSessions } from "../lib/api/chat";
import type { ChatMessage } from "../types/api";
import type { ChatRequest } from "../types/api";
import type { RagResponse } from "../types/rag";
import { normalizeRagResponse } from "../lib/api/chat";

type ConversationMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
  response?: RagResponse;
  tempContext?: any[];
};

type ChatSession = {
  session_id: string;
  title: string;
  created_at: string;
};

type ConversationStoreValue = {
  conversationId: string;
  messages: ConversationMessage[];
  sessions: ChatSession[];
  isLoading: boolean;
  error: string | null;
  canRetryLastFailedPrompt: boolean;
  sendPrompt: (prompt: string) => Promise<void>;
  retryLastFailedPrompt: () => Promise<void>;
  clearConversation: () => void;
  clearError: () => void;
  addMessage: (message: Omit<ConversationMessage, "id">) => void;
  streamingStatus: string | null;
  switchSession: (sessionId: string) => Promise<void>;
  refreshSessions: () => Promise<void>;
  login: (accessToken: string, refreshToken: string) => Promise<void>;
  logout: () => void;
};

type FailedPromptState = {
  prompt: string;
  payload: ChatRequest;
};

const ConversationStoreContext = createContext<ConversationStoreValue | null>(null);

export function rollbackOptimisticMessage(
  messages: ConversationMessage[],
  optimisticMessageId: string,
): ConversationMessage[] {
  return messages.filter((message) => message.id !== optimisticMessageId);
}

export function buildFailedPromptState(prompt: string, payload: ChatRequest): FailedPromptState {
  return { prompt, payload };
}

export function hasVisibleStreamToken(token: string): boolean {
  return /\S/.test(token);
}

function splitTypewriterText(text: string, maxChars = 12): string[] {
  const chunks: string[] = [];
  let current = "";

  for (const char of text) {
    current += char;
    if (current.length >= maxChars && /[\s.,;:!?)]/.test(char)) {
      chunks.push(current);
      current = "";
    }
  }

  if (current) chunks.push(current);
  return chunks;
}

function wait(ms: number): Promise<void> {
  return new Promise((resolve) => window.setTimeout(resolve, ms));
}

function toFinalAssistantMessage(message: ConversationMessage, metadata: RagResponse): ConversationMessage {
  return {
    ...message,
    response: metadata,
    content: metadata.text && metadata.text.length > 0 ? metadata.text : message.content,
  };
}

function withAssistantContent(
  messages: ConversationMessage[],
  assistantMessageId: string,
  updater: (message: ConversationMessage) => ConversationMessage,
): ConversationMessage[] {
  return messages.map((msg) => (msg.id === assistantMessageId ? updater(msg) : msg));
}

async function playTypewriterFallback(
  text: string,
  appendContent: (chunk: string) => void,
): Promise<void> {
  for (const chunk of splitTypewriterText(text)) {
    appendContent(chunk);
    await wait(/[.!?]\s*$/.test(chunk) ? 90 : 34);
  }
}

function toApiMessages(messages: ConversationMessage[]): ChatMessage[] {
  return messages.map(({ role, content }) => ({ role, content }));
}

function createMessageId(role: "user" | "assistant"): string {
  return `${role}-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
}

function createConversationId(): string {
  const cryptoApi = globalThis.crypto;
  if (cryptoApi && typeof cryptoApi.randomUUID === "function") {
    return cryptoApi.randomUUID();
  }
  return `conversation-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
}

export function ConversationStoreProvider({ children }: { children: ReactNode }) {
  const [conversationId, setConversationId] = useState(() => createConversationId());
  const [messages, setMessages] = useState<ConversationMessage[]>([]);
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [streamingStatus, setStreamingStatus] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [failedPromptState, setFailedPromptState] = useState<FailedPromptState | null>(null);
  const inFlightLockRef = useRef(false);
  const requestTokenRef = useRef(0);

  const refreshSessions = useCallback(async () => {
    try {
      const data = await fetchChatSessions();
      setSessions(data);
    } catch (err) {
      console.error("Failed to fetch sessions:", err);
    }
  }, []);

  const switchSession = useCallback(async (sessionId: string) => {
    if (inFlightLockRef.current) return;
    setIsLoading(true);
    setStreamingStatus("Đang tải cuộc hội thoại...");
    try {
      const history = await fetchChatHistory(sessionId);
      const formattedMessages: ConversationMessage[] = history.map((h: any) => ({
        id: h.id,
        role: h.role,
        content: h.content,
        response: h.metadata_json
      }));
      setMessages(formattedMessages);
      setConversationId(sessionId);
    } catch (err) {
      console.error("Failed to switch session:", err);
      setError("Không thể tải cuộc hội thoại này.");
    } finally {
      setIsLoading(false);
      setStreamingStatus(null);
    }
  }, []);

  // Tải dữ liệu ban đầu
  useEffect(() => {
    const init = async () => {
      const token = localStorage.getItem("access_token");
      if (!token) return;

      await refreshSessions();
      
      try {
        const history = await fetchChatHistory();
        if (history && history.length > 0) {
          const lastMsg = history[history.length - 1];
          setConversationId(lastMsg.session_id);
          
          const formattedMessages: ConversationMessage[] = history.map((h: any) => ({
            id: h.id,
            role: h.role,
            content: h.content,
            response: h.metadata_json
          }));
          setMessages(formattedMessages);
        }
      } catch (err) {
        console.error("Failed to load initial history:", err);
      }
    };
    init();
  }, [refreshSessions]);

  const sendPrompt = useCallback(
    async (prompt: string, retryPayload?: ChatRequest) => {
      const userPrompt = prompt.trim();
      if (!userPrompt || inFlightLockRef.current) {
        return;
      }

      inFlightLockRef.current = true;
      const requestToken = ++requestTokenRef.current;

      const optimisticUserMessage: ConversationMessage = {
        id: createMessageId("user"),
        role: "user",
        content: userPrompt,
      };

      const nextMessages = [...messages, optimisticUserMessage];
      const payload: ChatRequest = retryPayload ?? {
        conversation_id: conversationId,
        user_message: userPrompt,
        messages: toApiMessages(nextMessages),
      };

      const assistantMessageId = createMessageId("assistant");
      const optimisticAssistantMessage: ConversationMessage = {
        id: assistantMessageId,
        role: "assistant",
        content: "",
      };

      flushSync(() => {
        setMessages([...nextMessages, optimisticAssistantMessage]);
        setError(null);
        setFailedPromptState(null);
        setIsLoading(true);
        setStreamingStatus("Đang gửi yêu cầu...");
      });

      try {
        let isFirstToken = true;
        let hasReceivedVisibleToken = false;
        let hasFinalMetadata = false;

        await streamChat(
          payload,
          (token) => {
            if (requestToken !== requestTokenRef.current || hasFinalMetadata) return;
            if (isFirstToken && hasVisibleStreamToken(token)) {
              setIsLoading(false);
              isFirstToken = false;
              hasReceivedVisibleToken = true;
              setStreamingStatus(null);
            }
            setMessages((prev) =>
              prev.map((msg) =>
                msg.id === assistantMessageId 
                  ? { ...msg, content: msg.content + token } 
                  : msg
              )
            );
          },
          (metadata, serverConvId) => {
            if (requestToken !== requestTokenRef.current) return;
            hasFinalMetadata = true;
            if (serverConvId) setConversationId(serverConvId);
            setIsLoading(false);
            setStreamingStatus(null);
            const hasBase64 = metadata.text?.includes("data:image/png;base64,");
            const shouldPlayFallback = Boolean(metadata.text) && !hasReceivedVisibleToken && !hasBase64;
            if (shouldPlayFallback) {
              const chunks = splitTypewriterText(metadata.text);
              const [firstChunk = "", ...remainingChunks] = chunks;
              setMessages((prev) =>
                withAssistantContent(prev, assistantMessageId, (msg) => ({
                  ...msg,
                  response: undefined,
                  content: firstChunk,
                })),
              );

              void playTypewriterFallback(remainingChunks.join(""), (chunk) => {
                setMessages((prev) =>
                  withAssistantContent(prev, assistantMessageId, (msg) => ({
                    ...msg,
                    content: msg.content + chunk,
                  })),
                );
              }).then(() => {
                setMessages((prev) =>
                  withAssistantContent(prev, assistantMessageId, (msg) => toFinalAssistantMessage(msg, metadata)),
                );
              });
            } else {
              setMessages((prev) =>
                withAssistantContent(prev, assistantMessageId, (msg) => toFinalAssistantMessage(msg, metadata)),
              );
            }
            // Cập nhật lại danh sách sessions nếu đây là cuộc hội thoại mới (chưa có trong danh sách)
            setSessions(prev => {
              if (!prev.some(s => s.session_id === serverConvId)) {
                refreshSessions();
              }
              return prev;
            });
          },
          (docs) => {
            if (requestToken !== requestTokenRef.current) return;
            setMessages((prev) =>
              prev.map((msg) =>
                msg.id === assistantMessageId 
                  ? { ...msg, tempContext: docs } 
                  : msg
              )
            );
          },
          (status) => {
            if (requestToken !== requestTokenRef.current || hasFinalMetadata) return;
            setStreamingStatus(status);
          },
          (error) => {
             throw error;
          }
        );
      } catch (requestError) {
        if (requestToken !== requestTokenRef.current) return;
        setMessages((prev) => prev.filter(m => m.id !== optimisticUserMessage.id && m.id !== assistantMessageId));
        setFailedPromptState(buildFailedPromptState(userPrompt, payload));
        setError(requestError instanceof Error ? requestError.message : "Không thể gửi câu hỏi.");
      } finally {
        if (requestToken === requestTokenRef.current) {
          inFlightLockRef.current = false;
          setIsLoading(false);
        }
      }
    },
    [conversationId, messages, refreshSessions],
  );

  const retryLastFailedPrompt = useCallback(async () => {
    if (!failedPromptState || inFlightLockRef.current) return;
    await sendPrompt(failedPromptState.prompt, failedPromptState.payload);
  }, [failedPromptState, sendPrompt]);

  const login = useCallback(async (accessToken: string, refreshToken: string) => {
    localStorage.setItem("access_token", accessToken);
    localStorage.setItem("refresh_token", refreshToken);
    
    // Tải lại dữ liệu ngay lập tức cho user mới
    await refreshSessions();
    try {
      const history = await fetchChatHistory();
      if (history && history.length > 0) {
        const lastMsg = history[history.length - 1];
        setConversationId(lastMsg.session_id);
        const formattedMessages: ConversationMessage[] = history.map((h: any) => ({
          id: h.id,
          role: h.role,
          content: h.content,
          response: h.metadata_json
        }));
        setMessages(formattedMessages);
      } else {
        setMessages([]);
        setConversationId(createConversationId());
      }
    } catch (err) {
      console.error("Failed to load history after login:", err);
    }
  }, [refreshSessions]);

  const logout = useCallback(() => {
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
    setMessages([]);
    setSessions([]);
    setConversationId(createConversationId());
    setError(null);
    setStreamingStatus(null);
  }, []);

  const clearConversation = useCallback(() => {
    requestTokenRef.current += 1;
    inFlightLockRef.current = false;
    setMessages([]);
    setIsLoading(false);
    setStreamingStatus(null);
    setError(null);
    setFailedPromptState(null);
    setConversationId(createConversationId());
  }, []);

  const clearError = useCallback(() => {
    setError(null);
  }, []);

  const addMessage = useCallback((message: Omit<ConversationMessage, "id">) => {
    setMessages((prev) => [
      ...prev,
      {
        ...message,
        id: createMessageId(message.role),
      },
    ]);
  }, []);

  const value = useMemo(
    () => ({
      conversationId,
      messages,
      sessions,
      isLoading,
      error,
      canRetryLastFailedPrompt: Boolean(failedPromptState),
      sendPrompt: (prompt: string) => sendPrompt(prompt),
      retryLastFailedPrompt,
      clearConversation,
      clearError,
      addMessage,
      streamingStatus,
      switchSession,
      refreshSessions,
      login,
      logout,
    }),
    [clearConversation, clearError, conversationId, error, failedPromptState, isLoading, messages, retryLastFailedPrompt, sendPrompt, addMessage, streamingStatus, sessions, switchSession, refreshSessions, login, logout],
  );

  return createElement(ConversationStoreContext.Provider, { value }, children);
}

export function useConversationStore(): ConversationStoreValue {
  const context = useContext(ConversationStoreContext);
  if (!context) {
    throw new Error("useConversationStore must be used within ConversationStoreProvider");
  }

  return context;
}

export type { ConversationMessage };
