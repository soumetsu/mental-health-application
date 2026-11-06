# Mindful Moments

A full-stack mental-health journaling class prototype based on the project's Figma skeleton. It supports onboarding, short daily self-reports, positive/difficult event logging, a calendar, user-controlled exercises, supportive chat, and account appearance and accessibility preferences.

This is an educational prototype, not a medical device or diagnostic service. In the U.S., call or text **988** for crisis support. If there is immediate danger, contact local emergency services.

## Stack

- Vue 3 + Vite frontend
- FastAPI + Pydantic backend
- SQLite persistence using Python's standard library

## Run locally

Prerequisites: Git, Python 3.14 (including the Windows `py` launcher), and Node.js 22.12 or newer with npm. The commands below target Windows PowerShell. Start in the directory where you want to keep the project:

```powershell
git clone https://github.com/soumetsu/mental-health-application.git
Set-Location mental-health-application
git switch codex/exercise-interactions
py -3.14 -m venv backend\.venv
& .\backend\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
Copy-Item .env.example .env
Set-Location frontend
npm ci
Set-Location ..
```

The feature branch must be available on the remote for that `git switch` command to work. A local commit alone does not publish it. After merging, use the default branch instead.

The example environment contains no credentials. Leave the chatbot key empty to use account creation, check-ins, events, profiles, settings, and exercises without paid model requests. Ordinary chat needs the backend-only key described below. Voice support depends on the browser.

Use two terminals, each starting from the repository root:

```powershell
Set-Location backend
& .\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

```powershell
Set-Location frontend
npm run dev -- --host 127.0.0.1 --port 5173
```

Open `http://127.0.0.1:5173`. Vite proxies `/api` to FastAPI.

Create a new demo account and complete setup. The backend creates its SQLite database and applies profile/preferences migrations at startup. No database or pre-existing account is required. Restarting the backend expires login sessions; sign in again afterward.

### Local checks

From the repository root:

```powershell
Set-Location backend
& .\.venv\Scripts\python.exe -m unittest discover -s tests -v
Set-Location ..\frontend
npm run build
Set-Location ..
```

The current backend tests cover authentication, saved questionnaire/check-in/event data, dashboard output, user separation, and exercise history. They do not call the live model and are not a substitute for chatbot evaluation. Check `HANDOFF.md` for actual verification results and remaining coverage gaps.

For an installation smoke check, confirm `/api/health` returns `status: ok`, create an account, save a check-in and event, complete or stop an exercise, and save a profile/theme change. Reload and sign in again to check persistence. A fresh installation from a clean checkout has not yet been independently verified.

### Troubleshooting

- If the page cannot load, keep the frontend terminal running and check port 5173.
- If login or saving fails, check the backend terminal and `http://127.0.0.1:8000/api/health`.
- After backend restart, expired sessions require signing in again.
- An ordinary chat configuration error with an empty API key is expected; the rest of the app remains usable.

## API summary

- `GET /api/health`
- `POST /api/auth/register`, `POST /api/auth/login`, `GET /api/auth/me`, `POST /api/auth/logout`
- `PUT /api/profile`, `PUT /api/settings`
- `GET/PUT /api/questionnaire`
- `GET /api/dashboard`
- `GET/POST /api/check-ins`
- `GET/POST /api/events`, `DELETE /api/events/{event_id}`
- `GET /api/exercises`
- `GET/POST /api/exercise-history`, `PATCH/DELETE /api/exercise-history/{history_id}`
- `POST /api/chat` — authenticated supportive reflection using bounded recent app context

Exercise timing is recorded internally from start to completion or stop, but duration is intentionally omitted from all browser-facing response models and screens.

## Chatbot setup

The chat bubble uses the Gemini Interactions API from the backend. Add a Gemini authorization API key to the ignored project-root `.env` file:

```text
GEMINI_API_KEY=your-key-here
GEMINI_MODEL=gemini-3.5-flash-lite
```

Restart FastAPI after changing `.env`. The key is never returned by the API or exposed through a Vite environment variable. Each request sends the current message, up to ten recent chat messages, and a bounded seven-day summary of the signed-in user's questionnaire, check-ins, events, and exercise history. Requests set provider-side storage to false.

The opening greeting and other introductory chat copy live in `frontend/src/data/chatbot.json`. A fresh lightweight chat session starts with that introduction every time the bubble is opened.

This assistant is for supportive reflection only. It is not therapy, diagnosis, medical advice, or emergency support.

## Saved history and personalization

The dashboard uses explicit recent self-reports and saved events to choose a plain-language support state and optional exercise suggestion. The internal numeric value is not returned to the browser. Chat receives a bounded recent summary, while exercise history supports reflections and completion/stop records. Profile, theme, and accessibility preferences persist per account.

Known product gaps: there is no unified journal/check-in history screen, event editing, or interface to revise onboarding answers. The support-style choice is stored but does not yet clearly alter the interface. Hold-to-breathe currently completes on the fourth release, so a final user-paced exhale/finish step remains a refinement.

## Demo privacy and limitations

Journal data is stored locally and is not encrypted at rest by this application. Local storage should not be understood as protection from other people with access to the computer. Chat sends the current message and bounded recent context to Gemini; provider-side storage is disabled in the request, which is not a complete privacy guarantee. The visible crisis resource is available independently of model replies, and local phrase matching is not comprehensive crisis detection.

Authentication uses process-local bearer sessions. There is no password reset, MFA, account export/deletion, rate limiting, or production security hardening. Use fictional data for demonstrations and peer testing.

## Voice and accessibility privacy

Read-aloud uses the browser's speech-synthesis API. Optional dictation and conversation mode use the browser's speech-recognition API when available. The application does not record or store raw audio; it receives only the transcript produced by the browser and sends that text through the existing authenticated chat route. A browser or operating system may process speech using its own service, so voice features require an explicit user action, remain optional, show an in-product disclosure, and always provide stop controls.

Profile photos are resized in the browser and stored as compressed image data in the local SQLite database. The prototype has no external media store, account export, or production privacy controls.

OpenAPI is available at `http://127.0.0.1:8000/docs` while the backend is running.

