export interface QuestionAnswerSummary {
  topic: string;
  difficulty: string;
  question: string;
  answer: string;
  score: number;
  feedback: string;
}

export interface FinalReport {
  interview_id: string;
  candidate_name: string;
  target_role: string;
  overall_score: number;
  topic_scores: Record<string, number>;
  strengths: string[];
  weaknesses: string[];
  technical_gaps: string[];
  recommended_learning_areas: string[];
  question_count: number;
  summary: string;
  qa_history: QuestionAnswerSummary[];
}
