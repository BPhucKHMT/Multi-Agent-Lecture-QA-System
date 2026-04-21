import React, { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { CheckCircle2, XCircle, Info, ExternalLink, RotateCcw } from "lucide-react";
import type { QuizQuestion } from "../../types/rag";

interface QuizComponentProps {
  questions: QuizQuestion[];
}

export default function QuizComponent({ questions }: QuizComponentProps) {
  const [answers, setAnswers] = useState<Record<number, string | null>>({});
  const [showExplanations, setShowExplanations] = useState<Record<number, boolean>>({});

  const handleSelect = (qIndex: number, option: string) => {
    if (answers[qIndex]) return; // Prevent changing answer after selection
    setAnswers({ ...answers, [qIndex]: option });
    setShowExplanations({ ...showExplanations, [qIndex]: true });
  };

  const handleReset = () => {
    setAnswers({});
    setShowExplanations({});
  };

  const score = Object.entries(answers).reduce((acc, [idx, ans]) => {
    if (ans === questions[Number(idx)].correct_answer) return acc + 1;
    return acc;
  }, 0);

  const isCompleted = Object.keys(answers).length === questions.length;

  return (
    <div className="flex flex-col gap-6 py-2">
      <div className="flex items-center justify-between border-b border-violet-100 pb-4">
        <div className="flex items-center gap-2">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-violet-100 text-violet-600">
            <span className="text-sm font-bold">Q</span>
          </div>
          <h3 className="text-[16px] font-bold text-slate-900">Bài kiểm tra kiến thức nhanh</h3>
        </div>
        {Object.keys(answers).length > 0 && (
          <button
            onClick={handleReset}
            className="flex items-center gap-1.5 text-xs font-semibold text-slate-400 transition hover:text-violet-600"
          >
            <RotateCcw className="h-3.5 w-3.5" />
            Làm lại
          </button>
        )}
      </div>

      <div className="space-y-8">
        {questions.map((q, qIndex) => {
          const selectedOption = answers[qIndex];
          const isCorrect = selectedOption === q.correct_answer;
          const showExplanation = showExplanations[qIndex];

          return (
            <div key={qIndex} className="group relative">
              <div className="mb-4 flex items-start gap-3">
                <span className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-violet-100/50 text-[11px] font-bold text-violet-600">
                  {qIndex + 1}
                </span>
                <p className="text-[17px] font-extrabold text-slate-900 leading-snug tracking-tight">{q.question}</p>
              </div>

              <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
                {q.options.map((option, oIndex) => {
                  const isOptionSelected = selectedOption === option;
                  const isOptionCorrect = option === q.correct_answer;
                  
                  let stateStyle = "border-slate-200 bg-white hover:border-violet-200 hover:bg-violet-50/30";
                  if (selectedOption) {
                    if (isOptionCorrect) {
                      stateStyle = "border-emerald-300 bg-emerald-50 text-emerald-900 ring-1 ring-emerald-300";
                    } else if (isOptionSelected) {
                      stateStyle = "border-rose-300 bg-rose-50 text-rose-900 ring-1 ring-rose-300 opacity-95";
                    } else {
                      stateStyle = "border-slate-200 bg-slate-50/50 text-slate-600 opacity-75";
                    }
                  }

                  return (
                    <button
                      key={oIndex}
                      disabled={!!selectedOption}
                      onClick={() => handleSelect(qIndex, option)}
                      className={`relative flex items-center gap-3 rounded-xl border px-3.5 py-3 text-left text-[14.5px] font-medium transition-all duration-200 ${stateStyle} ${
                        !selectedOption ? "active:scale-[0.98]" : ""
                      }`}
                    >
                      <div className={`flex h-5 w-5 shrink-0 items-center justify-center rounded-full border text-[10px] ${
                        isOptionCorrect && selectedOption ? "bg-emerald-500 border-emerald-500 text-white" : 
                        isOptionSelected && !isCorrect ? "bg-rose-500 border-rose-500 text-white" : 
                        "border-slate-200 bg-slate-50"
                      }`}>
                        {selectedOption && isOptionCorrect ? <CheckCircle2 className="h-3.5 w-3.5" /> : 
                         selectedOption && isOptionSelected ? <XCircle className="h-3.5 w-3.5" /> :
                         String.fromCharCode(65 + oIndex)}
                      </div>
                      <span className="flex-1 leading-snug">{option}</span>
                    </button>
                  );
                })}
              </div>

              <AnimatePresence>
                {showExplanation && (
                  <motion.div
                    initial={{ opacity: 0, height: 0 }}
                    animate={{ opacity: 1, height: "auto" }}
                    exit={{ opacity: 0, height: 0 }}
                    className="overflow-hidden"
                  >
                    <div className={`mt-3 rounded-xl border p-3.5 ${isCorrect ? "bg-emerald-50/30 border-emerald-100" : "bg-blue-50/30 border-blue-100"}`}>
                      <div className="flex items-start gap-2.5">
                        <Info className={`mt-0.5 h-3.5 w-3.5 shrink-0 ${isCorrect ? "text-emerald-600" : "text-blue-600"}`} />
                        <div className="space-y-1.5">
                           <p className={`text-[12.5px] font-bold ${isCorrect ? "text-emerald-800" : "text-blue-800"}`}>
                             {isCorrect ? "Chính xác!" : `Chưa đúng. Đáp án là: ${q.correct_answer}`}
                           </p>
                           <p className="text-[13px] leading-relaxed text-slate-600">{q.explanation}</p>
                           
                           {q.video_url && (
                             <a
                               href={q.video_url}
                               target="_blank"
                               rel="noreferrer"
                               className="inline-flex items-center gap-1.5 rounded-lg bg-white/60 px-2.5 py-1 text-[11px] font-bold text-slate-700 shadow-sm transition hover:bg-white hover:text-violet-600"
                             >
                               <ExternalLink className="h-3 w-3 text-violet-500" />
                               {q.video_title ? `${q.video_title} tại ${q.timestamp}` : `Xem bài giảng tại ${q.timestamp}`}
                             </a>
                           )}
                        </div>
                      </div>
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>

              {qIndex < questions.length - 1 && (
                <div className="mt-8 h-px w-full bg-slate-100" />
              )}
            </div>
          );
        })}
      </div>

      <AnimatePresence>
        {isCompleted && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className="mt-2 flex items-center justify-between rounded-xl bg-gradient-to-r from-violet-600 to-indigo-600 p-4 text-white shadow-lg shadow-violet-500/20"
          >
            <div>
              <p className="text-[10px] font-bold uppercase tracking-widest opacity-70">Kết quả tổng quan</p>
              <h4 className="text-base font-black">Chính xác {score}/{questions.length} câu hỏi</h4>
            </div>
            <div className="text-2xl font-black opacity-50">
              {Math.round((score / questions.length) * 100)}%
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
