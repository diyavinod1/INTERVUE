export type InterviewMode = "text" | "voice";
export type InterviewLength = "quick" | "standard" | "deep" | "adaptive";
export type InterviewStatus = "created" | "in_progress" | "completed";

export interface ChatMessage {
  role: "interviewer" | "candidate";
  text: string;
  topic: string | null;
  difficulty: string | null;
  mode: string | null;
  created_at: string;
  status?: "sending" | "sent" | "failed";
}

export interface CurrentQuestionResponse {
  interview_id: string;
  status: InterviewStatus;
  question_id: string | null;
  question_text: string | null;
  topic: string | null;
  difficulty: string | null;
  questions_asked: number;
  question_limit: number;
  question_strategy: InterviewLength;
  mode: InterviewMode;
  conversation: ChatMessage[];
}

export interface SubmitAnswerResponse {
  interview_id: string;
  status: InterviewStatus;
  next_question_id: string | null;
  next_question_text: string | null;
  topic: string | null;
  difficulty: string | null;
  action_taken: string;
  questions_asked: number;
  question_limit: number;
  question_strategy: InterviewLength;
  conversation: ChatMessage[];
}

export interface InterviewSummary {
  id: string;
  status: InterviewStatus;
  mode: InterviewMode;
  candidate_name: string;
  target_role: string;
  questions_asked: number;
  question_limit: number;
  question_strategy: InterviewLength;
  current_topic: string;
  overall_score: number;
}

// Client-side voice pipeline state (PRD Sec. 35) - purely UI state, never
// sent to the backend.
export type VoiceUIState =
  | "idle"
  | "listening"
  | "recording"
  | "processing"
  | "transcribing"
  | "generating"
  | "speaking"
  | "error";
