import { Play, ExternalLink } from "lucide-react";
import { buildCitationItems } from "../../lib/utils/citation";
import type { RagResponse } from "../../types/rag";

type CitationListProps = {
  response: RagResponse;
};

export default function CitationList({ response }: CitationListProps) {
  const citations = buildCitationItems(response.text, response);

  if (citations.length === 0) {
    return null;
  }

  return (
    <div className="mt-4 border-t border-violet-100/30 pt-6">
      <div className="flex items-center gap-3 mb-4">
        <div className="flex h-5 w-5 items-center justify-center rounded-full bg-violet-600/10 text-violet-600">
          <ExternalLink className="h-3 w-3" />
        </div>
        <span className="text-[11px] font-black uppercase tracking-[0.2em] text-slate-500">Nguồn tham khảo từ bài giảng</span>
        <div className="h-px flex-1 bg-gradient-to-r from-violet-100/60 to-transparent" />
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {citations.map((citation, index) => (
          <a
            key={`${citation.marker}-${index}`}
            href={citation.video_url || "#"}
            target="_blank"
            rel="noreferrer"
            className="puq-glass group flex items-center gap-4 rounded-2xl border border-white/40 px-4 py-3 shadow-sm transition-all hover:border-violet-300/50 hover:bg-white hover:shadow-xl hover:shadow-violet-500/10 active:scale-[0.98]"
          >
            <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-violet-50 text-violet-600 shadow-inner transition-all group-hover:bg-violet-600 group-hover:text-white group-hover:rotate-6">
              <Play className="h-4 w-4 fill-current" />
            </div>
            <div className="flex flex-col min-w-0">
              <span className="truncate text-[14px] font-black text-slate-800 leading-tight group-hover:text-violet-900">
                {citation.marker} {citation.title || "Video bài giảng"}
              </span>
              <span className="mt-0.5 text-[11px] font-bold text-slate-400 flex items-center gap-2">
                <span className="rounded bg-slate-100 px-1 py-0.5 text-[9px] group-hover:bg-violet-100 group-hover:text-violet-600 transition-colors">TIMESTAMP</span>
                {citation.start_timestamp}
              </span>
            </div>
          </a>
        ))}
      </div>
    </div>
  );
}

