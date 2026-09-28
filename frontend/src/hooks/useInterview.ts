import { useCallback, useEffect, useState } from "react";
import * as interviewApi from "../services/interviewApi";
import { ApiError } from "../services/api";
import type { ChatMessage, InterviewLength, InterviewMode, InterviewStatus } from "../types/interview";

interface InterviewChatState {
  loading: boolean;
  error: string | null;
  status: InterviewStatus | null;
  mode: InterviewMode;
  conversation: ChatMessage[];
  currentQuestionText: string | null;
  currentQuestionId: string | null;
  topic: string | null;
  difficulty: string | null;
  questionsAsked: number;
  questionLimit: number;
  questionStrategy: InterviewLength;
  submitting: boolean;
  failedAnswer: { text: string; mode: InterviewMode } | null;
}

export function useInterview(interviewId: string) {
  const [state, setState] = useState<InterviewChatState>({
    loading: true, error: null, status: null, mode: "text", conversation: [],
    currentQuestionText: null, currentQuestionId: null, topic: null, difficulty: null,
    questionsAsked: 0, questionLimit: 0, questionStrategy: "standard", submitting: false, failedAnswer: null,
  });

  const refresh = useCallback(async () => {
    setState((s) => ({ ...s, loading: true, error: null }));
    try {
      const current = await interviewApi.getCurrentQuestion(interviewId);
      setState((s) => ({
        ...s, loading: false, status: current.status, mode: current.mode,
        conversation: current.conversation, currentQuestionText: current.question_text,
        currentQuestionId: current.question_id, topic: current.topic, difficulty: current.difficulty,
        questionsAsked: current.questions_asked, questionLimit: current.question_limit, questionStrategy: current.question_strategy, failedAnswer: null,
      }));
    } catch (e) {
      setState((s) => ({ ...s, loading: false, error: describeError(e) }));
    }
  }, [interviewId]);

  useEffect(() => { refresh(); }, [refresh]);

  const start = useCallback(async (mode: InterviewMode) => {
    setState((s) => ({ ...s, loading: true, error: null }));
    try {
      const current = await interviewApi.startInterview(interviewId, mode);
      setState((s) => ({
        ...s, loading: false, status: current.status, mode: current.mode,
        conversation: current.conversation, currentQuestionText: current.question_text,
        currentQuestionId: current.question_id, topic: current.topic, difficulty: current.difficulty,
        questionsAsked: current.questions_asked, questionLimit: current.question_limit,
      }));
    } catch (e) {
      setState((s) => ({ ...s, loading: false, error: describeError(e) }));
    }
  }, [interviewId]);

  const submitAnswer = useCallback(async (
    text: string,
    mode: InterviewMode,
    extra?: { audio_duration_seconds?: number; response_latency_ms?: number },
  ) => {
    const optimistic: ChatMessage = {
      role: "candidate",
      text,
      topic: state.topic,
      difficulty: state.difficulty,
      mode,
      created_at: new Date().toISOString(),
      status: "sending",
    };

    // Render the candidate answer first. The server response is intentionally
    // awaited only after this state update.
    setState((s) => ({
      ...s,
      submitting: true,
      error: null,
      failedAnswer: null,
      conversation: [...s.conversation, optimistic],
    }));

    try {
      const result = await interviewApi.submitAnswer(interviewId, text, mode, extra);
      setState((s) => ({
        ...s,
        submitting: false,
        status: result.status,
        // The API returns the persisted conversation. It is the source of truth
        // and therefore also prevents an optimistic candidate from duplicating.
        conversation: result.conversation.map((m) => ({ ...m, status: "sent" as const })),
        currentQuestionText: result.next_question_text,
        currentQuestionId: result.next_question_id,
        topic: result.topic,
        difficulty: result.difficulty,
        questionsAsked: result.questions_asked,
        questionLimit: result.question_limit,
        questionStrategy: result.question_strategy,
        failedAnswer: null,
      }));
      return true;
    } catch (e) {
      setState((s) => ({
        ...s,
        submitting: false,
        error: describeError(e),
        failedAnswer: { text, mode },
        conversation: s.conversation.map((m) =>
          m === optimistic ? { ...m, status: "failed" as const } : m
        ),
      }));
      return false;
    }
  }, [interviewId, state.topic, state.difficulty]);

  const retryAnswer = useCallback(async () => {
    if (!state.failedAnswer || state.submitting) return false;
    const failedText = state.failedAnswer.text;
    const failedMode = state.failedAnswer.mode;
    setState((s) => ({
      ...s,
      conversation: s.conversation.filter((m) => !(m.role === "candidate" && m.status === "failed" && m.text === failedText)),
    }));
    return submitAnswer(failedText, failedMode);
  }, [state.failedAnswer, state.submitting, submitAnswer]);

  const switchMode = useCallback(async (mode: InterviewMode) => {
    setState((s) => ({ ...s, mode }));
    try {
      await interviewApi.setMode(interviewId, mode);
    } catch (e) {
      setState((s) => ({ ...s, error: describeError(e) }));
    }
  }, [interviewId]);

  const finish = useCallback(async () => {
    setState((s) => ({ ...s, submitting: true }));
    try {
      await interviewApi.finishInterview(interviewId);
      setState((s) => ({ ...s, submitting: false, status: "completed" }));
      return true;
    } catch (e) {
      setState((s) => ({ ...s, submitting: false, error: describeError(e) }));
      return false;
    }
  }, [interviewId]);

  return { ...state, start, submitAnswer, retryAnswer, switchMode, finish, refresh };
}

function describeError(e: unknown): string {
  if (e instanceof ApiError) return e.message;
  if (e instanceof Error) return e.message;
  return "Something went wrong. Please try again.";
}
