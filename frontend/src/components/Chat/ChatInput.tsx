import { useRef, useState } from "react";
import { ModeSwitcher } from "../ModeSwitcher/ModeSwitcher";
import { VoiceRecorder } from "../VoiceRecorder/VoiceRecorder";
import type { InterviewMode, VoiceUIState } from "../../types/interview";

interface ChatInputProps {
  mode: InterviewMode;
  onModeChange: (mode: InterviewMode) => void;
  disabled: boolean;
  onSendText: (text: string) => void;
  voiceState: VoiceUIState;
  isRecording: boolean;
  voiceError: string | null;
  onStartRecording: () => void;
  onStopRecording: () => Promise<string | null>;
}

export function ChatInput({
  mode, onModeChange, disabled, onSendText, voiceState, isRecording, voiceError,
  onStartRecording, onStopRecording,
}: ChatInputProps) {
  const [textValue, setTextValue] = useState("");
  const [voiceDraft, setVoiceDraft] = useState("");
  const sendLockRef = useRef(false);

  function handleSendText() {
    const trimmed = textValue.trim();
    if (!trimmed || disabled || sendLockRef.current) return;
    sendLockRef.current = true;
    onSendText(trimmed);
    setTextValue("");
    window.setTimeout(() => { sendLockRef.current = false; }, 250);
  }

  async function handleToggleRecording() {
    if (isRecording) {
      const transcript = await onStopRecording();
      if (transcript) setVoiceDraft(transcript);
    } else {
      setVoiceDraft("");
      onStartRecording();
    }
  }

  function handleSendVoiceDraft() {
    const trimmed = voiceDraft.trim();
    if (!trimmed || disabled || sendLockRef.current) return;
    sendLockRef.current = true;
    onSendText(trimmed);
    setVoiceDraft("");
    window.setTimeout(() => { sendLockRef.current = false; }, 250);
  }

  return (
    <div className="border-t border-border-light dark:border-border-dark bg-paper/95 dark:bg-ink/95 px-5 py-4 backdrop-blur-md sm:px-6">
      <div className="mx-auto flex max-w-3xl flex-col gap-3">
        <div className="flex items-center justify-between gap-3">
          <ModeSwitcher mode={mode} onChange={onModeChange} disabled={disabled || isRecording} />
          <p className="hidden text-[11px] text-ink-muted dark:text-paper/40 sm:block">
            {mode === "text" ? "Enter to send · Shift + Enter for a new line" : "Voice answer"}
          </p>
          {voiceError && <p className="text-right text-xs text-signal-rose">{voiceError}</p>}
        </div>

        {mode === "text" ? (
          <div className="flex items-end gap-2">
            <textarea
              aria-label="Your interview answer"
              className="input-field min-h-[52px] max-h-40 flex-1 resize-none bg-white/70 dark:bg-surface-dark"
              placeholder="Write your answer…"
              value={textValue}
              disabled={disabled}
              onChange={(e) => setTextValue(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); handleSendText(); }
              }}
            />
            <button type="button" aria-label="Send answer" className="btn-accent h-[52px] px-5" disabled={disabled || !textValue.trim()} onClick={handleSendText}>
              Send
            </button>
          </div>
        ) : (
          <div className="flex flex-col items-center gap-4 py-1">
            <VoiceRecorder voiceState={voiceState} isRecording={isRecording} disabled={disabled} onToggle={handleToggleRecording} />
            {voiceDraft && (
              <div className="w-full">
                <label className="label-text" htmlFor="voice-transcript">Transcript</label>
                <textarea id="voice-transcript" className="input-field mt-1.5 min-h-[70px] resize-y" value={voiceDraft} onChange={(e) => setVoiceDraft(e.target.value)} />
                <div className="mt-2 flex justify-end gap-2">
                  <button type="button" className="btn-secondary px-4 py-2 text-sm" onClick={() => { setVoiceDraft(""); onModeChange("text"); }}>Switch to text</button>
                  <button type="button" className="btn-accent px-4 py-2 text-sm" disabled={disabled || !voiceDraft.trim()} onClick={handleSendVoiceDraft}>Send answer</button>
                </div>
              </div>
            )}
            {voiceState === "error" && !voiceDraft && (
              <button type="button" className="text-xs text-accent underline" onClick={() => onModeChange("text")}>Switch to text mode</button>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
