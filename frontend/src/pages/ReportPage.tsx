import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { NavBar } from "../components/Landing/NavBar";
import { ScoreSummary } from "../components/Report/ScoreSummary";
import { InsightList } from "../components/Report/InsightList";
import { QAHistory } from "../components/Report/QAHistory";
import { getReport } from "../services/interviewApi";
import { ApiError } from "../services/api";
import type { FinalReport } from "../types/report";

export function ReportPage() {
  const { interviewId } = useParams<{ interviewId: string }>();
  const [report, setReport] = useState<FinalReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!interviewId) return;
    getReport(interviewId)
      .then(setReport)
      .catch((e) => setError(e instanceof ApiError ? e.message : "Couldn't load the report."))
      .finally(() => setLoading(false));
  }, [interviewId]);

  return (
    <div className="min-h-screen">
      <NavBar minimal />
      <main className="mx-auto max-w-5xl px-5 py-12 sm:px-6 sm:py-16">
        {loading && <div className="text-sm text-ink-muted dark:text-paper/40">Preparing your report…</div>}
        {error && <div role="alert" className="rounded-lg border border-signal-rose/30 bg-signal-rose/5 px-4 py-3 text-sm text-signal-rose">{error}</div>}

        {report && (
          <>
            <header className="max-w-3xl">
              <p className="eyebrow">Interview report</p>
              <h1 className="mt-3 text-4xl font-semibold tracking-[-.045em]">{report.candidate_name} · {report.target_role}</h1>
              <p className="mt-4 text-sm leading-7 text-ink-muted dark:text-paper/55">{report.summary}</p>
            </header>

            <section className="mt-10 grid gap-6 lg:grid-cols-[.9fr_1.1fr]">
              <ScoreSummary overallScore={report.overall_score} topicScores={report.topic_scores} />
              <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-1">
                <InsightList title="Strengths" items={report.strengths} tone="positive" />
                <InsightList title="Areas to improve" items={report.weaknesses} tone="negative" />
              </div>
            </section>

            <section className="mt-6 grid gap-6 sm:grid-cols-2">
              <InsightList title="Technical gaps" items={report.technical_gaps} tone="negative" />
              <InsightList title="Recommended learning areas" items={report.recommended_learning_areas} tone="neutral" />
            </section>

            {report.qa_history.length > 0 && (
              <section className="mt-12">
                <div className="mb-4">
                  <p className="eyebrow">Conversation record</p>
                  <h2 className="mt-2 text-2xl font-semibold tracking-[-.03em]">Question by question</h2>
                </div>
                <QAHistory items={report.qa_history} />
              </section>
            )}

            <div className="mt-10 flex flex-wrap gap-3 border-t border-border-light pt-6 dark:border-border-dark">
              <Link to="/setup" className="btn-accent">Practice again</Link>
              <Link to="/" className="btn-secondary">Back home</Link>
            </div>
          </>
        )}
      </main>
    </div>
  );
}
