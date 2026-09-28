import type { ChatMessage } from "../../types/interview";

function formatTime(iso: string): string {
  try {
    return new Date(iso).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  } catch {
    return "";
  }
}

export function MessageBubble({ message }: { message: ChatMessage }) {
  const isInterviewer = message.role === "interviewer";
  const status = message.status;

  return (
    <article className={`flex animate-fade-in-up ${isInterviewer ? "justify-start" : "justify-end"}`}>
      <div className={`w-full max-w-[720px] ${isInterviewer ? "" : "flex justify-end"}`}>
        <div className={`max-w-[90%] ${isInterviewer ? "pr-4 sm:pr-10" : "pl-8 sm:pl-16"}`}>
          <div className={`mb-2 flex items-center gap-2 ${isInterviewer ? "" : "justify-end"}`}>
            <span className="text-[10px] font-semibold uppercase tracking-[.14em] text-ink-muted dark:text-paper/45">
              {isInterviewer ? "Interviewer" : "You"}
            </span>
            {message.mode === "voice" && <span className="text-[10px] text-ink-muted dark:text-paper/35">voice</span>}
            {status === "sending" && <span className="text-[10px] text-ink-muted dark:text-paper/40">sending…</span>}
            {status === "failed" && <span className="text-[10px] font-medium text-signal-rose">failed to send</span>}
            {status !== "sending" && status !== "failed" && <span className="text-[10px] text-ink-muted/70 dark:text-paper/30">{formatTime(message.created_at)}</span>}
          </div>

          <div
            className={
              isInterviewer
                ? "border-l-2 border-border-light dark:border-border-dark pl-4 text-[15px] leading-7 text-ink/85 dark:text-paper/85"
                : "rounded-2xl border border-border-light bg-white px-4 py-3 text-[15px] leading-7 shadow-sm dark:border-border-dark dark:bg-[#18202A]"
            }
          >
            {message.text}
          </div>
        </div>
      </div>
    </article>
  );
}
