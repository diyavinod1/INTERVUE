import { useCallback, useEffect, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { NavBar } from "../components/Landing/NavBar";
import { MessageList } from "../components/Chat/MessageList";
import { ChatInput } from "../components/Chat/ChatInput";
import { ModeSelectSplash } from "../components/Chat/ModeSelectSplash";
import { ProgressIndicator } from "../components/ProgressIndicator/ProgressIndicator";
import { AudioPlayer } from "../components/AudioPlayer/AudioPlayer";
import { useInterview } from "../hooks/useInterview";
import { useVoice } from "../hooks/useVoice";
import type { InterviewMode } from "../types/interview";

export function InterviewPage() {
  const { interviewId } = useParams<{ interviewId: string }>();
  const navigate = useNavigate();
  return interviewId ? <InterviewPageInner interviewId={interviewId} navigate={navigate} /> : null;
}

function InterviewPageInner({ interviewId, navigate }: {
  interviewId: string;
  navigate: ReturnType<typeof useNavigate>;
}) {
  const {
    loading, error, status, mode, conversation, currentQuestionText, topic,
    questionsAsked, questionLimit, questionStrategy, submitting, failedAnswer, start, submitAnswer,
    retryAnswer, switchMode, refresh,
  } = useInterview(interviewId);
  const voice = useVoice();
  const [starting, setStarting] = useState(false);
  const lastSpokenQuestion = useRef<string | null>(null);

  useEffect(() => {
    if (status === "completed") navigate(`/interview/${interviewId}/report`);
  }, [status, interviewId, navigate]);

  useEffect(() => {
    if (mode === "voice" && currentQuestionText && currentQuestionText !== lastSpokenQuestion.current) {
      lastSpokenQuestion.current = currentQuestionText;
      voice.speak(currentQuestionText);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [mode, currentQuestionText]);

  const handleSelectMode = useCallback(async (selected: InterviewMode) => {
    setStarting(true);
    await start(selected);
    setStarting(false);
  }, [start]);

  const handleSendText = useCallback((text: string) => {
    submitAnswer(text, mode);
  }, [submitAnswer, mode]);

  const handleModeChange = useCallback((newMode: InterviewMode) => {
    switchMode(newMode);
  }, [switchMode]);

  return (
    <div className="flex h-screen flex-col overflow-hidden bg-paper dark:bg-ink">
      <NavBar minimal />

      <div className="border-b border-border-light dark:border-border-dark px-5 py-3 sm:px-6">
        <div className="mx-auto flex max-w-3xl items-center justify-between">
          <ProgressIndicator questionsAsked={questionsAsked} questionLimit={questionLimit || 1} questionStrategy={questionStrategy} topic={topic} />
          <span className="hidden text-[11px] text-ink-muted dark:text-paper/40 sm:block">
            {mode === "voice" ? "Voice interview" : "Text interview"}
          </span>
        </div>
      </div>

      {loading && !status ? (
        <div className="flex flex-1 items-center justify-center text-sm text-ink-muted dark:text-paper/40">Loading your interview…</div>
      ) : error && !status ? (
        <div className="flex flex-1 flex-col items-center justify-center gap-3 px-6 text-center">
          <p className="text-sm text-signal-rose">{error}</p>
          <button className="btn-secondary" onClick={refresh}>Retry</button>
        </div>
      ) : status === "created" ? (
        <ModeSelectSplash onSelect={handleSelectMode} loading={starting} />
      ) : (
        <>
          <MessageList conversation={conversation} isGenerating={submitting} />

          {mode === "voice" && currentQuestionText && (
            <div className="mx-auto w-full max-w-3xl px-5 pb-1 sm:px-6">
              <AudioPlayer
                isSpeaking={voice.voiceState === "speaking" || voice.voiceState === "generating"}
                onReplay={() => voice.speak(currentQuestionText)}
              />
            </div>
          )}

          {(error || failedAnswer) && (
            <div className="mx-auto flex w-full max-w-3xl items-center justify-between gap-4 px-5 pb-3 sm:px-6">
              <p className="text-xs text-signal-rose">{error ?? "Your answer could not be sent."}</p>
              {failedAnswer && (
                <button type="button" className="text-xs font-semibold text-accent hover:text-accent-dark" onClick={retryAnswer}>
                  Retry answer
                </button>
              )}
            </div>
          )}

          <ChatInput
            mode={mode}
            onModeChange={handleModeChange}
            disabled={submitting || status !== "in_progress"}
            onSendText={handleSendText}
            voiceState={voice.voiceState}
            isRecording={voice.isRecording}
            voiceError={voice.errorMessage}
            onStartRecording={voice.startRecording}
            onStopRecording={voice.stopRecording}
          />
        </>
      )}
    </div>
  );
}
