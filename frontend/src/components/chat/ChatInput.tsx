import { FormEvent, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";

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
        className="puq-glass group relative flex items-center overflow-hidden rounded-[2rem] border border-slate-200/80 bg-white/70 shadow-[0_8px_30px_rgba(15,23,42,0.04)] transition-all duration-500 focus-within:border-teal-400/80 focus-within:bg-white focus-within:shadow-[0_0_25px_rgba(20,184,166,0.12)]"
      >
        <AnimatePresence mode="wait">
          {contextPill && (
            <motion.div
              initial={{ opacity: 0, scale: 0.8, x: -15 }}
              animate={{ opacity: 1, scale: 1, x: 0 }}
              exit={{ opacity: 0, scale: 0.8, x: -15 }}
              transition={{ type: "spring", stiffness: 400, damping: 25 }}
              className="ml-3 flex shrink-0 items-center gap-2 rounded-2xl bg-teal-50 border border-teal-100 py-2 pl-3 pr-2 text-[11px] font-bold text-teal-800 backdrop-blur-md max-w-[40%] sm:max-w-[50%]"
            >
              <span className="truncate">Ngữ cảnh: {contextPill.title}</span>
              <button
                type="button"
                onClick={onClearContextPill}
                className="rounded-lg bg-white px-2 py-1 text-[9px] font-bold uppercase tracking-wider text-teal-700 shadow-sm border border-teal-100 transition-all hover:bg-teal-600 hover:text-white active:scale-90"
              >
                Gỡ bỏ
              </button>
            </motion.div>
          )}
        </AnimatePresence>
        
        <input
          value={value}
          onChange={(event) => setValue(event.target.value)}
          placeholder={contextPill ? "Đặt câu hỏi về context này..." : "Hỏi bất cứ điều gì về tài liệu học tập của bạn..."}
          className={`flex-1 bg-transparent py-5 text-[15px] font-semibold outline-none placeholder:text-slate-400/70 ${contextPill ? 'pl-3' : 'pl-7'} pr-16 text-slate-800`}
          disabled={blocked}
        />
        
        <motion.button
          type="submit"
          disabled={blocked || !value.trim()}
          whileHover={blocked || !value.trim() ? {} : { scale: 1.05 }}
          whileTap={blocked || !value.trim() ? {} : { scale: 0.95 }}
          className="absolute right-2.5 top-1/2 flex h-11 w-11 -translate-y-1/2 cursor-pointer items-center justify-center rounded-2xl bg-slate-900 text-white shadow-md shadow-slate-900/10 transition-all disabled:cursor-not-allowed disabled:bg-slate-100 disabled:text-slate-400 disabled:shadow-none"
        >
          {isSubmitting ? (
             <svg className="h-4 w-4 animate-spin text-white" fill="none" viewBox="0 0 24 24"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg>
          ) : (
            <motion.svg 
              animate={value.trim() && !blocked ? { x: [0, 3, 0] } : {}}
              transition={{ repeat: Infinity, duration: 1.2, ease: "easeInOut" }}
              className="h-5 w-5" 
              viewBox="0 0 24 24" 
              fill="none" 
              stroke="currentColor" 
              strokeWidth="3" 
              strokeLinecap="round" 
              strokeLinejoin="round"
            >
              <path d="M5 12h14M12 5l7 7-7 7"/>
            </motion.svg>
          )}
        </motion.button>
      </form>
    </div>
  );
}
