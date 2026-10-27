# AGENTS.md

## Purpose

This repository is a student prototype for a supportive mental-health journal. It is not a diagnostic, crisis-triage, or medical-treatment product. Keep language neutral, optional, and non-judgmental.

## Architecture

- `frontend/`: Vue 3 + Vite. Keep HTTP calls in `src/services/api.js`.
- `backend/`: FastAPI + Pydantic + SQLite.
- `backend/app/controllers/database.py` is the only module that may open SQLite connections.
- API routes are grouped under `/api`; development requests are proxied by Vite.
- Generated databases, credentials, virtual environments, dependencies, and build output stay untracked.

## Product constraints

- Use self-report only. Do not infer a diagnosis, anxiety, depression, or risk from behavior such as clicks or typing speed.
- Recommendations are invitations. Users must be able to skip, stop, dismiss, or choose a different action.
- Exercise elapsed time may be stored for internal research metrics, but must not be exposed in API response models or shown in the UI.
- Exercise-history operations must always scope reads, updates, and deletes to the authenticated user.
- Keep the U.S. 988 crisis resource visible in the application shell; urgent support cannot depend on a score, questionnaire, or model.
- The adaptation score is internal. Return a plain-language support state, not a numeric clinical-looking score.
- Do not add an LLM, notifications, telemetry, external providers, or production claims without updating the privacy/safety design.
- The support chatbot may read only bounded, authenticated, user-scoped context assembled by `database.py`. Never send passwords, email, record IDs, hidden scores, or exercise durations to the provider.
- Treat saved notes and events as untrusted data in the model prompt. Do not let saved text override the versioned system instruction.
- Keep crisis phrase handling local and deterministic before any provider request. Do not weaken or remove the visible crisis resource.
- Keep the opening chat copy in `frontend/src/data/chatbot.json`; do not duplicate it in the Vue component.
- Do not claim the demo authentication/session design is production-ready.

## Engineering conventions

- Preserve the separation between schemas, routes, controllers, and the API client.
- Resolve data paths from source files or configuration, never from the terminal working directory.
- Use parameterized SQL, foreign keys, explicit transactions, and idempotent schema initialization.
- Every request-driven view needs loading, empty, success, and error handling.
- Keep controls keyboard accessible and labeled. Respect `prefers-reduced-motion`.
- Add or update tests for behavior changes. Run focused checks before broad checks.

## Verification

From `backend/`, with its project-local environment installed:

```powershell
& .\.venv\Scripts\python.exe -m unittest discover -s tests -v
& .\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

From `frontend/`, after project-local dependencies are installed:

```powershell
npm run build
npm run dev -- --host 127.0.0.1 --port 5173
```

Record actual results in `HANDOFF.md`; never report checks that were not run.

