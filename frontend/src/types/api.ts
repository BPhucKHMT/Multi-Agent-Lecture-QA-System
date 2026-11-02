import type { RagResponse } from "./rag";

export type ChatRequest = {
  conversation_id: string;
  user_message: string;
};

type ChatStreamTokenEvent = {
  type: "token";
  content: string;
};

type ChatStreamMetadataEvent = {
  type: "metadata";
  conversation_id: string;
  response: Partial<RagResponse>;
};

type ChatStreamContextEvent = {
  type: "context";
  docs: any[];
};

type ChatStreamStatusEvent = {
  type: "status";
  status: string;
};

type ChatStreamErrorEvent = {
  type: "error";
  content: string;
};

export type ChatStreamEvent = ChatStreamTokenEvent | ChatStreamMetadataEvent | ChatStreamContextEvent | ChatStreamStatusEvent | ChatStreamErrorEvent;

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
