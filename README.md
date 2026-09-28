# Intervue

**Turn every answer into your next question.**

Intervue is an adaptive, conversational, voice-enabled AI interview platform. It reads a
candidate's resume and a target job description, plans an interview around the overlap and the
gaps, and then asks questions that are shaped by what the candidate *just said* - not a fixed
script.

This README covers the architecture, how to run it locally, how to configure the three external
services it depends on (OpenRouter, Sarvam AI, Supabase), how to test and debug it, and how to
deploy it.

---

## 1. Architecture overview

```
API (FastAPI)
   |
   v
Service layer (InterviewService, ResumeService, JDService, LLMService, VoiceService)
   |
   v
Agent / Orchestration layer (LangGraph StateGraph)
   |
   v
Provider layer (OpenRouterProvider, SarvamSTT/TTSProvider, fallback providers)
   |
   v
Database (SQLAlchemy -> PostgreSQL / Supabase, or SQLite for local dev)
```

Nothing skips a layer: routes never touch the database directly, and the LangGraph nodes never
import SQLAlchemy - they only ever read and write the `InterviewState` TypedDict
(`backend/app/agents/state.py`). That separation is what makes the orchestration logic testable
without a database (see `backend/tests/test_decision.py`) and makes swapping a provider (a
different LLM, a different voice vendor) a change contained to one file.

### Why each technology is here

| Technology | Why |
|---|---|
| **FastAPI** | Async-native, Pydantic-validated request/response models, automatic OpenAPI docs, dependency injection for the DB session. |
| **Pydantic** | Every structured object that crosses a boundary (candidate profile, job profile, evaluation rubric, interview plan) is a validated model, not a loose dict - a malformed LLM response gets caught and coerced/rejected instead of silently corrupting state. |
| **SQLAlchemy** | Real relational schema (candidates -> interviews -> questions -> answers -> evaluations -> final_reports) with foreign keys and typed columns, portable between SQLite (local dev) and PostgreSQL (Supabase, production) via one `DATABASE_URL`. |
| **LangChain** | `ChatPromptTemplate` gives every prompt (planner, question generator, evaluator, final report) a single, reusable, readable definition (`backend/app/agents/prompts/`) instead of ad-hoc string concatenation. |
| **LangGraph** | The actual orchestration engine. A `StateGraph` with real conditional edges decides FOLLOW_UP vs INCREASE_DIFFICULTY vs CHANGE_TOPIC vs FINISH_INTERVIEW based on state - see `backend/app/agents/graph.py` and `backend/app/agents/nodes/decision.py`. |
| **OpenRouter** | One HTTP-compatible endpoint in front of many models, so the model is a config value (`OPENROUTER_MODEL`), not a hard-coded dependency - with an automatic, configurable fallback model. |
| **Sarvam AI** | Primary speech-to-text/text-to-speech provider, behind a provider-agnostic interface (`SpeechToTextService`/`TextToSpeechService`) so it can be swapped or supplemented without touching business logic. |
| **Supabase** | Supabase *is* PostgreSQL - `DATABASE_URL` points straight at it, so the app gets real relational storage rather than treating Supabase as a generic REST/JSON store. |
| **React + TypeScript** | Typed components/hooks/services mirroring the backend's Pydantic schemas field-for-field, so a backend response shape change is caught at compile time on the frontend. |

### Why NOT certain things (PRD "no buzzword engineering")

No vector database, no RAG, no multi-agent framework, no microservices. Resume and job
description parsing (`resume_service.py`, `jd_service.py`) are **deterministic, heuristic text
processing** - not an LLM call - specifically so the system can never invent a skill, project, or
requirement that isn't actually present in the source text. The LLM is reserved for the three
things that genuinely need semantic reasoning: phrasing an adaptive question, scoring an answer
against a rubric, and writing a narrative report summary. Deciding *what to do next* (harder,
easier, follow up, change topic, finish) is deterministic Python (`agents/nodes/decision.py`), not
another LLM call - this is also what makes the adaptive behavior unit-testable and reproducible.

---

## 2. User flow

```
Landing Page
   -> "Set up interview"
Interview Setup (name, target role, experience level, resume upload, job description)
   -> POST /api/interviews (creates Candidate + Interview, parses resume + JD)
Interview Page
   -> "How would you like to interview?" (Text / Voice)
   -> POST /api/interviews/{id}/start (LangGraph creates the plan + opening question)
Interview Chat
   -> candidate answers (text or voice) -> POST /api/interviews/{id}/answer
   -> LangGraph evaluates, decides the next action, generates the next question
   -> candidate can switch Text <-> Voice at any point without losing progress
   -> repeats until the question limit is reached or the candidate ends early
Final Report Page
   -> GET /api/interviews/{id}/report
```

---

## 3. Folder structure

```
intervue/
  backend/
    app/
      main.py                     FastAPI app, CORS, exception handlers, /api/health, /api/config
      api/routes/                 interviews.py, resume.py, voice.py - thin route handlers
      core/                       config.py (env settings), logging.py, security.py (upload validation, prompt-injection defusing)
      db/                         database.py (engine/session), session.py (get_db, init_db)
      models/                     SQLAlchemy models: candidate, interview, question, answer, evaluation, report
      schemas/                    Pydantic schemas: candidate/job profiles, interview plan, evaluation rubric, API request/response shapes
      repositories/               interview_repository.py - the only file with raw SQLAlchemy queries
      services/                   interview_service.py (orchestrator), resume_service.py, jd_service.py, llm_service.py, voice_service.py
      agents/
        state.py                  InterviewState TypedDict - the single source of truth threaded through the graph
        graph.py                  compiled LangGraph StateGraph
        nodes/                    planning.py, question_generation.py, evaluation.py, decision.py, final_report.py
        prompts/                  LangChain ChatPromptTemplate definitions
      providers/
        llm/                      base.py (ABC), openrouter.py (retries + fallback model)
        voice/                    base.py (ABC), sarvam.py (primary), fallback.py (gTTS/SpeechRecognition)
    tests/                        pytest suite - see Section 8
    requirements.txt
    .env.example
  frontend/
    src/
      components/                 Chat/, MessageBubble/, InterviewSetup helpers, ResumeUploader/, VoiceRecorder/, AudioPlayer/, ModeSwitcher/, ProgressIndicator/, ThemeToggle/, Report/, Landing/
      pages/                      LandingPage, InterviewSetupPage, InterviewPage, ReportPage
      services/                   api.ts, interviewApi.ts, resumeApi.ts, voiceApi.ts
      hooks/                      useInterview.ts, useVoice.ts, useTheme.ts
      types/                      candidate.ts, interview.ts, report.ts
    package.json
  README.md
```

---

## 4. Database schema

```
candidates
  id (pk), full_name, target_role, experience_level,
  resume_filename, resume_raw_text, resume_profile (jsonb),
  job_description_text, job_profile (jsonb), created_at

interviews
  id (pk), candidate_id (fk -> candidates),
  status, mode, interview_plan (jsonb),
  current_topic, current_difficulty,
  questions_asked, question_limit,
  overall_score, topic_scores (jsonb),
  consecutive_strong, consecutive_weak, covered_topics (jsonb),
  created_at, started_at, completed_at

questions
  id (pk), interview_id (fk -> interviews), sequence_index,
  topic, difficulty, text, reason (jsonb), action_type, created_at

answers
  id (pk), question_id (fk -> questions, unique), interview_id (fk),
  text, mode, audio_duration_seconds, word_count, filler_word_count,
  response_latency_ms, created_at

evaluations
  id (pk), answer_id (fk -> answers, unique), interview_id (fk),
  overall_score, correctness, completeness, technical_depth, relevance, clarity,
  strengths (jsonb), weaknesses (jsonb), missing_concepts (jsonb),
  feedback, recommended_action, created_at

final_reports
  id (pk), interview_id (fk -> interviews, unique),
  overall_score, topic_scores (jsonb), strengths (jsonb), weaknesses (jsonb),
  technical_gaps (jsonb), recommended_learning_areas (jsonb),
  question_count, summary, created_at
```

`resume_profile`, `job_profile`, `interview_plan`, and the various score/list fields are `JSON`
columns because their internal shape is inherently semi-structured (a variable-length skills list,
a variable number of projects); every field that's *always* present and simple (name, role,
status, scores) is a real typed column, not buried in JSON.

---

## 5. LangGraph state, nodes, and edges

**State** (`agents/state.py`): a single `InterviewState` TypedDict carrying identity fields,
static context (candidate/job profiles, interview plan), per-turn working fields (current
question/answer/evaluation/action), rolling memory (question/answer/evaluation history, capped to
the last 6 turns when rendered into prompts - see `agents/prompts/context.py`), scoring
aggregates, and progress/termination fields.

**Nodes** (`agents/nodes/`):
- `planning.py` - deterministically builds a balanced roadmap containing resume-grounded topics, a
  resume-wide topic, behavioral areas (ownership/initiative, teamwork/communication, challenges/failure/learning),
  and job-specific technical skills. The LLM only phrases one-line rationales for those topics.
- `question_generation.py` - the one call that actually writes the interview question. It receives
  both the structured candidate profile and the original extracted full resume, so details omitted
  by the deterministic parser remain available to the interviewer.
- `evaluation.py` - scores the candidate's last answer against a 5-dimension rubric via a
  structured-JSON LLM call, validated by `AnswerEvaluation` (Pydantic).
- `decision.py` - **the real agent.** Deterministic score-threshold and streak-counter logic (see
  the module docstring for the exact priority-ordered rules) decides FOLLOW_UP /
  INCREASE_DIFFICULTY / DECREASE_DIFFICULTY / CHANGE_TOPIC / ASK_RESUME_QUESTION /
  ASK_JOB_SPECIFIC_QUESTION / CLARIFY / FINISH_INTERVIEW.
- `final_report.py` - deterministically aggregates topic/overall scores from the full evaluation
  history, and makes one LLM call to write the narrative summary and learning recommendations.

**Conditional edges** (`agents/graph.py`):

```
START --(phase == "start")--> create_plan -> generate_question -> END
START --(phase == "answer_submitted")--> evaluate_answer -> decide_next_action
                                                                 |
                                                (next_action == FINISH_INTERVIEW?)
                                                    /                        \
                                                  no                          yes
                                                   |                           |
                                          generate_question           generate_final_report
                                                   |                           |
                                                  END                         END
```

Because Intervue is a request/response web app rather than a long-running process, "WAIT FOR
ANSWER" from the PRD's conceptual diagram is the natural HTTP request boundary: the graph runs to
a question being generated, returns, and `InterviewService` persists state and waits for the next
API call. When the candidate answers, a fresh graph invocation resumes from the
`"answer_submitted"` entry point using state rehydrated from the database. This intentionally
avoids relying on LangGraph's interrupt/checkpoint machinery for something a plain database row
already solves clearly.

---

## 6. Setup instructions

### 6.1 Prerequisites
- Python 3.11+
- Node.js 18+
- An [OpenRouter](https://openrouter.ai/keys) API key
- A [Sarvam AI](https://www.sarvam.ai/) API key (optional for local dev - see 6.5)
- A [Supabase](https://supabase.com) project (optional for local dev - SQLite works out of the box)

### 6.2 Backend setup

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# edit .env and set at minimum OPENROUTER_API_KEY
uvicorn app.main:app --reload --port 8000
```

The backend creates its tables automatically on startup (`init_db()` in `main.py`) - no manual
migration step is needed for local development. Visit `http://localhost:8000/docs` for the
interactive OpenAPI docs.

### 6.3 Frontend setup

```bash
cd frontend
npm install
npm run dev
```

Visit `http://localhost:5173`. The Vite dev server proxies `/api/*` to `http://localhost:8000`
(see `vite.config.ts`) - no CORS configuration needed in development beyond what's already in
`backend/app/main.py`.

### 6.4 Supabase setup (production database)

1. Create a project at [supabase.com](https://supabase.com).
2. In **Project Settings -> Database**, copy the connection string (use the "Session pooler" or
   direct connection string, in the form `postgresql://postgres:[PASSWORD]@[HOST]:5432/postgres`).
3. Set `DATABASE_URL` in `backend/.env` to that string.
4. Restart the backend - `init_db()` creates all tables (`candidates`, `interviews`, `questions`,
   `answers`, `evaluations`, `final_reports`) on startup the same way it does for SQLite.
5. (Optional) If you want resume files stored in Supabase Storage rather than processed in-memory
   and discarded, set `SUPABASE_URL`, `SUPABASE_ANON_KEY`, and `SUPABASE_SERVICE_ROLE_KEY` - the
   current implementation parses resumes in-memory and does not persist the raw file, only the
   extracted text and structured profile, which keeps the storage layer simple; wiring in Supabase
   Storage is a natural extension point (see Section 11).

**Never** put `SUPABASE_SERVICE_ROLE_KEY` (or any other secret) in frontend code or in any
response the frontend receives - `GET /api/config` is the only endpoint that exposes configuration
to the browser, and it hand-picks non-secret fields only.

### 6.5 OpenRouter setup

1. Create an account and API key at [openrouter.ai/keys](https://openrouter.ai/keys).
2. Set `OPENROUTER_API_KEY` in `backend/.env`.
3. `OPENROUTER_MODEL` and `OPENROUTER_FALLBACK_MODEL` are plain config strings - browse
   [openrouter.ai/models](https://openrouter.ai/models) for current options. Free-tier models
   change over time; if the default in `.env.example` is no longer available, just swap in a
   current model slug. Nothing else in the codebase needs to change.
4. Retries, timeout, and fallback behavior are all configurable via `OPENROUTER_MAX_RETRIES`,
   `OPENROUTER_TIMEOUT_SECONDS`, and `OPENROUTER_FALLBACK_MODEL` - see
   `providers/llm/openrouter.py`.

### 6.6 Sarvam AI setup (voice)

1. Get an API key at [sarvam.ai](https://www.sarvam.ai/).
2. Set `SARVAM_API_KEY` in `backend/.env`.
3. If you don't set it, voice mode still doesn't crash the app: every voice call falls back to
   gTTS (text-to-speech) / SpeechRecognition (speech-to-text) if `ENABLE_VOICE_FALLBACK=true`
   (the default), or returns a clear 503 the frontend surfaces as "switch to text" if fallback is
   disabled. Text mode works with zero voice configuration at all.

**Production voice prerequisite:** FFmpeg must be installed on the backend host and available on
`PATH`. Browser recordings are commonly WebM/Opus and are normalized to mono 16 kHz PCM WAV
before Sarvam STT or the fallback recognizer receives them.

### 6.7 Environment variables reference

See `backend/.env.example` for the full list with inline comments. Summary:

| Variable | Required | Purpose |
|---|---|---|
| `OPENROUTER_API_KEY` | Yes (for LLM features) | Auth for OpenRouter |
| `OPENROUTER_MODEL` | No (has default) | Primary model slug |
| `OPENROUTER_FALLBACK_MODEL` | No (has default) | Used if the primary model fails |
| `SARVAM_API_KEY` | No | Auth for Sarvam voice; falls back gracefully if unset |
| `ENABLE_VOICE_FALLBACK` | No (default true) | Whether to use gTTS/SpeechRecognition if Sarvam fails |
| `DATABASE_URL` | No (defaults to local SQLite) | Point at Supabase Postgres in production |
| `SUPABASE_URL` / `SUPABASE_ANON_KEY` / `SUPABASE_SERVICE_ROLE_KEY` | No | Only needed for Supabase Storage integration |
| `FRONTEND_URL` | No (has default) | Used for CORS allow-origin |
| `MAX_RESUME_SIZE_MB` | No (default 5) | Upload size limit |
| `MIN_QUESTIONS` / `MAX_QUESTIONS` | No (defaults 6/12) | Interview length bounds |

---

## 7. Local development workflow

Run the backend and frontend in two terminals as shown in Section 6.2/6.3. A typical loop:

1. Edit a backend file -> `uvicorn --reload` picks it up automatically.
2. Edit a frontend file -> Vite HMR updates the browser instantly.
3. Check `http://localhost:8000/docs` to try an endpoint directly without the UI.
4. Run `pytest` (Section 8) before committing changes to `agents/` or `services/`.

---

## 8. Testing

```bash
cd backend
pytest -q
```

The suite (`backend/tests/`) does **not** just check for HTTP 200s. It covers:

- `test_decision.py` - the deterministic adaptive engine: strong answer -> harder, weak answer ->
  easier, two weak answers in a row -> topic change, vague/incomplete answer -> clarify, topic
  exhaustion -> topic change, question limit -> finish, score/topic-score aggregation.
- `test_resume_service.py` / `test_jd_service.py` - deterministic parsing extracts what's actually
  present and never invents skills/technologies that aren't in the source text.
- `test_evaluation_schema.py` - malformed LLM output (out-of-range scores, non-numeric scores,
  invalid enum values) is clamped or rejected rather than silently corrupting state.
- `test_llm_provider.py` - OpenRouter primary-model failure correctly falls back to the secondary
  model; total failure raises a clear error; missing API key is caught early.
- `test_voice_service.py` - Sarvam failure falls back to the secondary voice provider; total
  voice failure raises `VoiceUnavailableError` (which the API layer turns into a 503 the frontend
  can act on); filler-word counting is purely lexical.
- `test_interview_flow.py` - a full interview lifecycle end-to-end (with the LLM layer mocked, so
  it runs with no network access and no API key): start -> strong answer -> mid-interview mode
  switch (text to voice) -> weak answer -> reaching the question limit -> a generated final report
  with the full, mode-mixed conversation transcript intact. A second test confirms an LLM outage
  during evaluation degrades to a neutral fallback score instead of crashing the interview.

All 30 tests pass with no external network access, because every LLM/voice call in the flow tests
is mocked at the provider boundary - which is exactly the seam the provider-abstraction pattern
(Section 1) was designed to make testable.

---

## 9. Debugging

- **`GET /api/health`** - basic liveness check.
- **`GET /api/config`** - confirms which non-secret settings the backend loaded.
- **Structured logs**: every lifecycle event (interview created, LLM fallback used, provider
  failure, voice fallback used) is logged as `key=value` pairs via `core/logging.py` - grep the
  backend's stdout for `error=` or `_failed` to find failures quickly. API keys and full
  candidate answer text are never logged.
- **"Both primary and fallback models failed"** - check `OPENROUTER_API_KEY` is set and the model
  slugs in `.env` are still valid on [openrouter.ai/models](https://openrouter.ai/models).
- **Voice always falls back / never uses Sarvam** - check `SARVAM_API_KEY`; the Sarvam provider
  raises immediately with a clear message if it's unset.
- **CORS errors in the browser console** - confirm `FRONTEND_URL` in `backend/.env` matches the
  URL you're actually loading the frontend from (default `http://localhost:5173`).
- **"Interview not found" (404)** - the interview ID in the URL doesn't exist in the database
  currently in use; if you recently switched `DATABASE_URL` (e.g. SQLite -> Supabase), old
  interview links from the previous database won't resolve.

---

## 10. Deployment

This is a two-service deployment (no special orchestration needed):

1. **Database**: use your Supabase project directly - no separate step, since the backend talks
   to it over the standard Postgres protocol.
2. **Backend**: deploy `backend/` to any Python host (Render, Railway, Fly.io, a plain VM). Set
   the environment variables from Section 6.7. Run with
   `uvicorn app.main:app --host 0.0.0.0 --port $PORT`. Set `ENVIRONMENT=production` and
   `FRONTEND_URL` to your deployed frontend's URL (for CORS).
3. **Frontend**: `npm run build` in `frontend/` produces a static `dist/` folder - deploy it to
   any static host (Vercel, Netlify, Cloudflare Pages). Point its API calls at your deployed
   backend by adjusting the dev-only Vite proxy assumption: in production, either serve the
   frontend from the same origin as the backend (simplest - no CORS needed at all) or set the
   `BASE_URL` constant in `frontend/src/services/api.ts` to your backend's full URL.
4. Double-check `backend/.env` is **not** committed and that the deployed backend's environment
   variables are set through your host's secret manager, not baked into the image.

---

## 11. Common errors

| Symptom | Likely cause | Fix |
|---|---|---|
| `OPENROUTER_API_KEY is not set` | `.env` missing or not loaded | Confirm `backend/.env` exists and `OPENROUTER_API_KEY=` has a real value; restart uvicorn |
| Resume upload rejected with 400 | Wrong extension/MIME type, empty file, or over `MAX_RESUME_SIZE_MB` | Upload a real `.pdf` or `.docx` under the size limit |
| Interview stuck on "Preparing your first question..." | OpenRouter unreachable and no fallback model configured, or network blocked | Check backend logs for `question_generation_failed`; the app will still produce a deterministic fallback question rather than hang indefinitely, so a true hang points at a network/DNS issue, not app logic |
| Voice never plays audio | Sarvam and fallback (gTTS) both failed, likely no outbound internet from the backend host | Check backend logs for `fallback_tts_failed`; switch to text mode meanwhile |
| `sqlite3.OperationalError: database is locked` | Multiple backend processes writing to the same SQLite file in local dev | Use one uvicorn process locally, or switch `DATABASE_URL` to Postgres/Supabase |
| Frontend shows CORS error | `FRONTEND_URL` mismatch | Match it exactly (including port) to where the frontend is actually served from |

---

## 12. Future improvements

- Resume file storage in Supabase Storage (currently resumes are parsed in-memory and only the
  extracted text/profile is persisted, not the original file).
- Streaming question generation (token-by-token) instead of waiting for the full LLM response.
- Alembic migrations instead of `create_all` for schema evolution in production.
- Multi-language interviews (Sarvam supports multiple Indian languages - `SARVAM_STT_LANGUAGE`
  and `SARVAM_TTS_VOICE` are already configurable per-deployment; a per-interview language
  selector on the setup page is a natural next step).
- Authenticated candidate accounts and an interview history dashboard (currently every interview
  is accessed by its unguessable UUID link, with no login).


### Interview length
Candidates can choose Quick (5 questions), Standard (8), Deep Dive (12), or Adaptive (6–12). Adaptive uses the same 12-question safety ceiling but can finish early when enough evidence has been collected across the interview.


### Interview question mix

Intervue deliberately mixes a human opening (`tell me about yourself` / career story), resume-grounded questions, role-specific technical questions, behavioral questions, and hypothetical/situational judgment questions. Short interviews reserve room for non-technical coverage instead of becoming technical-only.
