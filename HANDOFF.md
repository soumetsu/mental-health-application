# HANDOFF.md

## Current state

Initial full-stack prototype implemented on October 27, 2026.

- Vue mobile-first experience based on the supplied Figma flow.
- FastAPI API with SQLite persistence, demo authentication, questionnaire, daily check-ins, event logging, dashboard adaptation, and exercise catalog.
- Account profiles now include a display name, optional email and bio, a subdued sample avatar or compressed uploaded profile photo, and an account theme.
- A dedicated Settings page persists appearance, text size, reduced motion, higher contrast, automatic chat reading, and optional voice-input preferences.
- `report.md` was reviewed and left unchanged because it already contains user edits.
- The single visible Figma calendar raster is stored locally at `frontend/public/figma-calendar.png`; no temporary Figma URLs should remain in runtime code.

## Product decisions used to fill design gaps

- The hidden adaptation value is translated into one of `support`, `gentle`, `steady`, or `calm`; the numeric value is never sent to the browser.
- Recommendations never auto-start. A user can dismiss or choose another exercise.
- The first working questionnaire asks about common stressors, sleep, and desired support style.
- Check-ins use explicit self-report: mood, energy, optional words, and tags.
- Events are positive, difficult, or neutral and appear in a color-coded monthly calendar/list.
- Crisis support remains visible regardless of authentication or app state.
- The exercise area implements user-paced 5-4-3-2-1 grounding plus hold-to-inhale/release-to-exhale breathing and the original four-count timer. Elapsed time is stored privately but never returned to or displayed by the frontend.
- Exercise history supports create, list, reflection updates, completion/stop updates, and deletion for the signed-in user.
- A floating chat bubble opens a supportive-reflection window. The backend supplies a bounded seven-day summary of the signed-in user's saved context to Gemini with provider storage disabled.
- Chat crisis-language handling is local and deterministic, before any Gemini request. Ordinary chat requires `GEMINI_API_KEY` in the ignored root `.env`.
- The chatbot's introductory copy is configured in `frontend/src/data/chatbot.json` and is reset each time the chat window opens.
- Chat replies can be read aloud with the browser speech-synthesis API. When enabled in Settings, voice input supplies dictation and a start/stop conversation loop; the app sends only the resulting transcript through the existing chat route and does not save raw audio.
- Voice remains optional. The interface discloses that the browser or operating system may use its own speech service to process audio.

## Setup status

Project-local dependencies were installed with user-approved network access. The resulting versions are:

- Python 3.14.8 in `backend/.venv`
- FastAPI 0.162.0 and Uvicorn 0.54.0
- Vue 3.5.44, Vite 7.3.7, and `@vitejs/plugin-vue` 6.0.10
- npm reported 0 vulnerabilities across 36 audited packages

To recreate the local environments:

```powershell
py -3.14 -m venv backend\.venv
& .\backend\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
Set-Location frontend
npm install
```

## Verification record

- `python -m compileall -q app tests`: passed.
- `backend/.venv/Scripts/python.exe -m unittest discover -s tests -v`: 4 tests passed, including exercise-history CRUD and hidden duration persistence.
- OpenAPI generation: passed; 13 paths registered.
- `npm run build`: passed after the exercise-history milestone; 19 modules transformed.
- `npm ls --depth=0`: expected Vue/Vite packages resolved.
- Local API smoke flow: register, questionnaire, check-in, event, dashboard, exercises, and health returned expected 2xx responses.
- Browser review: desktop and 390 × 844 mobile welcome/dashboard/check-in/calendar/exercise layouts inspected; no browser console warnings or errors.
- The generated QA SQLite database was removed after verification so the next run starts clean.

Update this section with exact commands and outcomes after running checks.

### Restart and verification on November 4, 2026

- Backend restarted with `backend/.venv/Scripts/python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000`; `GET /api/health` returned HTTP 200 with `{"status":"ok","database":"ready"}`.
- Frontend restarted with `npm run dev -- --host 127.0.0.1 --port 5173`; `GET /` returned HTTP 200.
- From `backend/`, `& .\\.venv\\Scripts\\python.exe -m unittest discover -s tests -v`: passed, 4 tests.
- From `frontend/`, `npm run build`: passed; Vite transformed 20 modules.
- `git fetch origin` could not update remote tracking information because access to `.git/FETCH_HEAD` was denied. The checkout showed `main...origin/main` with no ahead/behind count before the fetch, so remote currency is unconfirmed.
- `report_2.md` has uncommitted user edits and was preserved. No commit was created.

### Profile, settings, and voice milestone on November 6, 2026

- Added authenticated `/api/profile` and `/api/settings` updates. All account reads and writes remain user-scoped through `backend/app/controllers/database.py`.
- Database initialization now idempotently adds profile fields and a `user_preferences` table for existing local databases.
- Added Profile and Settings pages, a header profile icon, four subdued sample avatars, uploaded-photo resizing, three themes, and persisted accessibility preferences.
- The account header uses a mobile-prioritized avatar menu. Its large first action shows the saved avatar, display name, and username; Profile, Settings, page reading, and logout are available from the dropdown without crowding the mobile header.
- Default avatars are project-local 256 × 256 transparent PNG assets in `frontend/public/avatars/`: leaf, moon, tea cup, and a faceless fox silhouette. They were generated with the built-in image tool in a coordinated muted paper-cut style, then resized for web use. The mobile account control renders only the selected image at a fixed size so flex layout cannot collapse it into a dot.
- The header now uses a direct fixed-size `<img>` for the account control instead of the reusable avatar wrapper. The Profile page keeps the saved picture, name, username, and editable account fields together at the top; sample icons are available through a collapsed chooser so they do not dominate the page.
- Added user-initiated page reading, per-message chat reading, optional automatic reply reading, voice dictation, and an explicitly started/stopped conversation mode using browser APIs.
- On mobile, the open chat becomes the top application layer beneath the always-visible 988 bar. The app header stays behind it, and the redundant floating close bubble is hidden while the chat header's close control is available.
- Restarted the backend after the migration; `GET http://127.0.0.1:8000/api/health` returned HTTP 200 with `{"status":"ok","database":"ready"}`, and `GET http://127.0.0.1:5173/` returned HTTP 200.
- `git diff --check` reported no whitespace errors in the milestone files; Git emitted its existing LF-to-CRLF working-copy warning for `frontend/src/data/chatbot.json`.
- Verification before the branch commit: from `backend/`, `& .\.venv\Scripts\python.exe -m unittest discover -s tests -v` passed all 4 existing tests; from `frontend/`, `npm run build` passed with 24 modules transformed. These tests make no live model calls.
- Authenticated profile/settings smoke flows, microphone permissions, the latest mobile layout changes, and a fresh dependency installation from a clean checkout remain unverified. Build success does not establish those behaviors.
- README now includes prerequisites, clone/branch selection, virtual environment setup, `npm ci`, environment configuration, startup, local checks, troubleshooting, and explicit clean-checkout verification limits.

## Known demo limitations

- Bearer sessions are process-local and disappear when the backend restarts.
- There is no password reset, verification, MFA, rate limiting, encrypted-at-rest health data, audit trail, export/delete-account flow, or production deployment hardening.
- Reminder delivery is represented in preferences only; no push/email/SMS service exists.
- The exercise catalog is static and not medical treatment.
- The chatbot is not a therapist and has not been clinically validated. No live provider call or mocked chatbot behavior test was run in this documentation/commit pass; current credentials were not inspected.
- Speech synthesis and recognition depend on browser and operating-system support. Voice recognition may be processed by the browser vendor; the prototype does not record or store raw audio.
- Uploaded profile photos are stored as compressed image data in the local SQLite database. There is no separate media store, malware scanning, or account export flow.
- The password minimum and local authentication are suitable only for a class prototype.

## Suggested next milestone

Exercise profile migration, photo upload, theme persistence, accessibility modes, speech support, and unsupported-browser fallbacks at mobile and desktop widths. Independently follow the README in a clean checkout. Product priorities are a journal/check-in history view, event editing, editable support preferences, and a final user-paced exhale step for interactive breathing. Add deterministic chatbot coverage and validate context-sharing choices before broader use. Data deletion/export and durable secure sessions remain deployment prerequisites.

