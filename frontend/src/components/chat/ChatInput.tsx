import { FormEvent, useState } from "react";

type ChatContextPill = {
  title: string;
  subtitle: string;
};

type ChatInputProps = {
  disabled?: boolean;
  onSubmit: (prompt: string) => Promise<void>;
  contextPill?: ChatContextPill | null;
  onClearContextPill?: () => void;
};

export default function ChatInput({
  disabled = false,
  onSubmit,
  contextPill = null,
  onClearContextPill,
}: ChatInputProps) {
  const [value, setValue] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    const prompt = value.trim();

    if (!prompt || disabled || isSubmitting) {
      return;
    }

    setValue("");
    setIsSubmitting(true);
    try {
      await onSubmit(prompt);
    } finally {
      setIsSubmitting(false);
    }
  };

  const blocked = disabled || isSubmitting;

  return (
    <div className="w-full">
      <form
        onSubmit={handleSubmit}
        className="relative flex items-center overflow-hidden rounded-full border border-violet-200/50 bg-white/70 shadow-xl shadow-violet-900/10 backdrop-blur-xl transition-all focus-within:border-violet-400 focus-within:bg-white"
      >
        {contextPill ? (
          <div className="ml-2 flex shrink-0 items-center gap-2 rounded-full bg-violet-100/90 py-1.5 pl-3 pr-1 text-[11px] font-medium text-violet-900 backdrop-blur-sm transition-all animate-in fade-in slide-in-from-left-2 duration-300 max-w-[40%] sm:max-w-[50%]">
            <span className="truncate">Ngữ cảnh: {contextPill.title}</span>
            <button
              type="button"
              onClick={onClearContextPill}
              className="rounded-full bg-white px-2 py-0.5 text-[10px] font-bold text-violet-700 shadow-sm transition-all hover:bg-violet-50 hover:text-violet-800 active:scale-95"
            >
              Xóa
            </button>
          </div>
        ) : null}
        
        <input
          value={value}
          onChange={(event) => setValue(event.target.value)}
          placeholder={contextPill ? "Đặt câu hỏi về context này..." : "Hỏi bất cứ điều gì về tài liệu học tập của bạn..."}
          className={`puq-input flex-1 bg-transparent py-4 text-[15px] outline-none placeholder:text-slate-400 ${contextPill ? 'pl-3' : 'pl-6'} pr-14`}
          disabled={blocked}
        />
        
        <button
          type="submit"
          disabled={blocked || !value.trim()}
          className="absolute right-2 top-1/2 flex h-10 w-10 -translate-y-1/2 cursor-pointer items-center justify-center rounded-full bg-violet-600 text-white shadow-md transition-all hover:bg-violet-700 active:scale-90 disabled:cursor-not-allowed disabled:bg-slate-200 disabled:text-slate-400 disabled:shadow-none"
        >
          {isSubmitting ? (
             <svg className="h-4 w-4 animate-spin text-white" fill="none" viewBox="0 0 24 24"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg>
          ) : (
            <svg className="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><path d="M5 12h14M12 5l7 7-7 7"/></svg>
          )}
        </button>
      </form>
    </div>
  );
}
