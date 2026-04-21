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
    <div className="mt-4 border-t border-violet-100/50 pt-4">
      <div className="flex items-center gap-2 mb-3">
        <span className="text-[11px] font-extrabold uppercase tracking-[0.1em] text-slate-400">Nguồn tham khảo</span>
        <div className="h-px flex-1 bg-violet-100/40" />
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        {citations.map((citation, index) => (
          <a
            key={`${citation.marker}-${index}`}
            href={citation.video_url || "#"}
            target="_blank"
            rel="noreferrer"
            className="group flex items-center gap-3 rounded-2xl border border-transparent bg-slate-100/50 px-4 py-2.5 transition-all hover:border-violet-200/50 hover:bg-violet-50/50 hover:shadow-sm active:scale-95"
          >
            <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-xl bg-white text-violet-600 shadow-sm transition-all group-hover:bg-violet-600 group-hover:text-white group-hover:scale-110">
              <Play className="h-3 w-3 fill-current" />
            </div>
            <div className="flex flex-col min-w-0">
              <span className="truncate text-[13.5px] font-bold text-slate-700 group-hover:text-violet-800">
                {citation.marker} {citation.title || "Video Lecture"}
              </span>
              <span className="text-[10.5px] font-bold text-slate-400 flex items-center gap-1.5 px-0.5">
                Timestamp: {citation.start_timestamp}
                <ExternalLink className="h-2.5 w-2.5 opacity-0 -translate-x-1 group-hover:opacity-60 group-hover:translate-x-0 transition-all" />
              </span>
            </div>
          </a>
        ))}
      </div>
    </div>
  );
}

