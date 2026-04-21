import React from "react";
import { motion } from "framer-motion";
import { Target, Lightbulb, CheckCircle2, AlertCircle, Calculator } from "lucide-react";
import type { MathData } from "../../types/rag";
import MarkdownRenderer from "./MarkdownRenderer";

interface MathComponentProps {
  data: MathData;
}

export default function MathComponent({ data }: MathComponentProps) {
  return (
    <div className="flex flex-col gap-6 py-2">
      {/* Header / Goal Section */}
      <div className="flex items-center gap-3 border-b border-violet-100 pb-4">
        <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-violet-600 text-white shadow-lg shadow-violet-500/20">
          <Target className="h-5 w-5" />
        </div>
        <div>
          <h4 className="text-[14px] font-bold uppercase tracking-wider text-violet-500">Mục tiêu giải quyết</h4>
          <p className="text-[17px] font-black text-slate-900 leading-tight">
            {data.goal}
          </p>
        </div>
      </div>

      {/* Steps Section */}
      <div className="space-y-4">
        {data.steps && Array.isArray(data.steps) && data.steps.length > 0 ? (
          data.steps.map((step, index) => (
            <motion.div
              key={index}
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: index * 0.1 }}
              className="group relative flex gap-4"
            >
              {/* Connector Line */}
              {index < data.steps.length - 1 && (
                <div className="absolute left-4 top-10 bottom-0 w-0.5 bg-slate-100 group-hover:bg-violet-100 transition-colors" />
              )}

              {/* Step Number Badge */}
              <div className="z-10 flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-white border-2 border-violet-100 text-sm font-black text-violet-600 shadow-sm transition-colors group-hover:border-violet-600 group-hover:bg-violet-600 group-hover:text-white">
                {index + 1}
              </div>

              {/* Step Content Card */}
              <div className="flex-1 rounded-2xl border border-slate-100 bg-slate-50/30 p-4 transition-all duration-300 hover:border-violet-200 hover:bg-white hover:shadow-xl hover:shadow-violet-500/5">
                {step.title && (
                  <h5 className="mb-2 text-[15px] font-extrabold text-slate-800 flex items-center gap-2">
                    <Lightbulb className="h-3.5 w-3.5 text-amber-500" />
                    {step.title}
                  </h5>
                )}
                <div className="math-rendered-content opacity-95">
                  <MarkdownRenderer content={step.content} className="prose-p:my-0 prose-p:text-slate-700 prose-p:text-sm prose-p:leading-relaxed" />
                </div>
              </div>
            </motion.div>
          ))
        ) : (
          <div className="p-4 rounded-xl bg-slate-50 text-slate-500 text-sm italic">
            Đang chuẩn bị các bước giải chi tiết...
          </div>
        )}
      </div>

      {/* Verification Box */}
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ delay: data.steps.length * 0.1 }}
        className={`mt-4 rounded-[2rem] border-2 p-5 ${
          data.verification.status === "success" 
            ? "border-emerald-100 bg-emerald-50/50" 
            : "border-amber-100 bg-amber-50/50"
        }`}
      >
        <div className="flex items-start gap-4">
          <div className={`mt-1 flex h-10 w-10 shrink-0 items-center justify-center rounded-2xl ${
            data.verification.status === "success" ? "bg-emerald-500" : "bg-amber-500"
          } text-white shadow-lg`}>
            {data.verification.status === "success" ? <CheckCircle2 className="h-5 w-5" /> : <AlertCircle className="h-5 w-5" />}
          </div>
          <div className="space-y-1">
            <h4 className={`text-sm font-black uppercase tracking-tight ${
              data.verification.status === "success" ? "text-emerald-800" : "text-amber-800"
            }`}>
              {data.verification.status === "success" ? "Đã kiểm chứng bằng Sympy" : "Kiểm chứng chưa hoàn thiện"}
            </h4>
            <div className="text-[13px] leading-relaxed text-slate-600 font-medium whitespace-pre-wrap">
              <MarkdownRenderer content={data.verification.details} className="prose-p:my-0 prose-p:text-sm" />
            </div>
          </div>
        </div>
      </motion.div>

      {/* Mini CTA */}
      <div className="flex items-center justify-center gap-2 py-2 opacity-50">
        <Calculator className="h-3.5 w-3.5" />
        <span className="text-[11px] font-bold uppercase tracking-widest text-slate-400">Giải toán thông minh bởi Sympy AI</span>
      </div>
    </div>
  );
}
