import React, { useState, useCallback, memo } from "react";
import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { ChatBubbleIcon, SummaryIcon } from "../components/shared/Icons";

type AppSection = "chatspace" | "summaryhub";

const GatewayCard = memo(({
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
  tone: "slate" | "cyan";
  active: boolean;
  onClick: () => void;
  onHover: () => void;
  onLeave: () => void;
  icon: React.ReactNode;
}) => {
  const iconBoxClass = tone === "slate" ? "bg-slate-900 text-white" : "bg-cyan-500 text-white";
  const ctaClass = tone === "slate" ? "text-slate-800" : "text-cyan-700";
  const toneGlowClass = tone === "slate" ? "from-slate-200/90 to-slate-100/70" : "from-cyan-100/90 to-emerald-100/70";

  const [coords, setCoords] = useState({ x: 0, y: 0 });
  const [isHovered, setIsHovered] = useState(false);

  const handleMouseMove = (e: React.MouseEvent<HTMLButtonElement>) => {
    const rect = e.currentTarget.getBoundingClientRect();
    setCoords({
      x: e.clientX - rect.left,
      y: e.clientY - rect.top,
    });
  };

  return (
    <motion.button
      type="button"
      onClick={onClick}
      onMouseEnter={() => {
        setIsHovered(true);
        onHover();
      }}
      onMouseLeave={() => {
        setIsHovered(false);
        onLeave();
      }}
      onMouseMove={handleMouseMove}
      whileHover={{ scale: 1.015, y: -8 }}
      whileTap={{ scale: 0.98 }}
      transition={{ 
        scale: { type: "spring", stiffness: 350, damping: 25 },
        y: { type: "spring", stiffness: 350, damping: 25 }
      }}
      style={{
        background: isHovered
          ? `radial-gradient(450px circle at ${coords.x}px ${coords.y}px, ${
              tone === "slate" ? "rgba(15,23,42,0.04)" : "rgba(6,182,212,0.06)"
            }, transparent 80%), rgba(255, 255, 255, 0.82)`
          : "rgba(255, 255, 255, 0.75)",
      }}
      className={`puq-gateway-card group relative flex min-h-[320px] w-full flex-col justify-between overflow-hidden rounded-3xl border border-slate-200/80 p-7 text-left backdrop-blur-md shadow-[0_8px_30px_rgb(0,0,0,0.03)] transition-colors duration-300 hover:border-slate-300/80 hover:shadow-[0_20px_50px_rgba(15,23,42,0.08)] ${
        active ? "ring-2 ring-cyan-400/50 shadow-[0_20px_50px_rgba(6,182,212,0.12)]" : "opacity-95"
      }`}
    >
      {/* Glow border overlay following cursor */}
      {isHovered && (
        <div
          className="pointer-events-none absolute inset-0 rounded-3xl transition-opacity duration-300"
          style={{
            background: `radial-gradient(300px circle at ${coords.x}px ${coords.y}px, ${
              tone === "slate" ? "rgba(15,23,42,0.08)" : "rgba(6,182,212,0.15)"
            }, transparent 80%)`,
            border: "1px solid transparent",
            WebkitMaskImage: "linear-gradient(#fff, #fff) content-box, linear-gradient(#fff, #fff)",
            WebkitMaskComposite: "xor",
            maskComposite: "exclude",
          }}
        />
      )}

      {/* Decorative Grid Lines inside Bento Card */}
      <div className="absolute inset-0 bg-[linear-gradient(to_right,#80808008_1px,transparent_1px),linear-gradient(to_bottom,#80808008_1px,transparent_1px)] bg-[size:16px_16px] [mask-image:radial-gradient(ellipse_60%_50%_at_50%_0%,#000_70%,transparent_100%)] opacity-70 group-hover:opacity-100 transition-opacity duration-500" />

      {/* Pulsing Ambient Orbs */}
      <motion.div 
        animate={isHovered ? { scale: 1.1, x: [0, 5, -5, 0], y: [0, -5, 5, 0] } : { scale: 1 }}
        transition={{ duration: 6, repeat: Infinity, ease: "linear" }}
        className={`pointer-events-none absolute -right-20 -top-14 h-48 w-48 rounded-full bg-gradient-to-br blur-sm opacity-80 ${toneGlowClass}`} 
      />
      <div className="pointer-events-none absolute -left-16 bottom-4 h-24 w-24 rounded-full bg-white/40 blur-md" />
      
      <div className="relative z-10">
        <motion.div 
          whileHover={{ rotate: [0, -5, 5, 0] }}
          transition={{ duration: 0.5 }}
          className={`mb-4 grid h-14 w-14 place-items-center rounded-2xl shadow-lg shadow-slate-200/50 transition-all duration-300 group-hover:shadow-xl ${
            tone === "slate" 
              ? "group-hover:shadow-slate-300/30" 
              : "group-hover:shadow-cyan-200/30"
          } ${iconBoxClass}`}
        >
          {icon}
        </motion.div>
        <h3 className="font-['Plus_Jakarta_Sans',sans-serif] text-[1.6rem] font-bold leading-8 tracking-tight text-[#181c23] group-hover:text-black transition-colors duration-300">{title}</h3>
        <p className="mt-2 max-w-xl text-[0.95rem] leading-6 text-[#414754]/95">{description}</p>
      </div>
      
      <div className={`relative z-10 mt-5 flex items-center gap-2 text-base font-bold ${ctaClass}`}>
        <span>{cta}</span>
        <motion.span 
          animate={isHovered ? { x: 5 } : { x: 0 }}
          transition={{ type: "spring", stiffness: 300, damping: 20 }}
          aria-hidden="true"
        >
          →
        </motion.span>
      </div>
    </motion.button>
  );
});

export default function GatewayPage() {
  const [hoveredCard, setHoveredCard] = useState<AppSection | null>(null);
  const navigate = useNavigate();

  const getFlexClass = (section: AppSection) => {
    if (!hoveredCard) return "flex-1";
    return hoveredCard === section ? "flex-[1.8]" : "flex-1";
  };

  const handleLogout = useCallback(() => {
    navigate("/login");
  }, [navigate]);

  const handleHover = useCallback((section: AppSection | null) => {
    setHoveredCard(section);
  }, []);

  return (
    <div className="relative z-10 flex h-screen flex-col overflow-hidden">
      <header className="sticky top-0 z-20 flex h-16 items-center justify-between border-b border-slate-200/80 bg-white/80 px-6 shadow-[0_1px_2px_rgba(0,0,0,0.05)] backdrop-blur-sm">
        <div className="flex items-center gap-8">
          <h1 className="font-['Plus_Jakarta_Sans',sans-serif] text-[1.35rem] font-bold text-[#0f172a]">Chọn không gian làm việc</h1>
          <div className="hidden items-center rounded-lg bg-[#f1f3fe] px-4 py-2.5 md:flex md:w-64">
            <span className="mr-2 text-slate-400">⌕</span>
            <span className="text-sm text-slate-500">Tìm kiếm không gian...</span>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <div className="text-right">
            <p className="text-sm font-bold text-[#181c23]">Quản trị viên</p>
            <p className="text-xs text-[#717786]">Tài khoản thử nghiệm</p>
          </div>
          <button
            type="button"
            onClick={handleLogout}
            className="rounded-lg border border-slate-300 px-3 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-100"
          >
            Đăng xuất
          </button>
        </div>
      </header>

      <main className="relative flex min-h-0 flex-1 flex-col overflow-hidden px-6 py-5">
        <div className="puq-float-orb pointer-events-none absolute -left-20 -top-20 h-60 w-60 rounded-full bg-cyan-300/25 blur-3xl" />
        <div className="puq-float-orb pointer-events-none absolute -bottom-16 -right-20 h-60 w-60 rounded-full bg-emerald-300/25 blur-3xl" style={{ animationDelay: "600ms" }} />

        <div className="mx-auto max-w-[1280px]">
          <div className="mb-5 text-center">
            <span className="mb-2 inline-flex rounded-full border border-cyan-200 bg-cyan-50 px-3 py-1 text-xs font-semibold text-cyan-800">
              Giao diện mới • Chuyển động v2
            </span>
            <h2 className="font-['Plus_Jakarta_Sans',sans-serif] text-4xl font-extrabold tracking-[-0.02em] text-[#181c23]">
              Cổng không gian
            </h2>
            <p className="mt-2 text-base text-[#414754]">
              Chọn môi trường chuyên dụng của bạn để bắt đầu phiên làm việc năng suất cao.
            </p>
          </div>

          <motion.div 
            layout
            transition={{ type: "spring", stiffness: 260, damping: 20 }}
            className="puq-split flex flex-1 flex-col lg:flex-row gap-6"
          >
            <div className={`flex h-full ${getFlexClass("chatspace")}`}>
              <GatewayCard
                title="Chuyên gia Chatspace"
                description="Thảo luận tự nhiên với tài liệu kỹ thuật. Đào sâu vào các API phức tạp và bài giảng với độ chính xác từ AI."
                cta="Vào không gian"
                tone="slate"
                active={hoveredCard === "chatspace"}
                onClick={() => navigate("/workspace/chatspace")}
                onHover={() => handleHover("chatspace")}
                onLeave={() => handleHover(null)}
                icon={<ChatBubbleIcon />}
              />
            </div>
            <div className={`flex h-full ${getFlexClass("summaryhub")}`}>
              <GatewayCard
                title="Trung tâm tóm tắt"
                description="Chắt lọc nội dung video thành thông tin hữu ích ngay lập tức. Tiết kiệm hàng giờ xem video với bản gỡ băng và tóm tắt tự động."
                cta="Bắt đầu phân tích"
                tone="cyan"
                active={hoveredCard === "summaryhub"}
                onClick={() => navigate("/workspace/summaryhub")}
                onHover={() => handleHover("summaryhub")}
                onLeave={() => handleHover(null)}
                icon={<SummaryIcon />}
              />
            </div>
          </motion.div>
        </div>
      </main>
    </div>
  );
}
