# Mindful Moments

A bare-bones full-stack mental-health journaling prototype based on the project's Figma skeleton and `report.md`. It supports optional onboarding, short daily self-reports, positive/difficult event logging, a color-coded calendar, and user-controlled calming exercises.

This is an educational prototype, not a medical device or diagnostic service. In the U.S., call or text **988** for crisis support. If there is immediate danger, contact local emergency services.

## Stack

- Vue 3 + Vite frontend
- FastAPI + Pydantic backend
- SQLite persistence using Python's standard library

## Run locally

Create project-local environments and install the declared dependencies first. Then use two terminals:

```powershell
Set-Location backend
& .\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

```powershell
Set-Location frontend
npm run dev -- --host 127.0.0.1 --port 5173
```

Open `http://127.0.0.1:5173`. Vite proxies `/api` to FastAPI.

## API summary

- `GET /api/health`
- `POST /api/auth/register`, `POST /api/auth/login`, `GET /api/auth/me`, `POST /api/auth/logout`
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

OpenAPI is available at `http://127.0.0.1:8000/docs` while the backend is running.

