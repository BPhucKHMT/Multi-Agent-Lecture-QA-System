export type RagConfidence = "high" | "medium" | "low" | "zero";

export type RagResponseType = "rag" | "direct" | "quiz" | "math" | "error";

export interface QuizQuestion {
  question: string;
  options: string[];
  correct_answer: string;
  explanation: string;
  video_url: string;
  video_title?: string;
  timestamp: string;
}

export interface MathStep {
  title: string;
  content: string;
}

export interface MathData {
  goal: string;
  steps: MathStep[];
  verification: {
    status: "success" | "warning" | "error";
    details: string;
  };
}

export type RagResponse = {
  text: string;
  video_url: string[];
  title: string[];
  filename: string[];
  start_timestamp: string[];
  end_timestamp: string[];
  confidence: RagConfidence[];
  type: RagResponseType;
  quizzes?: QuizQuestion[];
  math_data?: MathData;
};
