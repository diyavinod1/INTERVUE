import type { InterviewMode } from "../../types/interview";

interface ModeSelectSplashProps {
  candidateName?: string;
  onSelect: (mode: InterviewMode) => void;
  loading: boolean;
}

export function ModeSelectSplash({ onSelect, loading }: ModeSelectSplashProps) {
  return (
    <div className="flex flex-1 flex-col items-center justify-center px-6 text-center">
      <h2 className="font-display text-2xl tracking-tight">How would you like to interview?</h2>
      <p className="mt-2 max-w-sm text-sm text-ink/60 dark:text-paper/60">
        You can switch between text and voice at any point once the interview begins.
      </p>
      <div className="mt-8 flex gap-4">
        <button
          className="btn-secondary flex w-36 flex-col items-center gap-1 py-5"
          disabled={loading}
          onClick={() => onSelect("text")}
        >
          <span className="text-2xl">⌨</span>
          <span className="font-medium">Text</span>
        </button>
        <button
          className="btn-accent flex w-36 flex-col items-center gap-1 py-5"
          disabled={loading}
          onClick={() => onSelect("voice")}
        >
          <span className="text-2xl">🎙</span>
          <span className="font-medium">Voice</span>
        </button>
      </div>
      {loading && <p className="mt-6 text-xs text-ink/40 dark:text-paper/40">Preparing your first question...</p>}
    </div>
  );
}
