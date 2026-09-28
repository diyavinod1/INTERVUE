import { apiGet, apiPost, apiPostForm } from "./api";
import type { CreateInterviewResponse } from "../types/candidate";
import type {
  CurrentQuestionResponse,
  InterviewMode,
  InterviewSummary,
  SubmitAnswerResponse,
} from "../types/interview";
import type { FinalReport } from "../types/report";

export interface SetupFormData {
  fullName: string;
  targetRole: string;
  experienceLevel: string;
  jobDescription: string;
  resumeFile: File;
  interviewLength: "quick" | "standard" | "deep" | "adaptive";
}

export async function createInterview(data: SetupFormData): Promise<CreateInterviewResponse> {
  const form = new FormData();
  form.append("full_name", data.fullName);
  form.append("target_role", data.targetRole);
  form.append("experience_level", data.experienceLevel);
  form.append("job_description", data.jobDescription);
  form.append("interview_length", data.interviewLength);
  form.append("resume", data.resumeFile);
  return apiPostForm<CreateInterviewResponse>("/api/interviews", form);
}

export function getInterview(interviewId: string): Promise<InterviewSummary> {
  return apiGet<InterviewSummary>(`/api/interviews/${interviewId}`);
}

export function startInterview(interviewId: string, mode: InterviewMode): Promise<CurrentQuestionResponse> {
  return apiPost<CurrentQuestionResponse>(`/api/interviews/${interviewId}/start`, { mode });
}

export function getCurrentQuestion(interviewId: string): Promise<CurrentQuestionResponse> {
  return apiGet<CurrentQuestionResponse>(`/api/interviews/${interviewId}/current`);
}

export function submitAnswer(
  interviewId: string,
  text: string,
  mode: InterviewMode,
  extra?: { audio_duration_seconds?: number; response_latency_ms?: number }
): Promise<SubmitAnswerResponse> {
  return apiPost<SubmitAnswerResponse>(`/api/interviews/${interviewId}/answer`, {
    text,
    mode,
    ...extra,
  });
}

export function setMode(interviewId: string, mode: InterviewMode): Promise<InterviewSummary> {
  return apiPost<InterviewSummary>(`/api/interviews/${interviewId}/mode`, { mode });
}

export function finishInterview(interviewId: string): Promise<FinalReport> {
  return apiPost<FinalReport>(`/api/interviews/${interviewId}/finish`);
}

export function getReport(interviewId: string): Promise<FinalReport> {
  return apiGet<FinalReport>(`/api/interviews/${interviewId}/report`);
}
