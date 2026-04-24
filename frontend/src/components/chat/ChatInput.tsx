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
        className="puq-glass group relative flex items-center overflow-hidden rounded-[2rem] border border-white/60 shadow-2xl shadow-violet-900/10 transition-all duration-500 focus-within:border-violet-400 focus-within:bg-white/90 focus-within:shadow-violet-900/20"
      >
        {contextPill ? (
          <div className="ml-3 flex shrink-0 items-center gap-2 rounded-2xl bg-violet-600/10 py-2 pl-3 pr-2 text-[11px] font-black text-violet-700 backdrop-blur-md transition-all animate-in fade-in zoom-in duration-300 max-w-[40%] sm:max-w-[50%]">
            <span className="truncate">Ngữ cảnh: {contextPill.title}</span>
            <button
              type="button"
              onClick={onClearContextPill}
              className="rounded-lg bg-white/80 px-2 py-1 text-[9px] font-black uppercase tracking-wider text-violet-600 shadow-sm transition-all hover:bg-violet-600 hover:text-white active:scale-90"
            >
              Gỡ bỏ
            </button>
          </div>
        ) : null}
        
        <input
          value={value}
          onChange={(event) => setValue(event.target.value)}
          placeholder={contextPill ? "Đặt câu hỏi về context này..." : "Hỏi bất cứ điều gì về tài liệu học tập của bạn..."}
          className={`flex-1 bg-transparent py-5 text-[15px] font-medium outline-none placeholder:text-slate-400/80 ${contextPill ? 'pl-3' : 'pl-7'} pr-16`}
          disabled={blocked}
        />
        
        <button
          type="submit"
          disabled={blocked || !value.trim()}
          className="absolute right-2.5 top-1/2 flex h-11 w-11 -translate-y-1/2 cursor-pointer items-center justify-center rounded-2xl bg-violet-600 text-white shadow-lg shadow-violet-600/30 transition-all hover:bg-violet-700 hover:shadow-violet-700/40 active:scale-90 disabled:cursor-not-allowed disabled:bg-slate-200 disabled:text-slate-400 disabled:shadow-none"
        >
          {isSubmitting ? (
             <svg className="h-4 w-4 animate-spin text-white" fill="none" viewBox="0 0 24 24"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg>
          ) : (
            <svg className="h-5 w-5 transition-transform group-focus-within:translate-x-0.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round"><path d="M5 12h14M12 5l7 7-7 7"/></svg>
          )}
        </button>
      </form>
    </div>
  );
}
