import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { ChatBubbleIcon, SummaryIcon } from "../components/shared/Icons";

type AppSection = "chatspace" | "summaryhub";

function GatewayCard({
  title,
  description,
  cta,
  tone,
  active,
  onClick,
  onHover,
  onLeave,
  icon,
}: {
  title: string;
  description: string;
  cta: string;
  tone: "violet" | "cyan";
  active: boolean;
  onClick: () => void;
  onHover: () => void;
  onLeave: () => void;
  icon: React.ReactNode;
}) {
  const iconBoxClass = tone === "violet" ? "bg-violet-600 text-white" : "bg-cyan-500 text-white";
  const ctaClass = tone === "violet" ? "text-violet-700" : "text-cyan-700";
  const toneGlowClass = tone === "violet" ? "from-violet-200/90 to-fuchsia-100/70" : "from-cyan-100/90 to-emerald-100/70";

  return (
    <motion.button
      layout
      type="button"
      onClick={onClick}
      onMouseEnter={onHover}
      onMouseLeave={onLeave}
      whileHover={{ scale: 1.012, y: -5 }}
      whileTap={{ scale: 0.985 }}
      transition={{ 
        layout: { duration: 0.8, ease: [0.22, 1, 0.36, 1] },
        scale: { type: "spring", stiffness: 300, damping: 25 },
        y: { type: "spring", stiffness: 300, damping: 25 }
      }}
      className={`puq-gateway-card group relative flex min-h-[540px] w-full flex-col justify-between overflow-hidden rounded-2xl bg-white/80 p-9 text-left backdrop-blur-md shadow-[0_8px_30px_rgb(0,0,0,0.04)] hover:shadow-[0_20px_50px_rgba(37,99,235,0.1)] ${
        active ? "ring-2 ring-cyan-300/70 shadow-[0_20px_50px_rgba(6,182,212,0.15)]" : "opacity-95"
      }`}
    >
      <div className={`pointer-events-none absolute -right-20 -top-14 h-48 w-48 rounded-full bg-gradient-to-br ${toneGlowClass}`} />
      <div className="pointer-events-none absolute -left-16 bottom-4 h-24 w-24 rounded-full bg-white/55 blur-md" />
      <div>
        <div className={`mb-6 grid h-16 w-16 place-items-center rounded-xl shadow-lg shadow-slate-200 ${iconBoxClass}`}>
          {icon}
        </div>
        <h3 className="font-['Plus_Jakarta_Sans',sans-serif] text-[2rem] font-bold leading-9 text-[#181c23]">{title}</h3>
        <p className="mt-4 max-w-xl text-xl leading-8 text-[#414754]">{description}</p>
      </div>
      <div className={`mt-8 flex items-center gap-2 text-lg font-semibold ${ctaClass}`}>
        <span>{cta}</span>
        <span aria-hidden="true" className="transition group-hover:translate-x-1">→</span>
      </div>
    </motion.button>
  );
}

export default function GatewayPage() {
  const [hoveredCard, setHoveredCard] = useState<AppSection | null>(null);
  const navigate = useNavigate();

  const getFlexClass = (section: AppSection) => {
    if (!hoveredCard) return "flex-1";
    return hoveredCard === section ? "flex-[2.5]" : "flex-1";
  };

  const handleLogout = () => {
    navigate("/login");
  };

  return (
    <div className="relative z-10 min-h-screen">
      <header className="sticky top-0 z-20 flex h-16 items-center justify-between border-b border-slate-200/80 bg-white/80 px-6 shadow-[0_1px_2px_rgba(0,0,0,0.05)] backdrop-blur-sm">
        <div className="flex items-center gap-8">
          <h1 className="font-['Plus_Jakarta_Sans',sans-serif] text-[1.35rem] font-bold text-[#2563eb]">Workspace Selector</h1>
          <div className="hidden items-center rounded-lg bg-[#f1f3fe] px-4 py-2.5 md:flex md:w-64">
            <span className="mr-2 text-slate-400">⌕</span>
            <span className="text-sm text-slate-500">Search workspaces...</span>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <div className="text-right">
            <p className="text-sm font-bold text-[#181c23]">Admin User</p>
            <p className="text-xs text-[#717786]">Demo Account</p>
          </div>
          <button
            type="button"
            onClick={handleLogout}
            className="rounded-lg border border-slate-300 px-3 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-100"
          >
            Log out
          </button>
        </div>
      </header>

      <main className="relative overflow-hidden px-6 py-10">
        <div className="puq-float-orb pointer-events-none absolute -left-20 -top-20 h-60 w-60 rounded-full bg-cyan-300/25 blur-3xl" />
        <div className="puq-float-orb pointer-events-none absolute -bottom-16 -right-20 h-60 w-60 rounded-full bg-emerald-300/25 blur-3xl" style={{ animationDelay: "600ms" }} />

        <div className="mx-auto max-w-[1280px]">
          <div className="mb-10 text-center">
            <span className="mb-4 inline-flex rounded-full border border-cyan-200 bg-cyan-50 px-3 py-1 text-xs font-semibold text-cyan-800">
              UI Updated • Motion Pass v2
            </span>
            <h2 className="font-['Plus_Jakarta_Sans',sans-serif] text-5xl font-extrabold tracking-[-0.02em] text-[#181c23]">
              Choice Gateway
            </h2>
            <p className="mt-3 text-xl text-[#414754]">
              Select your specialized environment to begin your high-productivity session.
            </p>
          </div>

          <motion.div 
            layout
            transition={{ duration: 0.5, ease: [0.22, 1, 0.36, 1] }}
            className="puq-split flex flex-col lg:flex-row gap-10"
          >
            <div className={`transition-all duration-500 ease-[cubic-bezier(0.22,1,0.36,1)] ${getFlexClass("chatspace")}`}>
              <GatewayCard
                title="Chatspace Agent"
                description="Engage in natural dialogue with your technical documentation. Deep-dive into complex APIs and internal wikis with AI precision."
                cta="Enter Workspace"
                tone="violet"
                active={hoveredCard === "chatspace"}
                onClick={() => navigate("/workspace/chatspace")}
                onHover={() => setHoveredCard("chatspace")}
                onLeave={() => setHoveredCard(null)}
                icon={<ChatBubbleIcon />}
              />
            </div>
            <div className={`transition-all duration-500 ease-[cubic-bezier(0.22,1,0.36,1)] ${getFlexClass("summaryhub")}`}>
              <GatewayCard
                title="Summary Hub"
                description="Instant distillations of video content into actionable insights. Save hours of meeting time with high-fidelity automated transcripts and summaries."
                cta="Launch Analytics"
                tone="cyan"
                active={hoveredCard === "summaryhub"}
                onClick={() => navigate("/workspace/summaryhub")}
                onHover={() => setHoveredCard("summaryhub")}
                onLeave={() => setHoveredCard(null)}
                icon={<SummaryIcon />}
              />
            </div>
          </motion.div>
        </div>
      </main>

      <footer className="px-6 py-8 text-center text-sm text-[#717786]">© 2024 Hub Central. Enterprise Intelligence Suite.</footer>
    </div>
  );
}
