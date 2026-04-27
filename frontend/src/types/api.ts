import type { RagResponse } from "./rag";

export type ChatMessage = {
  role: "user" | "assistant";
  content: string;
};

export type ChatRequest = {
  conversation_id: string;
  messages: ChatMessage[];
  user_message: string;
};

export type ChatResponseEnvelope = {
  conversation_id: string;
  response: Partial<RagResponse>;
  updated_at: string;
};

export type ChatStreamTokenEvent = {
  type: "token";
  content: string;
};

export type ChatStreamMetadataEvent = {
  type: "metadata";
  conversation_id: string;
  response: Partial<RagResponse>;
};

export type ChatStreamContextEvent = {
  type: "context";
  docs: any[];
};

export type ChatStreamStatusEvent = {
  type: "status";
  status: string;
};

export type ChatStreamEvent = ChatStreamTokenEvent | ChatStreamMetadataEvent | ChatStreamContextEvent | ChatStreamStatusEvent;


export type NormalizedChatResponse = {
  conversation_id: string;
  response: RagResponse;
  updated_at: string;
};

export type VideoItem = {
  id: string;
  video_id: string;
  title: string;
  course: string;
  file_name: string;
  relative_path: string;
  file_size_mb: number;
  thumbnail_url: string;
  video_url: string;
};

export type VideoListResponse = {
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
  query: string;
  videos: VideoItem[];
};

export type VideoSummaryRequest = {
  video_id: string;
};

export type VideoSummaryResponse = {
  video_id: string;
  summary: string;
};
