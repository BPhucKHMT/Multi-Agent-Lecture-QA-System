import React, { useState, useMemo, useEffect } from "react";
import { Sparkles, Loader2 } from "lucide-react";
import { useParams, useNavigate } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import ChatInput from "../components/chat/ChatInput";
import MessageList from "../components/chat/MessageList";
import ConversationSidebar from "../components/sidebar/ConversationSidebar";
import { useConversationStore, type ConversationMessage } from "../store/conversationStore";
import { getVideos, summarizeVideo } from "../lib/api/videos";
import type { VideoItem } from "../types/api";
import type { AppSection, DiscussionContext } from "../types/app";

const SummaryLoading = () => (
  <div className="space-y-6 p-2 animate-in fade-in duration-700">
    <div className="flex items-center gap-4">
      <div className="relative flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl bg-gradient-to-br from-violet-500 to-indigo-600 text-white shadow-lg shadow-violet-200">
        <Sparkles className="h-6 w-6 animate-pulse" />
        <div className="absolute -right-1 -top-1 h-3 w-3 rounded-full bg-emerald-400 border-2 border-white" />
      </div>
      <div className="flex-1 space-y-2">
        <div className="h-4 w-32 animate-pulse rounded-full bg-slate-200" />
        <div className="flex items-center gap-2">
          <Loader2 className="h-3 w-3 animate-spin text-violet-500" />
          <div className="h-3 w-48 animate-pulse rounded-full bg-slate-100" />
        </div>
      </div>
    </div>
    <div className="space-y-4 pl-16">
      <div className="h-4 w-full animate-pulse rounded-full bg-slate-100/80" />
      <div className="h-4 w-[92%] animate-pulse rounded-full bg-slate-100/80 [animation-delay:0.2s]" />
      <div className="h-4 w-[96%] animate-pulse rounded-full bg-slate-100/80 [animation-delay:0.4s]" />
      <div className="h-4 w-[40%] animate-pulse rounded-full bg-slate-100/80 [animation-delay:0.6s]" />
    </div>
  </div>
);

function SummaryHubPanel({
  messages,
  onDiscussInChat,
}: {
  messages: ConversationMessage[];
  onDiscussInChat: (context: DiscussionContext) => void;
}) {
  const [videos, setVideos] = useState<VideoItem[]>([]);
  const [isLoadingVideos, setIsLoadingVideos] = useState(true);
  const [videoError, setVideoError] = useState<string | null>(null);
  const [searchText, setSearchText] = useState("");
  const [appliedSearch, setAppliedSearch] = useState("");
  const [page, setPage] = useState(1);
  const [pageSize] = useState(12);
  const [totalVideos, setTotalVideos] = useState(0);
  const [totalPages, setTotalPages] = useState(0);
  const [selectedVideoId, setSelectedVideoId] = useState<string | null>(null);
  const [summaryText, setSummaryText] = useState("");
  const [summarizedVideoId, setSummarizedVideoId] = useState<string | null>(null);
  const [isSummarizing, setIsSummarizing] = useState(false);
  const [summaryError, setSummaryError] = useState<string | null>(null);
  const [isRailHovered, setIsRailHovered] = useState(false);

  const getPaneFlexClass = (pane: "summary" | "rail") => {
    if (isRailHovered) return pane === "summary" ? "flex-[6.5]" : "flex-[3.5]";
    return pane === "summary" ? "flex-[7.5]" : "flex-[2.5]";
  };

  const { isLoading, error, clearError, sendPrompt, retryLastFailedPrompt, canRetryLastFailedPrompt, addMessage, streamingStatus } = useConversationStore();

  useEffect(() => {
    let mounted = true;
    setIsLoadingVideos(true);
    setVideoError(null);

    getVideos({ query: appliedSearch, page, pageSize })
      .then((response) => {
        if (!mounted) return;
        setVideos(response.videos);
        setTotalVideos(response.total);
        setTotalPages(response.total_pages);
        setSelectedVideoId((current) => current ?? response.videos[0]?.id ?? null);
      })
      .catch((error: unknown) => {
        if (!mounted) return;
        setVideoError(error instanceof Error ? error.message : "Không tải được danh sách video.");
      })
      .finally(() => {
        if (mounted) setIsLoadingVideos(false);
      });

    return () => {
      mounted = false;
    };
  }, [appliedSearch, page, pageSize]);

  const selectedVideo = useMemo(
    () => videos.find((video) => video.id === selectedVideoId) ?? videos[0] ?? null,
    [videos, selectedVideoId],
  );

  const canGoPrevious = page > 1;
  const canGoNext = totalPages > 0 && page < totalPages;

  const applySearch = () => {
    setPage(1);
    setAppliedSearch(searchText.trim());
  };

  useEffect(() => {
    const timeoutId = window.setTimeout(() => {
      setPage(1);
      setAppliedSearch(searchText.trim());
    }, 250);
    return () => window.clearTimeout(timeoutId);
  }, [searchText]);

  useEffect(() => {
    if (!selectedVideo) return;
    if (summarizedVideoId && summarizedVideoId !== selectedVideo.id) {
      setSummaryText("");
      setSummaryError(null);
      setSummarizedVideoId(null);
    }
  }, [selectedVideo, summarizedVideoId]);

  const handleSummarize = async () => {
    if (!selectedVideo || !selectedVideo.video_id) {
      setSummaryError("Video hiện tại chưa có video_id để tóm tắt.");
      return;
    }

    setIsSummarizing(true);
    setSummaryError(null);
    try {
      const result = await summarizeVideo({ video_id: selectedVideo.video_id });
      setSummaryText(result.summary);
      setSummarizedVideoId(selectedVideo.id);
    } catch (error: unknown) {
      setSummaryError(error instanceof Error ? error.message : "Không thể tóm tắt video.");
      setSummaryText("");
      setSummarizedVideoId(null);
    } finally {
      setIsSummarizing(false);
    }
  };

  const canDiscussInChat = Boolean(selectedVideo && summarizedVideoId === selectedVideo.id && summaryText.trim());

  return (
    <motion.div 
      layout
      transition={{ duration: 0.5, ease: [0.22, 1, 0.36, 1] }}
      className="puq-split flex flex-col lg:flex-row h-full gap-4"
    >
      <div 
        className={`transition-all duration-500 ease-[cubic-bezier(0.22,1,0.36,1)] flex flex-col space-y-4 overflow-y-auto ${getPaneFlexClass("summary")}`} 
      >
        <div className="puq-pane puq-message-enter rounded-xl bg-white p-5 shadow-sm" style={{ animationDelay: "40ms" }}>
          <p className="text-sm font-semibold text-slate-900">Video đang chọn</p>
          {selectedVideo ? (
            <div className="mt-3 space-y-1.5 text-sm text-slate-700">
              <p className="text-[15px] font-bold text-slate-900 leading-tight mb-2">{selectedVideo.title}</p>
              <div className="flex items-center gap-2 text-[13px] text-slate-500">
                <span className="rounded-md bg-slate-100 px-2 py-0.5 font-medium text-slate-600">{selectedVideo.course}</span>
                <span>•</span>
                <span className="truncate">{selectedVideo.file_name}</span>
              </div>
            </div>
          ) : (
            <p className="mt-3 text-sm text-slate-500 italic">Chọn một bài giảng để bắt đầu tóm tắt AI.</p>
          )}

          <div className="mt-4 flex flex-wrap items-center gap-2">
            <button
              type="button"
              onClick={handleSummarize}
              disabled={!selectedVideo || isSummarizing}
              className="group flex items-center justify-center gap-2 rounded-xl bg-violet-100/60 px-5 py-3 text-sm font-semibold text-violet-700 transition hover:bg-violet-200 active:scale-95 disabled:pointer-events-none disabled:opacity-50"
            >
              {isSummarizing ? "Đang xử lý..." : (
                <>
                   <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                     <path strokeLinecap="round" strokeLinejoin="round" d="M13 10V3L4 14h7v7l9-11h-7z" />
                   </svg>
                   Tóm tắt Audio/Video
                </>
              )}
            </button>

            <button
              type="button"
              onClick={() => {
                if (!selectedVideo) return;
                onDiscussInChat({
                  title: selectedVideo.title,
                  subtitle: `video_id=${selectedVideo.video_id}`,
                  summaryText: summaryText || undefined,
                });
              }}
              disabled={!canDiscussInChat}
              className="group flex items-center justify-center gap-2 rounded-xl bg-indigo-50/60 px-5 py-3 text-sm font-semibold text-indigo-700 transition hover:bg-indigo-100 active:scale-95 disabled:pointer-events-none disabled:opacity-50"
            >
               Thảo luận trong Chatspace &rarr;
            </button>
          </div>

          {!canDiscussInChat ? (
            <p className="mt-2 text-[13px] text-slate-400">Tóm tắt để kích hoạt chế độ thảo luận sâu.</p>
          ) : null}

          {summaryError ? <p className="mt-2 text-sm text-red-500">{summaryError}</p> : null}
        </div>

        {isSummarizing ? (
          <div className="puq-pane rounded-xl bg-white p-8 shadow-sm border border-violet-100/50">
             <SummaryLoading />
          </div>
        ) : null}

        {summaryText ? (
          <div className="puq-pane rounded-xl bg-white/80 p-5 shadow-sm pr-2">
            <p className="mb-2 text-sm font-semibold text-violet-800">Kết quả tóm tắt AI</p>
            <MessageList 
              messages={[{ id: "1", role: "assistant", content: summaryText }]} 
            />
          </div>
        ) : null}
      </div>

      <motion.aside
        layout
        className={`puq-pane puq-message-enter flex min-h-0 flex-col rounded-xl bg-white p-4 transition-all duration-500 ease-[cubic-bezier(0.22,1,0.36,1)] ${getPaneFlexClass("rail")}`}
        style={{ animationDelay: "160ms" }}
        onMouseEnter={() => setIsRailHovered(true)}
        onMouseLeave={() => setIsRailHovered(false)}
      >
        <p className="text-sm font-semibold text-slate-900">Danh sách video</p>
        <div className="mt-3 flex gap-2">
          <input
            value={searchText}
            onChange={(event) => setSearchText(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter") {
                event.preventDefault();
                applySearch();
              }
            }}
            placeholder="Tìm video..."
            className="flex-1 rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-blue-500"
          />
          <button
            type="button"
            onClick={applySearch}
            className="rounded-lg bg-slate-900 px-3 py-2 text-sm font-medium text-white transition hover:bg-slate-800"
          >
            Tìm
          </button>
        </div>

        <p className="mt-2 text-xs text-slate-500">Tổng: {totalVideos} video</p>

        <div className="mt-3 min-h-0 flex-1 space-y-2 overflow-y-auto pr-1">
          {isLoadingVideos ? (
            <div className="space-y-2">
              {Array.from({ length: 6 }).map((_, idx) => (
                <div key={idx} className="rounded-lg border border-slate-200 p-2">
                  <div className="flex items-start gap-3">
                    <div className="puq-skeleton h-12 w-20 rounded-md" />
                    <div className="min-w-0 flex-1 space-y-2">
                      <div className="puq-skeleton h-3 w-full rounded" />
                      <div className="puq-skeleton h-3 w-2/3 rounded" />
                    </div>
                  </div>
                </div>
              ))}
            </div>
          ) : null}
          {videoError ? <p className="text-sm text-red-600">{videoError}</p> : null}
          {!isLoadingVideos && !videoError && videos.length === 0 ? (
            <p className="text-sm text-slate-500">Không tìm thấy video phù hợp.</p>
          ) : null}

          {videos.map((video) => (
            <button
              key={video.id}
              type="button"
              onClick={() => setSelectedVideoId(video.id)}
              className={`w-full rounded-lg border px-3 py-2 text-left transition ${
                selectedVideo?.id === video.id
                  ? "border-blue-300 bg-blue-50"
                  : "border-slate-200 bg-white hover:border-slate-300 hover:bg-slate-50"
              }`}
            >
              <div className="flex items-start gap-3">
                <div className="h-12 w-20 overflow-hidden rounded-md bg-slate-100">
                  {video.thumbnail_url ? (
                    <img src={video.thumbnail_url} alt={video.title} className="h-full w-full object-cover" loading="lazy" />
                  ) : (
                    <div className="grid h-full w-full place-items-center text-[10px] font-semibold text-slate-400">NO IMAGE</div>
                  )}
                </div>
                <div className="min-w-0 flex-1">
                   <p className="line-clamp-2 text-sm font-medium text-slate-800">{video.title}</p>
                   <p className="mt-1 truncate text-xs text-slate-500">{video.course}</p>
                </div>
              </div>
            </button>
          ))}
        </div>

        <div className="mt-3 flex items-center justify-between border-t border-slate-200 pt-3">
          <button
            type="button"
            disabled={!canGoPrevious}
            onClick={() => setPage((current) => Math.max(1, current - 1))}
            className="rounded-lg border border-slate-300 px-3 py-1.5 text-xs font-medium text-slate-700 disabled:cursor-not-allowed disabled:opacity-40"
          >
            Trang trước
          </button>
          <span className="text-xs text-slate-500">Trang {totalPages === 0 ? 0 : page}/{totalPages}</span>
          <button
            type="button"
            disabled={!canGoNext}
            onClick={() => setPage((current) => current + 1)}
            className="rounded-lg border border-slate-300 px-3 py-1.5 text-xs font-medium text-slate-700 disabled:cursor-not-allowed disabled:opacity-40"
          >
            Trang sau
          </button>
        </div>
      </motion.aside>
    </motion.div>
  );
}

export default function WorkspacePage() {
  const { section } = useParams<{ section: string }>();
  const navigate = useNavigate();
  const activeSection = (section as AppSection) || "chatspace";

  const {
    conversationId,
    messages,
    isLoading,
    error,
    clearError,
    sendPrompt,
    retryLastFailedPrompt,
    canRetryLastFailedPrompt,
    clearConversation,
    addMessage,
    streamingStatus,
  } = useConversationStore();

  const [summaryContext, setSummaryContext] = useState<DiscussionContext | null>(null);
  const scrollRef = React.useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom during streaming or new messages
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTo({
        top: scrollRef.current.scrollHeight,
        behavior: "smooth"
      });
    }
  }, [messages, isLoading]);

  const historyItems = useMemo(() => {
    const userMessages = messages.filter((m) => m.role === "user");
    if (userMessages.length === 0) return [];

    // Chỉ hiển thị 1 mục đại diện cho cuộc hội thoại hiện tại
    const firstMsg = userMessages[0];
    return [
      {
        id: conversationId,
        title: firstMsg.content.slice(0, 42) || "Hội thoại mới",
        subtitle: `ID: ${conversationId.slice(0, 8)}`,
      },
    ];
  }, [conversationId, messages]);

  const handleSectionChange = (newSection: AppSection) => {
    navigate(`/workspace/${newSection}`);
  };

  const handleLogout = () => {
    navigate("/login");
  };

  return (
    <div className="relative z-10 flex h-screen overflow-hidden bg-slate-100/40">
      <ConversationSidebar
        activeSection={activeSection}
        onChangeSection={handleSectionChange}
        conversationId={conversationId}
        historyItems={historyItems}
        onNewConversation={() => { clearConversation(); setSummaryContext(null); }}
      />
      <main className="flex min-w-0 flex-1 flex-col">
        <header className="flex h-[72px] shrink-0 items-center justify-between border-b border-slate-200/50 bg-white/30 px-8 backdrop-blur-2xl">
          <div className="flex items-center gap-4">
            <h2 className="font-['Plus_Jakarta_Sans',sans-serif] text-[1.1rem] font-bold text-slate-800">
              {activeSection === "chatspace" ? "Chatspace" : "Trung tâm tóm tắt"}
            </h2>
            <div className="flex items-center gap-2 rounded-full border border-slate-200/60 bg-white/60 px-3 py-1 shadow-sm">
              <span className="relative flex h-2 w-2">
                <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75" />
                <span className="relative inline-flex h-2 w-2 rounded-full bg-emerald-500" />
              </span>
              <p className="puq-mono text-[11px] font-semibold text-slate-500">ID: {conversationId.split("-")[0]}</p>
            </div>
          </div>
          <div className="flex items-center gap-2.5">
            <button
              type="button"
              onClick={() => navigate("/gateway")}
              className="flex items-center gap-2 rounded-xl border border-transparent bg-white/80 px-4 py-2 text-[13px] font-semibold text-slate-600 shadow-sm transition hover:border-slate-200 hover:bg-white active:scale-95"
            >
              <svg className="h-4 w-4 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M4 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2V6zM14 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V6zM4 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2v-2zM14 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z" />
              </svg>
              Không gian
            </button>
            <button
              type="button"
              onClick={handleLogout}
              className="flex h-[36px] w-[36px] items-center justify-center rounded-xl bg-slate-200/50 text-slate-500 transition hover:bg-red-50 hover:text-red-500 active:scale-95"
              title="Đăng xuất"
            >
              <svg className="h-4.5 w-4.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                 <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
              </svg>
            </button>
          </div>
        </header>

        <div className="min-h-0 flex-1 relative overflow-hidden">
          <AnimatePresence mode="wait">
            {activeSection === "summaryhub" ? (
              <motion.div
                key="summaryhub"
                initial={{ opacity: 0, scale: 0.98, y: 8 }}
                animate={{ opacity: 1, scale: 1, y: 0 }}
                exit={{ opacity: 0, scale: 0.98, y: -8 }}
                transition={{ duration: 0.35, ease: [0.22, 1, 0.36, 1] }}
                className="h-full p-6"
              >
                <SummaryHubPanel
                  messages={messages}
                  onDiscussInChat={(context) => {
                    setSummaryContext(context);
                    // Inject summary vào Chatspace như tin nhắn AI đầu tiên
                    // để Supervisor Agent thấy context trong chat_history
                    if (context.summaryText) {
                      addMessage({
                        role: "assistant",
                        content: `📋 **Tóm tắt video: ${context.title}**\n\n${context.summaryText}`,
                      });
                    }
                    handleSectionChange("chatspace");
                  }}
                />
              </motion.div>
            ) : (
              <motion.div
                key="chatspace"
                initial={{ opacity: 0, scale: 0.98, y: 8 }}
                animate={{ opacity: 1, scale: 1, y: 0 }}
                exit={{ opacity: 0, scale: 0.98, y: -8 }}
                transition={{ duration: 0.35, ease: [0.22, 1, 0.36, 1] }}
                className="flex h-full flex-col"
              >
                {error ? (
                  <div className="mx-6 mt-6 mb-2 flex items-center justify-between rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
                    <span>Gửi câu hỏi thất bại: {error}</span>
                    <div className="flex items-center gap-3">
                      {canRetryLastFailedPrompt ? (
                        <button type="button" onClick={retryLastFailedPrompt} className="text-red-700 underline">
                          Thử lại
                        </button>
                      ) : null}
                      <button type="button" onClick={clearError} className="text-red-700 underline">
                        Đóng
                      </button>
                    </div>
                  </div>
                ) : null}

                <div ref={scrollRef} className="min-h-0 flex-1 overflow-y-auto px-6 py-8">
                  {summaryContext ? (
                    <div className="mx-auto max-w-4xl mb-4 rounded-xl border border-cyan-200 bg-cyan-50/50 p-4 text-sm text-cyan-900 shadow-sm backdrop-blur-sm">
                      <div className="flex items-center gap-2 mb-1">
                        <div className="h-2 w-2 rounded-full bg-cyan-400 animate-pulse" />
                        <p className="font-bold">Đang thảo luận từ Summary Hub</p>
                      </div>
                      <p className="font-medium text-cyan-800">{summaryContext.title}</p>
                      <p className="puq-mono text-xs text-cyan-700/70 mt-1">{summaryContext.subtitle}</p>
                    </div>
                  ) : null}
                  <div className="mx-auto max-w-4xl">
                    <MessageList messages={messages} isLoading={isLoading} streamingStatus={streamingStatus} />
                  </div>
                </div>
                <div className="w-full max-w-4xl mx-auto px-6 pb-8 pt-2">
                  <ChatInput
                    disabled={isLoading}
                    onSubmit={sendPrompt}
                    contextPill={summaryContext}
                    onClearContextPill={() => setSummaryContext(null)}
                  />
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </main>
    </div>
  );
}
