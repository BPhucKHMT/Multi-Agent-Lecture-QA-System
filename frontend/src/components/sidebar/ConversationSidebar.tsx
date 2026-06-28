import { motion } from "framer-motion";

type AppSection = "chatspace" | "summaryhub";

type HistoryItem = {
  id: string;
  title: string;
  subtitle: string;
};

type ConversationSidebarProps = {
  activeSection: AppSection;
  onChangeSection: (section: AppSection) => void;
  conversationId: string;
  historyItems: HistoryItem[];
  onNewConversation: () => void;
  onSelectConversation: (id: string) => void;
};

function SidebarSparkIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true" className="h-4.5 w-4.5 text-white">
      <path fill="currentColor" d="m12 1.5 1.9 4.6L18.5 8l-4.6 1.9L12 14.5 10.1 9.9 5.5 8l4.6-1.9L12 1.5Zm6.4 11.4 1 2.3 2.3 1-2.3 1-1 2.3-1-2.3-2.3-1 2.3-1 1-2.3ZM5.6 13.8l1 2.3 2.3 1-2.3 1-1 2.3-1-2.3-2.3-1 2.3-1 1-2.3Z" />
    </svg>
  );
}

function NavigationButton({
  active,
  label,
  onClick,
}: {
  active: boolean;
  label: string;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`relative flex w-full items-center rounded-xl px-4 py-3 text-left text-[15px] font-semibold transition-all duration-300 active:scale-[0.97] focus:outline-none ${
        active ? "text-slate-900 font-bold" : "text-slate-500 hover:text-slate-800"
      }`}
    >
      {active && (
        <motion.div
          layoutId="activeTabPill"
          className="absolute inset-0 rounded-xl bg-slate-100 shadow-[inset_0_1px_rgba(255,255,255,0.8)] border border-slate-200/40"
          transition={{ type: "spring", stiffness: 380, damping: 30 }}
        />
      )}
      {active && (
        <span className="relative z-10 mr-2 h-1.5 w-1.5 rounded-full bg-teal-600 shadow-[0_0_8px_rgba(13,148,136,0.5)]" />
      )}
      <span className="relative z-10">{label}</span>
    </button>
  );
}

export default function ConversationSidebar({
  activeSection,
  onChangeSection,
  conversationId,
  historyItems,
  onNewConversation,
  onSelectConversation,
}: ConversationSidebarProps) {
  return (
    <aside className="flex h-screen w-[340px] flex-col border-r border-slate-200/60 bg-white/30 p-6 backdrop-blur-2xl">
      <div className="mb-6 flex items-center gap-3">
        <div className="grid h-9 w-9 place-items-center rounded-xl bg-teal-600 shadow-sm">
          <SidebarSparkIcon />
        </div>
        <div>
          <p className="font-['Plus_Jakarta_Sans',sans-serif] text-base font-bold text-slate-900">Không gian PUQ</p>
          <p className="text-xs text-slate-500">ID: {conversationId.slice(0, 8)}</p>
        </div>
      </div>

      <div className="space-y-1.5 border-b border-slate-200/50 pb-5">
        <NavigationButton active={activeSection === "chatspace"} label="Chatspace" onClick={() => onChangeSection("chatspace")} />
        <NavigationButton active={activeSection === "summaryhub"} label="Trung tâm tóm tắt" onClick={() => onChangeSection("summaryhub")} />
      </div>

      <div className="mt-4 flex min-h-0 flex-1 flex-col">
        <p className="mb-2 text-xs font-semibold uppercase tracking-[0.08em] text-slate-500">Lịch sử chat</p>
        <div className="min-h-0 flex-1 space-y-2 overflow-y-auto pr-1">
          {historyItems.length === 0 ? (
            <div className="mt-8 flex flex-col items-center justify-center text-center opacity-60">
              <svg className="mb-2 h-8 w-8 text-slate-300" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
              </svg>
              <p className="px-2 text-[13px] font-medium text-slate-500">
                Chưa có lịch sử.
                <br />Bắt đầu trò chuyện để lưu.
              </p>
            </div>
          ) : (
            historyItems.map((item) => (
              <button
                key={item.id}
                type="button"
                onClick={() => onSelectConversation(item.id)}
                className={`group w-full rounded-xl border px-4 py-3 text-left transition-all duration-300 ease-out active:scale-[0.97] hover:translate-x-1 ${
                  conversationId === item.id
                    ? "border-slate-200 bg-white shadow-sm"
                    : "border-transparent bg-white/40 hover:border-slate-200 hover:bg-white hover:shadow-sm"
                }`}
              >
                <p className={`truncate text-sm font-bold transition-colors duration-300 ${conversationId === item.id ? "text-teal-700" : "text-slate-600 group-hover:text-slate-800"}`}>
                  {item.title}
                </p>
                <p className="truncate text-xs text-slate-400 mt-0.5">{item.subtitle}</p>
              </button>
            ))
          )}
        </div>
      </div>

      <button
        type="button"
        onClick={onNewConversation}
        className="group mt-5 flex items-center justify-center gap-2 rounded-xl bg-slate-900 px-4 py-3 text-[15px] font-semibold text-white shadow-md shadow-slate-900/10 transition-all duration-300 ease-out hover:bg-slate-800 active:scale-[0.97]"
      >
        <span className="text-lg leading-none transition-transform duration-300 group-hover:rotate-90 group-hover:scale-125">+</span> Hội thoại mới
      </button>
    </aside>
  );
}
