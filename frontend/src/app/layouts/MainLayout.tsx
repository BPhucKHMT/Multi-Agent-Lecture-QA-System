import React from "react";
import { useOutlet, useLocation } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";

export default function MainLayout() {
  const location = useLocation();
  const outlet = useOutlet();

  return (
    <div className="puq-ambient relative h-screen w-full overflow-hidden" style={{ scrollbarGutter: "stable" }}>
      {/* Global Background Orbs */}
      <div className="pointer-events-none fixed inset-0 z-0 overflow-hidden">
        <div className="puq-float-orb absolute -left-20 -top-20 h-96 w-96 rounded-full bg-violet-400/10 blur-[100px]" />
        <div className="puq-float-orb absolute -bottom-16 -right-20 h-96 w-96 rounded-full bg-cyan-400/10 blur-[100px]" style={{ animationDelay: "1s" }} />
      </div>

      <AnimatePresence mode="wait" initial={false}>
        <motion.div
          key={location.pathname.split("/")[1] || "/"}
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -10 }}
          transition={{ duration: 0.4, ease: [0.22, 1, 0.36, 1] }}
          className="relative z-10 w-full h-full"
        >
          {outlet}
        </motion.div>
      </AnimatePresence>
    </div>
  );
}
