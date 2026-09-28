interface AudioPlayerProps {
  isSpeaking: boolean;
  disabled?: boolean;
  onReplay: () => void;
}

export function AudioPlayer({ isSpeaking, disabled, onReplay }: AudioPlayerProps) {
  return (
    <button
      type="button"
      onClick={onReplay}
      disabled={disabled}
      className="inline-flex items-center gap-1.5 text-xs text-ink/50 dark:text-paper/50 hover:text-accent transition-colors disabled:opacity-40"
    >
      <span>{isSpeaking ? "🔊" : "🔈"}</span>
      {isSpeaking ? "Playing question..." : "Replay question"}
    </button>
  );
}
