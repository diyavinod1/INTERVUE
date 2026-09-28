interface ProgressIndicatorProps {
  questionsAsked: number;
  questionLimit: number;
  topic: string | null;
  questionStrategy?: "quick" | "standard" | "deep" | "adaptive";
}

export function ProgressIndicator({ questionsAsked, questionLimit, topic, questionStrategy = "standard" }: ProgressIndicatorProps) {
  const current = Math.min(Math.max(questionsAsked, 1), questionLimit);
  const target = questionStrategy === "adaptive" ? `up to ${questionLimit}` : String(questionLimit).padStart(2, "0");
  return (
    <div className="flex items-center justify-between gap-4">
      <div>
        <p className="label-text">Interview</p>
        <p className="mt-1 text-sm font-medium">{String(current).padStart(2, "0")} / {target}</p>
      </div>
      {topic && <p className="text-xs text-ink-muted dark:text-paper/50">{topic}</p>}
    </div>
  );
}
