import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { NavBar } from "../components/Landing/NavBar";
import { ResumeUploader } from "../components/ResumeUploader/ResumeUploader";
import { createInterview } from "../services/interviewApi";
import { ApiError } from "../services/api";

const TARGET_ROLES = ["Software Engineer","AI/ML Engineer","Full Stack Developer","Backend Developer","Frontend Developer","Data Scientist"];
const EXPERIENCE_LEVELS = ["Student","Fresher","Entry Level","1-2 Years","2-5 Years","5+ Years"];

export function InterviewSetupPage() {
  const navigate = useNavigate();
  const [fullName, setFullName] = useState("");
  const [targetRole, setTargetRole] = useState(TARGET_ROLES[0]);
  const [experienceLevel, setExperienceLevel] = useState(EXPERIENCE_LEVELS[0]);
  const [jobDescription, setJobDescription] = useState("");
  const [resumeFile, setResumeFile] = useState<File | null>(null);
  const [interviewLength, setInterviewLength] = useState<"quick" | "standard" | "deep" | "adaptive">("standard");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const isValid = fullName.trim().length > 0 && jobDescription.trim().length > 20 && resumeFile !== null;

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!isValid || !resumeFile) return;
    setSubmitting(true); setError(null);
    try {
      const result = await createInterview({ fullName, targetRole, experienceLevel, jobDescription, resumeFile, interviewLength });
      navigate(`/interview/${result.interview_id}`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong creating your interview. Please try again.");
      setSubmitting(false);
    }
  }

  return (
    <div className="min-h-screen">
      <NavBar minimal />
      <main className="mx-auto max-w-3xl px-5 py-12 sm:px-6 sm:py-16">
        <div className="max-w-xl">
          <p className="eyebrow">Interview setup</p>
          <h1 className="mt-3 text-4xl font-semibold tracking-[-.045em]">Give the interview some context.</h1>
          <p className="mt-4 text-sm leading-6 text-ink-muted dark:text-paper/55">
            Intervue uses your background and the role you're targeting to shape the conversation before it starts.
          </p>
        </div>

        <form onSubmit={handleSubmit} className="mt-12">
          <div className="grid gap-8">
            <div>
              <label className="label-text" htmlFor="fullName">Your name</label>
              <input id="fullName" className="input-field mt-2" placeholder="Your full name" value={fullName} onChange={(e) => setFullName(e.target.value)} required />
            </div>

            <div className="grid gap-5 sm:grid-cols-2">
              <div>
                <label className="label-text" htmlFor="targetRole">Target role</label>
                <select id="targetRole" className="input-field mt-2" value={targetRole} onChange={(e) => setTargetRole(e.target.value)}>
                  {TARGET_ROLES.map((r) => <option key={r}>{r}</option>)}
                </select>
              </div>
              <div>
                <label className="label-text" htmlFor="experienceLevel">Experience level</label>
                <select id="experienceLevel" className="input-field mt-2" value={experienceLevel} onChange={(e) => setExperienceLevel(e.target.value)}>
                  {EXPERIENCE_LEVELS.map((lvl) => <option key={lvl}>{lvl}</option>)}
                </select>
              </div>
            </div>

            <div>
              <div>
                <p className="label-text">Interview length</p>
                <p className="mt-1 text-xs leading-5 text-ink-muted dark:text-paper/45">Choose how much practice you want. Adaptive lets Intervue decide when it has enough evidence to finish.</p>
              </div>
              <div className="mt-3 grid gap-3 sm:grid-cols-2">
                {[
                  ["quick", "Quick", "5 questions", "A focused warm-up."],
                  ["standard", "Standard", "8 questions", "A balanced interview."],
                  ["deep", "Deep Dive", "12 questions", "More room for follow-ups."],
                  ["adaptive", "Adaptive", "6–12 questions", "AI stops when the assessment is complete."],
                ].map(([value, label, count, description]) => (
                  <button
                    key={value}
                    type="button"
                    onClick={() => setInterviewLength(value as typeof interviewLength)}
                    className={`text-left rounded-xl border px-4 py-4 transition ${interviewLength === value ? "border-accent bg-accent/5 ring-1 ring-accent/20" : "border-border-light hover:border-ink/20 dark:border-border-dark dark:hover:border-paper/20"}`}
                    aria-pressed={interviewLength === value}
                  >
                    <div className="flex items-center justify-between gap-3">
                      <span className="text-sm font-semibold">{label}</span>
                      <span className="text-[11px] font-semibold text-accent">{count}</span>
                    </div>
                    <p className="mt-1 text-xs leading-5 text-ink-muted dark:text-paper/45">{description}</p>
                  </button>
                ))}
              </div>
            </div>

            <div>
              <label className="label-text">Resume</label>
              <div className="mt-2"><ResumeUploader file={resumeFile} onChange={setResumeFile} /></div>
            </div>

            <div>
              <div className="flex items-center justify-between">
                <label className="label-text" htmlFor="jobDescription">Job description</label>
                <span className="text-[11px] text-ink-muted dark:text-paper/35">{jobDescription.trim().length} chars</span>
              </div>
              <textarea id="jobDescription" className="input-field mt-2 min-h-[190px] resize-y" placeholder="Paste the full job description here…" value={jobDescription} onChange={(e) => setJobDescription(e.target.value)} required />
            </div>
          </div>

          {error && <div role="alert" className="mt-7 rounded-lg border border-signal-rose/30 bg-signal-rose/5 px-4 py-3 text-sm text-signal-rose">{error}</div>}

          <div className="mt-8 flex items-center justify-between gap-4 border-t border-border-light pt-6 dark:border-border-dark">
            <p className="hidden text-xs text-ink-muted dark:text-paper/40 sm:block">PDF or DOCX resume · max 5MB</p>
            <button type="submit" className="btn-accent w-full py-3 sm:w-auto" disabled={!isValid || submitting}>
              {submitting ? "Preparing interview…" : "Start interview"}
            </button>
          </div>
        </form>
      </main>
    </div>
  );
}
