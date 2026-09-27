import React, { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { CheckCircle2, XCircle, Info, ExternalLink, RotateCcw } from "lucide-react";
import type { QuizQuestion } from "../../types/rag";

interface QuizComponentProps {
  questions: QuizQuestion[];
}

export default function QuizComponent({ questions }: QuizComponentProps) {
  const [answers, setAnswers] = useState<Record<number, string>>({});
  const [revealedAnswers, setRevealedAnswers] = useState<Record<number, boolean>>({});

  const handleSelect = (qIndex: number, option: string) => {
    if (answers[qIndex]) return;
    setAnswers({ ...answers, [qIndex]: option });
  };

  const handleShortAnswerChange = (qIndex: number, value: string) => {
    setAnswers({ ...answers, [qIndex]: value });
  };

  const handleRevealAnswer = (qIndex: number) => {
    setRevealedAnswers({ ...revealedAnswers, [qIndex]: true });
  };

  const handleReset = () => {
    setAnswers({});
    setRevealedAnswers({});
  };

  const gradableQuestions = questions.filter(
    (question) => question.question_type !== "short_answer" && Boolean(question.correct_answer),
  );
  const score = questions.reduce((total, question, questionIndex) => (
    total + (
      question.question_type !== "short_answer"
      && question.correct_answer
      && answers[questionIndex] === question.correct_answer
        ? 1
        : 0
    )
  ), 0);
  const isCompleted = questions.length > 0 && questions.every((question, index) => (
    question.question_type === "short_answer"
      ? Boolean(revealedAnswers[index])
      : Boolean(answers[index])
  ));

  return (
    <div className="flex flex-col gap-6 py-2">
      <div className="flex items-center justify-between border-b border-slate-200/60 pb-4">
        <div className="flex items-center gap-2">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-teal-50 border border-teal-100 text-teal-600">
            <span className="text-sm font-bold">Q</span>
          </div>
          <h3 className="text-[16px] font-bold text-slate-900">Bài kiểm tra kiến thức nhanh</h3>
        </div>
        {Object.keys(answers).length > 0 && (
          <button
            onClick={handleReset}
            className="flex items-center gap-1.5 text-xs font-semibold text-slate-400 transition hover:text-teal-600"
          >
            <RotateCcw className="h-3.5 w-3.5" />
            Làm lại
          </button>
        )}
      </div>

      <div className="space-y-8">
        {questions.map((q, qIndex) => {
          const questionType = q.question_type ?? "multiple_choice";
          const hasAnswer = Boolean(q.correct_answer);
          const selectedAnswer = answers[qIndex];
          const isCorrect = hasAnswer && selectedAnswer === q.correct_answer;
          const isRevealed = questionType === "short_answer"
            ? Boolean(revealedAnswers[qIndex])
            : Boolean(selectedAnswer);

          return (
            <div key={qIndex} className="group relative">
              <div className="mb-4 flex items-start gap-3">
                <span className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-slate-100 text-[11px] font-bold text-slate-600">
                  {qIndex + 1}
                </span>
                <p className="text-[17px] font-extrabold text-slate-900 leading-snug tracking-tight">{q.question}</p>
              </div>

              {questionType === "short_answer" ? (
                <div className="space-y-3">
                  <textarea
                    aria-label={`Câu trả lời cho câu ${qIndex + 1}`}
                    value={selectedAnswer ?? ""}
                    onChange={(event) => handleShortAnswerChange(qIndex, event.target.value)}
                    rows={3}
                    className="w-full resize-y rounded-xl border border-slate-200 bg-white px-3.5 py-3 text-sm leading-relaxed text-slate-800 outline-none transition focus:border-teal-400 focus:ring-2 focus:ring-teal-100"
                    placeholder="Nhập câu trả lời của bạn..."
                  />
                  {!revealedAnswers[qIndex] && (
                    <button
                      type="button"
                      disabled={!selectedAnswer?.trim()}
                      onClick={() => handleRevealAnswer(qIndex)}
                      className="min-h-10 rounded-lg bg-teal-700 px-4 py-2 text-sm font-semibold text-white transition hover:bg-teal-800 disabled:cursor-not-allowed disabled:opacity-50"
                    >
                      {q.correct_answer ? "Xem đáp án tham khảo" : "Ghi nhận câu trả lời"}
                    </button>
                  )}
                </div>
              ) : (
                <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
                  {(q.options ?? []).map((option, oIndex) => {
                    const isOptionSelected = selectedAnswer === option;
                    const isOptionCorrect = hasAnswer && option === q.correct_answer;
                    let stateStyle = "border-slate-200 bg-white hover:border-teal-300 hover:bg-teal-50/30";
                    if (selectedAnswer) {
                      if (isOptionCorrect) {
                        stateStyle = "border-emerald-300 bg-emerald-50 text-emerald-900 ring-1 ring-emerald-300";
                      } else if (isOptionSelected && hasAnswer) {
                        stateStyle = "border-rose-300 bg-rose-50 text-rose-900 ring-1 ring-rose-300";
                      } else if (isOptionSelected) {
                        stateStyle = "border-blue-300 bg-blue-50 text-blue-900 ring-1 ring-blue-300";
                      } else {
                        stateStyle = "border-slate-200 bg-slate-50/50 text-slate-600 opacity-75";
                      }
                    }

                    return (
                      <button
                        key={oIndex}
                        type="button"
                        disabled={Boolean(selectedAnswer)}
                        onClick={() => handleSelect(qIndex, option)}
                        className={`relative flex min-h-11 items-center gap-3 rounded-xl border px-3.5 py-3 text-left text-[14.5px] font-medium transition-all duration-200 ${stateStyle} ${
                          !selectedAnswer ? "active:scale-[0.98]" : ""
                        }`}
                      >
                        <div className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full border border-slate-200 bg-slate-50 text-[10px]">
                          {hasAnswer && selectedAnswer && isOptionCorrect ? <CheckCircle2 className="h-3.5 w-3.5" /> :
                           hasAnswer && selectedAnswer && isOptionSelected ? <XCircle className="h-3.5 w-3.5" /> :
                           String.fromCharCode(65 + oIndex)}
                        </div>
                        <span className="flex-1 leading-snug">{option}</span>
                      </button>
                    );
                  })}
                </div>
              )}

              <AnimatePresence>
                {isRevealed && (
                  <motion.div
                    initial={{ opacity: 0, height: 0 }}
                    animate={{ opacity: 1, height: "auto" }}
                    exit={{ opacity: 0, height: 0 }}
                    className="overflow-hidden"
                  >
                    <div className={`mt-3 rounded-xl border p-3.5 ${
                      hasAnswer && questionType !== "short_answer"
                        ? isCorrect ? "border-emerald-100 bg-emerald-50/30" : "border-blue-100 bg-blue-50/30"
                        : "border-blue-100 bg-blue-50/30"
                    }`}>
                      <div className="flex items-start gap-2.5">
                        <Info className="mt-0.5 h-3.5 w-3.5 shrink-0 text-blue-600" />
                        <div className="space-y-1.5">
                          {questionType === "short_answer" ? (
                            <>
                              <p className="text-[12.5px] font-bold text-blue-800">
                                Đã ghi nhận câu trả lời; không tự chấm câu trả lời ngắn.
                              </p>
                              {q.correct_answer && (
                                <p className="text-[13px] leading-relaxed text-slate-700">
                                  Đáp án tham khảo: {q.correct_answer}
                                </p>
                              )}
                            </>
                          ) : (
                            <p className={`text-[12.5px] font-bold ${
                              hasAnswer && isCorrect ? "text-emerald-800" : "text-blue-800"
                            }`}>
                              {hasAnswer
                                ? isCorrect ? "Chính xác!" : `Chưa đúng. Đáp án là: ${q.correct_answer}`
                                : "Đã ghi nhận lựa chọn."}
                            </p>
                          )}
                          {q.explanation && (
                            <p className="text-[13px] leading-relaxed text-slate-600">{q.explanation}</p>
                          )}
                          {q.video_url && (
                            <a
                              href={q.video_url}
                              target="_blank"
                              rel="noreferrer"
                              className="inline-flex min-h-10 items-center gap-1.5 rounded-lg bg-white/60 px-2.5 py-1 text-[11px] font-bold text-slate-700 shadow-sm transition hover:bg-white hover:text-teal-600"
                            >
                              <ExternalLink className="h-3 w-3 text-teal-600" />
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
            className="mt-2 flex items-center justify-between rounded-xl border border-slate-950 bg-slate-900 p-5 text-white shadow-md shadow-slate-900/10"
          >
            <div>
              <p className="text-[10px] font-bold uppercase tracking-widest opacity-70">Kết quả tổng quan</p>
              <h4 className="text-base font-black">
                {gradableQuestions.length
                  ? `Chính xác ${score}/${gradableQuestions.length} câu trắc nghiệm`
                  : "Đã hoàn thành bộ câu hỏi"}
              </h4>
            </div>
            {gradableQuestions.length > 0 && (
              <div className="text-2xl font-black opacity-70">
                {Math.round((score / gradableQuestions.length) * 100)}%
              </div>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
