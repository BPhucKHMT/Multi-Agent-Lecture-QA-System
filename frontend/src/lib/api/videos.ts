import { apiClient } from "./client";
import type { VideoListResponse, VideoSummaryRequest, VideoSummaryResponse } from "../../types/api";

type GetVideosParams = {
  query?: string;
  page?: number;
  pageSize?: number;
};

export async function getVideos({ query = "", page = 1, pageSize = 20 }: GetVideosParams = {}): Promise<VideoListResponse> {
  const params = new URLSearchParams({
    query,
    page: String(page),
    page_size: String(pageSize),
  });
  return apiClient.get<VideoListResponse>(`/api/v1/videos?${params.toString()}`);
}

export async function summarizeVideo(payload: VideoSummaryRequest): Promise<VideoSummaryResponse> {
  return apiClient.post<VideoSummaryResponse>("/api/v1/videos/summary", payload);
}
