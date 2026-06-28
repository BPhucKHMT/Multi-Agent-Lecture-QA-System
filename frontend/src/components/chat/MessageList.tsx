import { User, Sparkles, Search, Layers, BrainCircuit, CheckCircle2 } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import MarkdownRenderer from "./MarkdownRenderer";
import CitationList from "./CitationList";
import QuizComponent from "./QuizComponent";
import MathComponent from "./MathComponent";
import type { ConversationMessage } from "../../store/conversationStore";

type MessageListProps = {
  messages: ConversationMessage[];
  isLoading?: boolean;
  streamingStatus?: string | null;
};

export function getMessageAnimationDelay(): string {
  return "0ms";
}

function LoadingSteps({ status }: { status?: string | null }) {
  const currentStatus = status || "Đang phân tích dữ liệu bài giảng...";
  const steps = [
    { label: "Phân tích câu hỏi", icon: BrainCircuit },
    { label: "Truy hồi bài giảng", icon: Search },
    { label: "Xếp hạng ngữ cảnh", icon: Layers },
  ];

  let activeIndex = 0;
  const statusStr = currentStatus.toLowerCase();
  if (statusStr.includes("truy hồi") || statusStr.includes("retriev") || statusStr.includes("tìm kiếm")) {
    activeIndex = 1;
  } else if (statusStr.includes("xếp hạng") || statusStr.includes("rerank") || statusStr.includes("suy nghĩ") || statusStr.includes("tổng hợp")) {
    activeIndex = 2;
  }

  return (
    <div className="min-w-[280px] max-w-[420px] py-2">
      <div className="mb-4 flex items-center gap-2.5 text-[13.5px] font-bold text-teal-800">
        <span className="relative flex h-2.5 w-2.5">
          <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-teal-400 opacity-75" />
          <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-teal-600" />
        </span>
        <span className="animate-pulse">{currentStatus}</span>
      </div>

      <div className="space-y-3 relative before:absolute before:left-3.5 before:top-2 before:bottom-2 before:w-[1.5px] before:bg-slate-100">
        {steps.map(({ label, icon: Icon }, index) => {
          const isDone = index < activeIndex;
          const isActive = index === activeIndex;
          
          return (
            <div key={label} className="flex items-center gap-3 text-[13px] relative z-10">
              <motion.div 
                initial={{ scale: 0.8 }}
                animate={{ 
                  scale: isActive ? 1.1 : 1,
                  backgroundColor: isDone ? "#f0fdf4" : isActive ? "#f0fdfa" : "#f8fafc",
                  borderColor: isDone ? "#bbf7d0" : isActive ? "#99f6e4" : "#e2e8f0"
                }}
                className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full border text-[13px] shadow-sm transition-colors duration-300"
              >
                {isDone ? (
                  <CheckCircle2 className="h-4 w-4 text-emerald-600" />
                ) : (
                  <Icon className={`h-3.5 w-3.5 ${isActive ? "text-teal-600" : "text-slate-400"}`} />
                )}
              </motion.div>
              
              <span className={`font-semibold transition-colors duration-300 ${
                isDone ? "text-slate-400 line-through decoration-slate-300" : isActive ? "text-teal-900 font-bold" : "text-slate-500"
              }`}>
                {label}
              </span>
              
              {isActive && (
                <span className="puq-typing-dots ml-auto shrink-0">
                  <span className="bg-teal-500 animate-bounce" />
                  <span className="bg-teal-500 animate-bounce [animation-delay:0.2s]" />
                  <span className="bg-teal-500 animate-bounce [animation-delay:0.4s]" />
                </span>
              )}
            </div>
          );
        })}
      </div>

      <div className="mt-5 space-y-2">
        <div className="h-2 w-full animate-pulse rounded-full bg-slate-100/60" />
        <div className="h-2 w-[85%] animate-pulse rounded-full bg-slate-100/60 [animation-delay:150ms]" />
      </div>
    </div>
  );
}

export default function MessageList({ messages, isLoading = false, streamingStatus = null }: MessageListProps) {
  if (messages.length === 0 && !isLoading) {
    return (
      <div className="flex h-full flex-col items-center justify-center py-12 text-slate-400">
        <div className="mb-6 flex h-16 w-16 items-center justify-center rounded-3xl bg-slate-100 text-slate-400 border border-slate-200/40 shadow-sm">
          <Sparkles className="h-8 w-8 text-teal-600" strokeWidth={1.5} />
        </div>
        <h3 className="text-[17px] font-bold text-slate-950">Bắt đầu trò chuyện</h3>
        <p className="mt-2 max-w-[280px] text-center text-[14.5px] leading-relaxed opacity-70">
          Hãy đặt một câu hỏi để AI phân tích và tìm trích dẫn từ video học tập của bạn.
        </p>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-6 pb-4">
      <AnimatePresence initial={false}>
        {messages.map((message, index) => {
          const isUser = message.role === "user";
          const isLatestAssistant = !isUser && index === messages.length - 1;
          const isAssistantWaiting = isLatestAssistant && isLoading && !message.content && !message.response;
          const showAssistantBubble = isUser || message.content.trim() !== "" || message.response || isAssistantWaiting;

          if (!showAssistantBubble) return null;

          const isSmallBubble = !isUser && message.content.length < 10 && !message.response && !isAssistantWaiting;
          const isStreaming = isLoading && isLatestAssistant && !message.response;

          return (
            <motion.div
              key={message.id}
              initial={{ opacity: 0, y: 15, scale: 0.97 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: -10 }}
              transition={{ type: "spring", stiffness: 400, damping: 28 }}
              className={`flex w-full min-w-0 gap-4 ${isUser ? "flex-row-reverse" : "flex-row"}`}
            >
              <div className={`mt-1 flex h-9 w-9 shrink-0 items-center justify-center rounded-2xl shadow-sm border transition-all duration-300 ${
                isUser ? "bg-slate-900 text-white border-slate-950" : "bg-white text-teal-600 border-slate-200/60"
              }`}>
                {isUser ? <User className="h-4 w-4" /> : <Sparkles className="h-4 w-4" />}
              </div>

              <div className={`group relative w-fit min-w-0 min-h-[44px] max-w-[85%] sm:max-w-[75%] px-6 py-3 transition-all duration-300 flex items-center overflow-hidden ${
                isUser
                  ? "rounded-[1.75rem] rounded-tr-none bg-slate-900 text-white shadow-md shadow-slate-900/5 border border-slate-950"
                  : `${isSmallBubble ? "rounded-[1.75rem]" : "rounded-[1.75rem] rounded-tl-none"} border ${
                      isStreaming 
                        ? "border-teal-300 shadow-[0_0_20px_rgba(20,184,166,0.1)] bg-white" 
                        : "border-slate-200/80 bg-white/80"
                    } text-slate-800 shadow-[0_2px_8px_rgba(15,23,42,0.03)] backdrop-blur-md hover:border-slate-300/80 hover:bg-white hover:shadow-[0_8px_24px_rgba(15,23,42,0.06)]`
              }`}>
                {/* Subtle streaming glow background pulse */}
                {isStreaming && (
                  <motion.div 
                    animate={{ opacity: [0.15, 0.3, 0.15] }}
                    transition={{ repeat: Infinity, duration: 2, ease: "easeInOut" }}
                    className="absolute inset-0 bg-gradient-to-r from-teal-500/5 to-emerald-500/5 pointer-events-none"
                  />
                )}

                {isUser ? (
                  <p className="whitespace-pre-wrap text-[15px] font-medium leading-relaxed tracking-tight">{message.content}</p>
                ) : (
                  <div className="flex min-w-0 max-w-full flex-col gap-3">
                    {isAssistantWaiting ? (
                      <LoadingSteps status={streamingStatus} />
                    ) : (
                      <>
                        {message.response?.type === "quiz" && message.response.quizzes ? (
                          <QuizComponent questions={message.response.quizzes} />
                        ) : message.response?.type === "math" && message.response.math_data ? (
                          <MathComponent data={message.response.math_data} />
                        ) : (
                          <MarkdownRenderer
                            content={message.content}
                            response={message.response}
                            tempContext={message.tempContext}
                            isStreaming={isStreaming}
                          />
                        )}
                        {message.response && <CitationList response={message.response} />}
                      </>
                    )}
                  </div>
                )}
              </div>
            </motion.div>
          );
        })}
      </AnimatePresence>
    </div>
  );
}
