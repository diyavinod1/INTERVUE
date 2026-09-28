import { useState } from "react";
import type { QuestionAnswerSummary } from "../../types/report";

export function QAHistory({ items }: { items: QuestionAnswerSummary[] }) {
  const [openIndex, setOpenIndex] = useState<number | null>(null);

  return (
    <div className="surface divide-y divide-border-light dark:divide-border-dark rounded-xl">
      {items.map((item, i) => {
        const isOpen = openIndex === i;
        return (
          <div key={i}>
            <button
              className="flex w-full items-center justify-between gap-4 px-6 py-4 text-left"
              onClick={() => setOpenIndex(isOpen ? null : i)}
            >
              <div>
                <p className="text-xs font-medium uppercase tracking-wide text-ink/40 dark:text-paper/40">
                  {item.topic} · {item.difficulty}
                </p>
                <p className="mt-1 text-sm font-medium">{item.question}</p>
              </div>
              <span className="flex-shrink-0 text-sm font-medium text-ink/50 dark:text-paper/50">
                {item.score.toFixed(1)}
              </span>
            </button>
            {isOpen && (
              <div className="px-6 pb-5 text-sm leading-relaxed text-ink/70 dark:text-paper/70">
                <p className="mb-2">
                  <span className="font-medium text-ink/50 dark:text-paper/50">Your answer: </span>
                  {item.answer}
                </p>
                {item.feedback && (
                  <p className="text-ink/50 dark:text-paper/50">
                    <span className="font-medium">Note: </span>
                    {item.feedback}
                  </p>
                )}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
