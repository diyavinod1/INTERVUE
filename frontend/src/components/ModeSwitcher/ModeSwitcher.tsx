import type { InterviewMode } from "../../types/interview";

interface ModeSwitcherProps {
  mode: InterviewMode;
  onChange: (mode: InterviewMode) => void;
  disabled?: boolean;
}

export function ModeSwitcher({ mode, onChange, disabled }: ModeSwitcherProps) {
  return (
    <div className="inline-flex rounded-lg border border-border-light dark:border-border-dark p-1 text-xs">
      {(["text", "voice"] as const).map((m) => (
        <button
          key={m}
          type="button"
          disabled={disabled}
          onClick={() => onChange(m)}
          className={`rounded-md px-3 py-1.5 font-medium transition-colors disabled:opacity-40 ${
            mode === m
              ? "bg-ink text-paper dark:bg-paper dark:text-ink"
              : "text-ink-muted dark:text-paper/55 hover:text-ink dark:hover:text-paper"
          }`}
        >
          {m === "voice" ? "Voice" : "Text"}
        </button>
      ))}
    </div>
  );
}
