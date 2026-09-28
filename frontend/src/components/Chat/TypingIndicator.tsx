export function TypingIndicator() {
  return (
    <div className="flex justify-start animate-fade-in-up">
      <div className="border-l-2 border-border-light dark:border-border-dark pl-4">
        <div className="flex items-center gap-2 text-xs text-ink-muted dark:text-paper/50">
          <span>Interviewer is typing</span>
          <span className="flex gap-1" aria-hidden="true">
            <span className="h-1 w-1 animate-pulse-dot rounded-full bg-ink-muted dark:bg-paper/50 [animation-delay:0ms]" />
            <span className="h-1 w-1 animate-pulse-dot rounded-full bg-ink-muted dark:bg-paper/50 [animation-delay:160ms]" />
            <span className="h-1 w-1 animate-pulse-dot rounded-full bg-ink-muted dark:bg-paper/50 [animation-delay:320ms]" />
          </span>
        </div>
      </div>
    </div>
  );
}
