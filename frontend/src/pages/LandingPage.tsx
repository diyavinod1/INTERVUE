import { Link } from "react-router-dom";
import { NavBar } from "../components/Landing/NavBar";

const EXCHANGE = [
  { role: "interviewer" as const, text: "You mentioned building a MERN e-commerce app. How did you structure the authentication flow?" },
  { role: "candidate" as const, text: "I used JWT for authentication." },
  { role: "interviewer" as const, text: "Why JWT for that project, and how did your backend verify the token?" },
];

const STEPS = [
  ["01", "Give it the context", "Your name, target role, experience, resume, and the job description."],
  ["02", "Let it prepare", "Intervue reads your background and role context before the first question."],
  ["03", "Answer naturally", "Type or speak. Switch modes mid-interview without losing your place."],
  ["04", "Review what happened", "Get topic scores, strengths, gaps, and a question-by-question record."],
];

export function LandingPage() {
  return (
    <div className="min-h-screen">
      <NavBar />

      <main>
        <section className="mx-auto grid max-w-6xl gap-14 px-5 pb-24 pt-16 sm:px-6 sm:pt-24 lg:grid-cols-[1fr_.85fr] lg:items-center lg:gap-20">
          <div>
            <p className="eyebrow">Adaptive mock interviews</p>
            <h1 className="mt-5 max-w-3xl text-[2.9rem] font-semibold leading-[1.02] tracking-[-.055em] sm:text-6xl lg:text-[4.65rem]">
              Turn every answer into your next question.
            </h1>
            <p className="mt-7 max-w-xl text-base leading-7 text-ink-muted dark:text-paper/60 sm:text-lg">
              A serious practice environment that reads your resume, understands the role, and adapts the conversation to what you actually say.
            </p>
            <div className="mt-9 flex flex-wrap items-center gap-4">
              <Link to="/setup" className="btn-accent px-6 py-3">Set up an interview</Link>
              <a href="#how-it-works" className="quiet-link">See how it works ↓</a>
            </div>
            <div className="mt-10 flex flex-wrap gap-x-6 gap-y-2 text-xs text-ink-muted dark:text-paper/40">
              <span>Resume-grounded</span><span>Text + voice</span><span>Adaptive follow-ups</span>
            </div>
          </div>

          <div className="surface rounded-2xl p-5 shadow-card dark:shadow-darkcard sm:p-6">
            <div className="flex items-center justify-between border-b border-border-light pb-4 dark:border-border-dark">
              <div>
                <p className="label-text">Interview preview</p>
                <p className="mt-1 text-sm font-medium">Backend engineering</p>
              </div>
              <span className="flex items-center gap-2 text-[10px] font-semibold uppercase tracking-[.12em] text-signal-green">
                <span className="h-1.5 w-1.5 rounded-full bg-signal-green" /> Live
              </span>
            </div>
            <div className="flex flex-col gap-7 py-6">
              {EXCHANGE.map((m, i) => (
                <div key={i} className={m.role === "candidate" ? "flex justify-end" : ""}>
                  <div className={m.role === "candidate" ? "max-w-[86%] rounded-2xl border border-border-light bg-paper px-4 py-3 text-sm leading-6 dark:border-border-dark dark:bg-[#18202A]" : "max-w-[92%] border-l-2 border-border-light pl-4 text-sm leading-6 dark:border-border-dark"}>
                    <p className="mb-1.5 text-[10px] font-semibold uppercase tracking-[.14em] text-ink-muted dark:text-paper/40">{m.role === "candidate" ? "You" : "Interviewer"}</p>
                    {m.text}
                  </div>
                </div>
              ))}
              <div className="border-l-2 border-border-light pl-4 dark:border-border-dark">
                <p className="text-xs text-ink-muted dark:text-paper/45">Interviewer is typing <span className="tracking-[.2em]">•••</span></p>
              </div>
            </div>
          </div>
        </section>

        <section id="how-it-works" className="border-y border-border-light dark:border-border-dark">
          <div className="mx-auto max-w-6xl px-5 py-20 sm:px-6">
            <div className="max-w-xl">
              <p className="eyebrow">A focused workflow</p>
              <h2 className="mt-3 text-3xl font-semibold tracking-[-.04em]">Practice the interview, not the interface.</h2>
            </div>
            <div className="mt-12 grid gap-8 sm:grid-cols-2 lg:grid-cols-4">
              {STEPS.map(([n, title, body]) => (
                <div key={n} className="border-t border-border-light pt-5 dark:border-border-dark">
                  <p className="text-xs font-semibold text-accent">{n}</p>
                  <h3 className="mt-4 font-medium">{title}</h3>
                  <p className="mt-2 text-sm leading-6 text-ink-muted dark:text-paper/55">{body}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        <section id="experience" className="mx-auto max-w-6xl px-5 py-20 sm:px-6">
          <div className="grid gap-10 lg:grid-cols-[.8fr_1.2fr]">
            <div>
              <p className="eyebrow">The experience</p>
              <h2 className="mt-3 text-3xl font-semibold tracking-[-.04em]">Calm enough to think. Structured enough to improve.</h2>
            </div>
            <div className="grid gap-5 sm:grid-cols-2">
              {[
                ["Your resume matters", "Questions can reference the projects, internships, and skills in your uploaded resume."],
                ["The role matters", "The job description gives the interview a concrete target instead of generic questions."],
                ["The conversation adapts", "Follow-ups respond to the answer you just gave rather than following a fixed script."],
                ["Voice stays human", "Speak an answer, review the transcript, and continue without changing the interview state."],
              ].map(([title, body]) => (
                <div key={title} className="rounded-xl border border-border-light p-6 dark:border-border-dark">
                  <h3 className="font-medium">{title}</h3>
                  <p className="mt-2 text-sm leading-6 text-ink-muted dark:text-paper/55">{body}</p>
                </div>
              ))}
            </div>
          </div>
        </section>
      </main>

      <footer className="border-t border-border-light dark:border-border-dark">
        <div className="mx-auto flex max-w-6xl flex-col gap-2 px-5 py-9 text-sm text-ink-muted dark:text-paper/40 sm:flex-row sm:items-center sm:justify-between sm:px-6">
          <span className="flex items-center gap-2 font-semibold text-ink dark:text-paper"><img src="/favicon.svg" alt="" aria-hidden="true" className="h-6 w-6 rounded-md" />INTERVUE</span>
          <span>Turn every answer into your next question.</span>
        </div>
      </footer>
    </div>
  );
}
