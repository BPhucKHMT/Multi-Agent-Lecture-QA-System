import { User, Sparkles, Loader2 } from "lucide-react";
import MarkdownRenderer from "./MarkdownRenderer";
import CitationList from "./CitationList";
import QuizComponent from "./QuizComponent";
import MathComponent from "./MathComponent";
import type { ConversationMessage } from "../../store/conversationStore";

type MessageListProps = {
  messages: ConversationMessage[];
  isLoading?: boolean;
};

export default function MessageList({ messages, isLoading = false }: MessageListProps) {
  if (messages.length === 0) {
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
        
        const showAssistantBubble = !isUser && (message.content.trim() !== "" || message.response || !isLoading);

        if (!isUser && !showAssistantBubble) return null;

        const isSmallBubble = !isUser && message.content.length < 10 && !message.response;

        return (
          <div
            key={message.id}
            className={`puq-message-enter flex w-full gap-4 ${isUser ? "flex-row-reverse" : "flex-row"}`}
            style={{ animationDelay: `${index * 40}ms` }}
          >
            {/* Avatar / Icon circle */}
            <div className={`mt-1 flex h-9 w-9 shrink-0 items-center justify-center rounded-2xl shadow-sm border ${
              isUser ? "bg-violet-700 text-white border-violet-800" : "bg-white text-violet-600 border-violet-100"
            }`}>
              {isUser ? <User className="h-4.5 w-4.5" /> : <Sparkles className="h-4.5 w-4.5" />}
            </div>

            {/* Bubble */}
            <div className={`group relative w-fit min-w-[64px] min-h-[44px] max-w-[85%] sm:max-w-[75%] px-6 py-3 transition-all duration-300 flex items-center ${
              isUser 
                ? "rounded-[2rem] rounded-tr-none bg-gradient-to-br from-violet-600 via-indigo-600 to-indigo-700 text-white shadow-lg shadow-violet-500/20 ring-1 ring-white/20 ring-inset" 
                : `${isSmallBubble ? "rounded-[2rem]" : "rounded-[2rem] rounded-tl-none"} border border-violet-100/60 bg-white/95 text-slate-800 puq-message-shadow backdrop-blur-md hover:shadow-xl hover:shadow-violet-500/5`
            }`}>
              {isUser ? (
                <p className="whitespace-pre-wrap text-[15px] font-medium leading-relaxed tracking-tight">{message.content}</p>
              ) : (

                <div className="flex flex-col gap-3">
                  {!message.content && !message.response && !message.tempContext ? (
                    <div className="flex items-center gap-1.5 py-1 opacity-40">
                      <div className="h-1.5 w-1.5 animate-bounce rounded-full bg-violet-600" />
                      <div className="h-1.5 w-1.5 animate-bounce rounded-full bg-violet-600 [animation-delay:0.2s]" />
                      <div className="h-1.5 w-1.5 animate-bounce rounded-full bg-violet-600 [animation-delay:0.4s]" />
                    </div>
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
                          isStreaming={!isUser && index === messages.length - 1 && !message.response}
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

      {isLoading && (
        <div className="puq-message-enter flex w-full gap-4 flex-row">
          <div className="mt-1 flex h-9 w-9 shrink-0 items-center justify-center rounded-2xl border border-violet-100 bg-white text-violet-600 shadow-sm">
            <Loader2 className="h-4.5 w-4.5 animate-spin" />
          </div>
          <div className="rounded-2xl rounded-tl-none border border-violet-100/60 bg-white/80 px-5 py-3 shadow-sm backdrop-blur-sm">
            <div className="flex items-center gap-3 text-sm font-semibold text-violet-600/80">
              <span>Đang phân tích dữ liệu</span>
              <span className="puq-typing-dots">
                <span className="bg-violet-400" />
                <span className="bg-violet-400" />
                <span className="bg-violet-400" />
              </span>
            </div>
          </div>
        </div>
      )}

    </div>
  );
}

