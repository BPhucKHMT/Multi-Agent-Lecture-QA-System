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
      className={`relative flex w-full items-center overflow-hidden rounded-xl px-4 py-3 text-left text-[15px] font-semibold transition-all duration-200 ease-out active:scale-[0.98] ${
        active 
          ? "bg-violet-100/60 text-violet-800 shadow-[inset_0_1px_rgba(255,255,255,0.8)] shadow-violet-200/40" 
          : "text-slate-500 hover:bg-violet-50/50 hover:text-violet-700 hover:shadow-sm"
      }`}
    >
      {active && (
        <span className="absolute inset-y-2.5 left-2 w-1 rounded-full bg-violet-600 shadow-[0_0_8px_rgba(124,58,237,0.4)]" />
      )}
      <span className={active ? "pl-2 transition-all" : "transition-all"}>{label}</span>
    </button>
  );
}

export default function ConversationSidebar({
  activeSection,
  onChangeSection,
  conversationId,
  historyItems,
  onNewConversation,
}: ConversationSidebarProps) {
  return (
    <aside className="flex h-screen w-[340px] flex-col border-r border-violet-100/60 bg-white/50 p-6 backdrop-blur-2xl">
      <div className="mb-6 flex items-center gap-3">
        <div className="grid h-9 w-9 place-items-center rounded-xl bg-gradient-to-br from-violet-600 to-indigo-600 shadow-md shadow-violet-500/20">
          <SidebarSparkIcon />
        </div>
        <div>
          <p className="font-['Plus_Jakarta_Sans',sans-serif] text-base font-bold text-slate-900">PUQ Workspace</p>
          <p className="text-xs text-slate-500">ID: {conversationId.slice(0, 8)}</p>
        </div>
      </div>

      <div className="space-y-1.5 border-b border-violet-100/50 pb-5">
        <NavigationButton active={activeSection === "chatspace"} label="Chatspace" onClick={() => onChangeSection("chatspace")} />
        <NavigationButton active={activeSection === "summaryhub"} label="Summary Hub" onClick={() => onChangeSection("summaryhub")} />
      </div>

      <div className="mt-4 flex min-h-0 flex-1 flex-col">
        <p className="mb-2 text-xs font-semibold uppercase tracking-[0.08em] text-slate-500">Lịch sử chat</p>
        <div className="min-h-0 flex-1 space-y-2 overflow-y-auto pr-1">
          {historyItems.length === 0 ? (
            <div className="mt-8 flex flex-col items-center justify-center text-center opacity-60">
              <svg className="mb-2 h-8 w-8 text-violet-300" fill="none" viewBox="0 0 24 24" stroke="currentColor">
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
                className="w-full rounded-xl border border-transparent bg-white/40 px-4 py-3 text-left transition-all duration-200 ease-out hover:border-violet-200 hover:bg-violet-50 hover:shadow-sm active:scale-[0.98]"
              >
                <p className="truncate text-sm font-semibold text-slate-700">{item.title}</p>
                <p className="truncate text-xs text-slate-500">{item.subtitle}</p>
              </button>
            ))
          )}
        </div>
      </div>

      <button
        type="button"
        onClick={onNewConversation}
        className="mt-5 flex items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-violet-600 to-indigo-600 px-4 py-3 text-[15px] font-semibold text-white shadow-md shadow-violet-500/20 transition-all duration-200 ease-out hover:from-violet-700 hover:to-indigo-700 hover:shadow-lg active:scale-[0.98]"
      >
        <span className="text-lg leading-none">+</span> New chat
      </button>
    </aside>
  );
}
