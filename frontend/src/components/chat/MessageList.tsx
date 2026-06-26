import { User, Sparkles, Search, Layers, BrainCircuit } from "lucide-react";
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

  return (
    <div className="min-w-[260px] max-w-[420px] py-1">
      <div className="mb-3 flex items-center gap-2 text-[13px] font-semibold text-violet-700">
        <span className="relative flex h-2.5 w-2.5">
          <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-violet-400 opacity-60" />
          <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-violet-600" />
        </span>
        <span>{currentStatus}</span>
      </div>

      <div className="space-y-2">
        {steps.map(({ label, icon: Icon }, index) => (
          <div key={label} className="flex items-center gap-2 text-[12.5px] text-slate-500">
            <div className="flex h-6 w-6 items-center justify-center rounded-full bg-violet-50 text-violet-500">
              <Icon className="h-3.5 w-3.5" />
            </div>
            <span>{label}</span>
            <span className="puq-typing-dots ml-auto" style={{ animationDelay: `${index * 120}ms` }}>
              <span className="bg-violet-400" />
              <span className="bg-violet-400" />
              <span className="bg-violet-400" />
            </span>
          </div>
        ))}
      </div>

      <div className="mt-4 space-y-2">
        <div className="h-2.5 w-full animate-pulse rounded-full bg-gradient-to-r from-violet-100 via-indigo-100 to-sky-100" />
        <div className="h-2.5 w-4/5 animate-pulse rounded-full bg-gradient-to-r from-violet-100 via-indigo-100 to-sky-100 [animation-delay:120ms]" />
      </div>
    </div>
  );
}

export default function MessageList({ messages, isLoading = false, streamingStatus = null }: MessageListProps) {
  if (messages.length === 0 && !isLoading) {
    return (
      <div className="flex h-full flex-col items-center justify-center py-12 text-slate-400">
        <div className="mb-6 flex h-16 w-16 items-center justify-center rounded-3xl bg-violet-50 text-violet-300">
          <Sparkles className="h-8 w-8" strokeWidth={1.5} />
        </div>
        <h3 className="text-[17px] font-bold text-slate-900">Bắt đầu trò chuyện</h3>
        <p className="mt-2 max-w-[280px] text-center text-[14.5px] leading-relaxed opacity-70">
          Hãy đặt một câu hỏi để AI phân tích và tìm trích dẫn từ video học tập của bạn.
        </p>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-6 pb-4">
      {messages.map((message, index) => {
        const isUser = message.role === "user";
        const isLatestAssistant = !isUser && index === messages.length - 1;
        const isAssistantWaiting = isLatestAssistant && isLoading && !message.content && !message.response;
        const showAssistantBubble = isUser || message.content.trim() !== "" || message.response || isAssistantWaiting;

        if (!showAssistantBubble) return null;

        const isSmallBubble = !isUser && message.content.length < 10 && !message.response && !isAssistantWaiting;

        return (
          <div
            key={message.id}
            className={`puq-message-enter flex w-full min-w-0 gap-4 ${isUser ? "flex-row-reverse" : "flex-row"}`}
            style={{ animationDelay: getMessageAnimationDelay() }}
          >
            <div className={`mt-1 flex h-9 w-9 shrink-0 items-center justify-center rounded-2xl shadow-sm border ${
              isUser ? "bg-violet-700 text-white border-violet-800" : "bg-white text-violet-600 border-violet-100"
            }`}>
              {isUser ? <User className="h-4.5 w-4.5" /> : <Sparkles className="h-4.5 w-4.5" />}
            </div>

            <div className={`group relative w-fit min-w-0 min-h-[44px] max-w-[85%] sm:max-w-[75%] px-6 py-3 transition-all duration-300 flex items-center overflow-hidden ${
              isUser
                ? "rounded-[2rem] rounded-tr-none bg-gradient-to-br from-violet-600 via-indigo-600 to-indigo-700 text-white shadow-lg shadow-violet-500/20 ring-1 ring-white/20 ring-inset"
                : `${isSmallBubble ? "rounded-[2rem]" : "rounded-[2rem] rounded-tl-none"} border border-violet-100/60 bg-white/95 text-slate-800 puq-message-shadow backdrop-blur-md hover:shadow-xl hover:shadow-violet-500/5`
            }`}>
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
                          isStreaming={isLoading && !isUser && index === messages.length - 1 && !message.response}
                        />
                      )}
                      {message.response && <CitationList response={message.response} />}
                    </>
                  )}
                </div>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}
