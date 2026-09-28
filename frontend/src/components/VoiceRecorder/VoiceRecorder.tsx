import type { VoiceUIState } from "../../types/interview";

const STATE_LABELS: Record<VoiceUIState, string> = {
  idle: "Tap to answer",
  listening: "Listening…",
  recording: "Recording… tap to stop",
  processing: "Processing…",
  transcribing: "Transcribing…",
  generating: "Preparing question audio…",
  speaking: "Speaking…",
  error: "Voice unavailable",
};

interface VoiceRecorderProps {
  voiceState: VoiceUIState;
  isRecording: boolean;
  disabled?: boolean;
  onToggle: () => void;
}

export function VoiceRecorder({ voiceState, isRecording, disabled, onToggle }: VoiceRecorderProps) {
  const busy = ["processing", "transcribing", "generating", "speaking"].includes(voiceState);
  return (
    <div className="flex flex-col items-center gap-2">
      <button
        type="button"
        onClick={onToggle}
        disabled={disabled || busy}
        aria-label={isRecording ? "Stop recording" : "Start recording"}
        className={`relative flex h-16 w-16 items-center justify-center rounded-full border transition-all disabled:opacity-40 ${
          isRecording
            ? "border-signal-green bg-signal-green/10 text-signal-green"
            : voiceState === "error"
            ? "border-signal-rose/40 bg-signal-rose/10 text-signal-rose"
            : "border-border-light bg-white text-ink dark:border-border-dark dark:bg-surface-dark dark:text-paper"
        }`}
      >
        {isRecording && <span className="absolute h-20 w-20 animate-recording-pulse rounded-full border border-signal-green" />}
        <span className="relative text-lg" aria-hidden="true">{isRecording ? "■" : "●"}</span>
      </button>
      <p className="text-xs text-ink-muted dark:text-paper/50">{STATE_LABELS[voiceState]}</p>
      {isRecording && <span className="text-[10px] font-medium uppercase tracking-[.12em] text-signal-green">Live</span>}
    </div>
  );
}
