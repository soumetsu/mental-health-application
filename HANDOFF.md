# HANDOFF.md

## Current state

Initial full-stack prototype implemented on October 27, 2026.

- Vue mobile-first experience based on the supplied Figma flow.
- FastAPI API with SQLite persistence, demo authentication, questionnaire, daily check-ins, event logging, dashboard adaptation, and exercise catalog.
- `report.md` was reviewed and left unchanged because it already contains user edits.
- The single visible Figma calendar raster is stored locally at `frontend/public/figma-calendar.png`; no temporary Figma URLs should remain in runtime code.

## Product decisions used to fill design gaps

- The hidden adaptation value is translated into one of `support`, `gentle`, `steady`, or `calm`; the numeric value is never sent to the browser.
- Recommendations never auto-start. A user can dismiss or choose another exercise.
- The first working questionnaire asks about common stressors, sleep, and desired support style.
- Check-ins use explicit self-report: mood, energy, optional words, and tags.
- Events are positive, difficult, or neutral and appear in a color-coded monthly calendar/list.
- Crisis support remains visible regardless of authentication or app state.
- The exercise area implements user-paced 5-4-3-2-1 grounding and internally paced four-count breathing. Elapsed time is stored privately but never returned to or displayed by the frontend.
- Exercise history supports create, list, reflection updates, completion/stop updates, and deletion for the signed-in user.

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

## Known demo limitations

- Bearer sessions are process-local and disappear when the backend restarts.
- There is no password reset, verification, MFA, rate limiting, encrypted-at-rest health data, audit trail, export/delete-account flow, or production deployment hardening.
- Reminder delivery is represented in preferences only; no push/email/SMS service exists.
- The exercise catalog is static and not medical treatment.
- The password minimum and local authentication are suitable only for a class prototype.

## Suggested next milestone

Install project-local dependencies, run the recorded checks, then do an integrated browser pass at mobile and desktop widths. After that, prioritize data deletion/export, durable secure sessions, and a privacy/threat-model review before adding more personalization.

