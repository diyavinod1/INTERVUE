function scoreTone(score: number): string {
  if (score >= 7.5) return "bg-signal-green";
  if (score >= 5) return "bg-accent";
  return "bg-signal-rose";
}

export function ScoreSummary({ overallScore, topicScores }: { overallScore: number; topicScores: Record<string, number> }) {
  return (
    <div className="surface rounded-2xl p-6 shadow-card dark:shadow-darkcard">
      <p className="label-text">Overall score</p>
      <div className="mt-3 flex items-end gap-2">
        <span className="text-6xl font-semibold tracking-[-.06em]">{overallScore.toFixed(1)}</span>
        <span className="pb-2 text-sm text-ink-muted dark:text-paper/45">/ 10</span>
      </div>
      <div className="mt-8 border-t border-border-light pt-6 dark:border-border-dark">
        <p className="label-text">By topic</p>
        <div className="mt-5 flex flex-col gap-4">
          {Object.entries(topicScores).map(([topic, score]) => (
            <div key={topic}>
              <div className="mb-1.5 flex items-center justify-between text-xs">
                <span className="font-medium">{topic}</span><span className="text-ink-muted dark:text-paper/45">{score.toFixed(1)}</span>
              </div>
              <div className="h-1 w-full overflow-hidden rounded-full bg-paper-dim dark:bg-ink-soft">
                <div className={`h-full rounded-full ${scoreTone(score)}`} style={{ width: `${Math.min(100, (score / 10) * 100)}%` }} />
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
