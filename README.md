# 🎙️ INTERVUE

### *Turn every answer into your next question.*

> **What if your mock interview didn't just ask questions...**
>
> **What if it actually listened? 👀**

**INTERVUE** is an adaptive AI mock interview platform that conducts interviews like an actual interviewer — using your **resume, target role, job description, previous answers, performance, and voice** to decide what should happen next.

No boring list of 20 random questions.

No "Question 1 → Question 2 → Question 3 → good luck bro." 💀

Instead:

**You answer → AI evaluates → AI decides → next question adapts.**

---

## 🚀 TRY INTERVUE

### 🎯 [**LIVE DEMO → INTERVUE**](https://intervue-frontend-tgi7.onrender.com)

> **Best experienced with a microphone 🎙️**

### ⚡ Backend Health

[**API → `intervue-backend-v6ox.onrender.com/api/health`**](https://intervue-backend-v6ox.onrender.com/api/health)

---

# 🧠 THE IDEA

Traditional mock interviews look like this:

```text
Question
   ↓
Answer
   ↓
Question
   ↓
Answer
   ↓
Question
   ↓
"Good job 👍"
```

INTERVUE looks more like this:

```text
             YOUR RESUME
                  │
                  ▼
          ┌───────────────┐
          │    INTERVUE   │
          │   AI ENGINE   │
          └───────┬───────┘
                  │
          Ask the right question
                  │
                  ▼
              YOU ANSWER
                  │
                  ▼
             AI EVALUATES
                  │
        ┌─────────┼─────────┐
        │         │         │
     Strong    Weak      Missing
        │         │         │
        ▼         ▼         ▼
      Probe    Simplify   Explore
        │         │         │
        └─────────┼─────────┘
                  ▼
          NEXT QUESTION
```

### That's the entire philosophy:

> **The next question should depend on the last answer.**

---

# 👀 WHAT MAKES IT DIFFERENT?

## 📄 01 — Your resume actually matters

INTERVUE doesn't just read the first project on your resume and call it a day.

It extracts and uses your **resume-wide background** to generate relevant questions.

That means the interview can explore:

* projects
* internships
* skills
* experience
* career story
* achievements
* technical background
* behavioral experiences

So instead of:

> "Tell me about React."

You might get:

> "You mentioned building X during your internship. What was the hardest decision you had to make there?"

Now we're talking. 👀

---

## 🎯 02 — The job description matters too

INTERVUE can compare your background with the target role and identify areas worth exploring.

The interview can cover:

```text
Your Resume
     +
Job Description
     +
Your Answers
     ↓
Personalized Interview
```

So you're not practicing **generic interview questions**.

You're practicing for **your interview**.

---

# 🤖 03 — IT ACTUALLY ADAPTS

This is the heart of INTERVUE.

The system evaluates every answer and tracks things like:

* correctness
* completeness
* technical depth
* relevance
* clarity
* strengths
* weaknesses
* missing concepts
* topic coverage

Then a deterministic decision layer decides what should happen next.

For example:

```text
Candidate gives strong answer
          ↓
AI identifies strong evidence
          ↓
Probe deeper
          ↓
More challenging follow-up
```

Or:

```text
Candidate struggles
       ↓
Weak / incomplete evidence
       ↓
Change direction
       ↓
Clarify or explore another area
```

The interview isn't following a fixed script.

**The answer changes the interview.**

---

# 🧩 04 — NOT JUST TECHNICAL QUESTIONS

INTERVUE is designed to feel more like a real interview.

The interview can explore:

### 💻 Technical

* skills from the resume
* job requirements
* technical depth
* projects
* implementation decisions

### 🧑‍💼 Behavioral

* teamwork
* communication
* ownership
* motivation
* initiative
* challenges
* failure
* learning

### 🎭 Situational

* conflicting priorities
* ambiguous tasks
* unhappy teammates or stakeholders
* deadline trade-offs
* discovering mistakes before delivery

So the interview isn't:

> "Explain REST APIs."

for 45 minutes straight. 😭

---

# 🎙️ 05 — TALK TO IT

INTERVUE supports both:

```text
⌨️ TEXT
  ↕
🎙️ VOICE
```

For voice interviews, the pipeline is:

```text
Browser Microphone
        ↓
MediaRecorder
        ↓
WebM / Opus Audio
        ↓
FFmpeg
        ↓
Mono 16k PCM WAV
        ↓
Sarvam Speech-to-Text
        ↓
Candidate Answer
        ↓
AI Evaluation
```

And when primary transcription isn't available, the system has a fallback speech-recognition path.

Because:

> **"Sorry, I couldn't hear you"**

shouldn't be the final boss of your interview. 💀

---

# 🗣️ THE AI ALSO TALKS BACK

The platform supports AI-generated speech using Sarvam TTS.

So the experience becomes:

```text
        🤖 AI INTERVIEWER
              │
              ▼
        asks a question
              │
              ▼
          🎙️ YOU
              │
              ▼
         gives answer
              │
              ▼
        🧠 AI EVALUATES
              │
              ▼
       decides what next
              │
              ▼
        🤖 AI INTERVIEWER
```

It's much closer to an actual conversation than filling out a questionnaire.

---

# 🎮 CHOOSE YOUR INTERVIEW MODE

INTERVUE supports four interview lengths:

| Mode             | Questions | Vibe                                   |
| ---------------- | --------: | -------------------------------------- |
| ⚡ **Quick**      |     **5** | Focused warm-up                        |
| 🎯 **Standard**  |     **8** | Balanced interview                     |
| 🧠 **Deep Dive** |    **12** | More detailed assessment               |
| 🧬 **Adaptive**  |  **6–12** | AI decides when enough evidence exists |

### Adaptive mode is the interesting one.

It doesn't blindly say:

> "We have reached Question 12. Bye."

Instead, it can finish once the interview has gathered enough useful evidence.

---

# 🧠 UNDER THE HOOD

Here's where the fun stuff happens.

```text
                    ┌───────────────────┐
                    │     FRONTEND      │
                    │    React + TS     │
                    └─────────┬─────────┘
                              │
                         HTTP / REST
                              │
                              ▼
                    ┌───────────────────┐
                    │      FASTAPI      │
                    │      BACKEND      │
                    └─────────┬─────────┘
                              │
                              ▼
                    ┌───────────────────┐
                    │    INTERVIEW      │
                    │     SERVICE       │
                    └─────────┬─────────┘
                              │
                              ▼
                    ┌───────────────────┐
                    │    LANGGRAPH      │
                    │  INTERVIEW GRAPH  │
                    └─────────┬─────────┘
                              │
                    ┌─────────┴─────────┐
                    ▼                   ▼
             Question Node       Evaluation Node
                    │                   │
                    └─────────┬─────────┘
                              ▼
                    ┌───────────────────┐
                    │ DECISION ENGINE   │
                    │ What happens next?│
                    └─────────┬─────────┘
                              │
                              ▼
                    Next Interview Action
                              │
                              ▼
                    ┌───────────────────┐
                    │    PostgreSQL     │
                    │     Supabase      │
                    └───────────────────┘
```

---

# 🧠 LANGGRAPH = THE INTERVIEW BRAIN

INTERVUE uses **LangGraph** to represent the interview flow as a stateful graph.

Conceptually:

```text
START
  ↓
Load Interview State
  ↓
Generate Question
  ↓
Candidate Answers
  ↓
Evaluate Answer
  ↓
Update State
  ↓
Decision
  │
  ├── Ask Follow-up
  ├── Ask New Topic
  ├── Increase Difficulty
  ├── Explore Weak Area
  └── Finish Interview
```

The important part?

### The LLM does NOT control everything.

The LLM handles things it's good at:

> **semantic reasoning**

Python handles things that should be deterministic:

> **control flow + limits + interview rules**

That separation makes the system much easier to reason about.

---

# 🧠 ADAPTIVE INTERVIEW ENGINE

At a high level:

```python
answer
   ↓
evaluate(answer)
   ↓
update_interview_state()
   ↓
decide_next_action()
   ↓
generate_next_question()
```

The system keeps track of things like:

```text
Current Topic
Current Difficulty
Questions Asked
Question Limit
Covered Topics
Consecutive Strong Answers
Consecutive Weak Answers
Topic Scores
```

This lets the interview evolve instead of simply progressing linearly.

---

# 📄 RESUME INTELLIGENCE — WITHOUT RAG

One deliberate architecture choice:

### INTERVUE does not require a vector database or RAG pipeline for resume grounding.

Instead, the application:

```text
Resume File
    ↓
Extract Text
    ↓
Create Structured Profile
    ↓
Store Raw Resume Text
    ↓
Inject Relevant Resume Context
    ↓
LLM Question Generation
```

The resume is grounded directly into the interview context.

That keeps the architecture simpler for this use case.

No unnecessary:

```text
Vector DB
Embeddings
Retriever
Chunking pipeline
RAG orchestration
```

just because the word **AI** appeared somewhere. 😭

---

# 🛡️ RELIABILITY

AI systems are cool.

AI systems that randomly die halfway through your interview?

**Not cool.**

INTERVUE includes reliability mechanisms around the external AI services.

### OpenRouter

```text
LLM Request
    ↓
Timeout / Retry Handling
    ↓
Primary Model
    ↓
Fallback Model
```

### Voice

```text
Browser Audio
     ↓
Audio Conversion
     ↓
Sarvam STT
     ↓
Fallback Recognizer
```

The application also validates and limits uploaded resume content before using it in prompts.

---

# 🗄️ DATABASE

INTERVUE uses **PostgreSQL through Supabase** with SQLAlchemy.

The core data model looks like:

```text
Candidate
   │
   └───────────────┐
                   ▼
               Interview
                   │
          ┌────────┼────────┐
          ▼        ▼        ▼
      Question   Answer   Evaluation
          │        │        │
          └────────┴────────┘
                   │
                   ▼
              Final Report
```

### Main entities

* `Candidate`
* `Interview`
* `Question`
* `Answer`
* `Evaluation`
* `Final Report`

Interview planning and analysis data are stored in structured JSON fields where appropriate.

---

# ⚙️ TECH STACK

| Layer               | Technology            |
| ------------------- | --------------------- |
| 🎨 Frontend         | React + TypeScript    |
| ⚡ Build             | Vite                  |
| 🎨 Styling          | Tailwind CSS          |
| 🌐 Routing          | React Router          |
| 🐍 Backend          | FastAPI               |
| 🧠 AI Workflow      | LangGraph + LangChain |
| 🤖 LLM              | OpenRouter            |
| 🎙️ STT             | Sarvam                |
| 🔊 TTS              | Sarvam                |
| 🗄️ Database        | PostgreSQL / Supabase |
| 🧱 ORM              | SQLAlchemy            |
| 📄 Resume Parsing   | pypdf + python-docx   |
| 🎤 Audio Processing | FFmpeg                |
| 🧪 Testing          | Pytest                |
| ☁️ Deployment       | Render                |

---

# 🏗️ PROJECT STRUCTURE

```text
INTERVUE/
│
├── backend/
│   ├── app/
│   │   ├── agents/
│   │   │   ├── nodes/
│   │   │   ├── prompts/
│   │   │   └── graph.py
│   │   │
│   │   ├── api/
│   │   │   └── routes/
│   │   │
│   │   ├── core/
│   │   ├── db/
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── services/
│   │   └── providers/
│   │
│   ├── tests/
│   └── requirements.txt
│
├── frontend/
│   ├── public/
│   ├── src/
│   │   ├── components/
│   │   ├── hooks/
│   │   ├── pages/
│   │   ├── services/
│   │   └── types/
│   │
│   ├── package.json
│   └── vite.config.ts
│
├── render.yaml
└── README.md
```

---

# 🔥 THE ENGINE IN ONE SENTENCE

> **INTERVUE combines resume-aware context, job-aware planning, LLM evaluation, deterministic decision logic, and voice interaction to create an interview that adapts to the candidate instead of forcing the candidate through a fixed script.**

---

# 🧪 TESTING

The backend includes automated tests covering important interview behavior.

Examples include:

* interview planning
* question limits
* adaptive decisions
* behavioral topics
* situational topics
* fallback behavior
* state transitions

The goal isn't just:

```text
"It works on my laptop."
```

The goal is:

```text
"It still works after I changed something at 2 AM."
```

---

# 🚀 RUN LOCALLY

## 1. Clone

```bash
git clone https://github.com/diyavinod1/INTERVUE.git
cd INTERVUE
```

---

## 2. Backend

```bash
cd backend

python -m venv .venv
source .venv/bin/activate
```

Windows:

```bash
.venv\Scripts\activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Create your environment file:

```bash
cp .env.example .env
```

Then configure your API keys and database.

Start the backend:

```bash
python -m uvicorn app.main:app --reload --port 8000
```

Backend:

```text
http://localhost:8000
```

Health check:

```text
http://localhost:8000/api/health
```

---

# 🎨 FRONTEND

```bash
cd frontend
npm install
npm run dev
```

Frontend:

```text
http://localhost:5173
```

---

# 🔐 ENVIRONMENT VARIABLES

INTERVUE uses environment variables for external services and deployment configuration.

Important variables include:

```env
DATABASE_URL=

OPENROUTER_API_KEY=
OPENROUTER_MODEL=
OPENROUTER_FALLBACK_MODEL=

SARVAM_API_KEY=
SARVAM_BASE_URL=
SARVAM_TTS_VOICE=
SARVAM_STT_LANGUAGE=

SUPABASE_URL=
SUPABASE_ANON_KEY=
SUPABASE_SERVICE_ROLE_KEY=

FRONTEND_URL=
BACKEND_URL=

ENVIRONMENT=
LOG_LEVEL=
```

### ⚠️ Never commit real API keys.

Your `.env` belongs on your machine.

Your production secrets belong in your deployment environment.

Not in GitHub.

Not in screenshots.

Definitely not in a README. 😭

---

# ☁️ PRODUCTION ARCHITECTURE

INTERVUE is deployed using **Render + Supabase**.

```text
                 INTERNET
                    │
          ┌─────────┴─────────┐
          ▼                   ▼
   Render Frontend      Render Backend
       React                 FastAPI
          │                   │
          │                   ├──────► OpenRouter
          │                   │
          │                   ├──────► Sarvam
          │                   │
          │                   ▼
          │              Supabase
          │             PostgreSQL
          │
          └──────── API ────────►
```

Production URLs are configured through environment variables rather than hardcoded into the application.

---

# 🎨 DESIGN PHILOSOPHY

INTERVUE intentionally avoids the usual:

```text
🌌 purple gradient
✨ floating particles
🤖 giant glowing robot
💎 "AI-powered" repeated 47 times
```

Instead:

```text
Dark
Minimal
Professional
Calm
Human
Focused
```

The interface is designed to feel like a serious interview product rather than an AI demo from 2023.

### Visual system

```text
Background     #0B0F14
Surface        #121820
Elevated       #202833
Primary        #3B82F6
Hover          #2563EB
Secondary      #8B949E
Success        #22C55E
```

---

# 🧭 PRODUCT PRINCIPLES

### 1. Conversation > Questionnaire

The interview should feel like a conversation.

### 2. Context > Randomness

Questions should have a reason.

### 3. Evidence > Buzzwords

The system evaluates actual answers.

### 4. Adaptation > Fixed Scripts

The next question should respond to what happened before.

### 5. Reliability > AI Magic

Deterministic rules handle deterministic behavior.

### 6. Human Experience > Tech Demo

The candidate should forget they're navigating a workflow.

---

# 🛣️ WHAT'S NEXT?

INTERVUE has plenty of room to grow.

Possible future directions:

```text
📊 richer analytics
🎯 company-specific interview packs
🧠 stronger role-specific evaluation
🎙️ more natural voice conversations
📈 long-term candidate progress
🏆 interview history & benchmarking
👥 recruiter / interviewer dashboards
🔐 authentication & profiles
```

---

# 💡 WHY I BUILT IT

Because practicing interviews shouldn't mean memorizing answers to:

> "What are your strengths?"

for the 700th time. 😭

Real interviews are dynamic.

Interviewers listen.

They notice what you say.

They notice what you don't say.

They ask follow-ups.

They change direction.

They dig deeper when something sounds interesting.

They move on when you've demonstrated enough.

**INTERVUE tries to bring that behavior into an AI-powered practice environment.**

---

# 🎙️ THE WHOLE PRODUCT

```text
        RESUME
           +
    JOB DESCRIPTION
           +
      CAREER STORY
           +
       YOUR ANSWER
           +
      VOICE / TEXT
           ↓
    ┌───────────────┐
    │    INTERVUE   │
    │               │
    │  UNDERSTANDS  │
    │       ↓       │
    │  EVALUATES    │
    │       ↓       │
    │  DECIDES      │
    │       ↓       │
    │  ADAPTS       │
    └───────┬───────┘
            ↓
      NEXT QUESTION
            ↓
       BETTER PRACTICE
```

---

# ⭐ IF YOU MADE IT THIS FAR...

You probably want to try it now. 😭

## 🎙️ [**OPEN INTERVUE →**](https://intervue-frontend-tgi7.onrender.com)

Upload your resume.

Choose your role.

Pick your interview mode.

Turn on your mic.

And let the interviewer begin.

---

## 🧠 INTERVUE

### *Don't practice questions.*

### **Practice being interviewed.** 🎙️

---

<p align="center">

**Built with React • FastAPI • LangGraph • OpenRouter • Sarvam • PostgreSQL • Supabase**

</p>

<p align="center">

⭐ If you found the project interesting, consider giving the repo a star.

</p>
