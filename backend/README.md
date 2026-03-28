# AXION Backend (Phase 1)

## Run Locally
1. Create `.env` from `.env.example`.
2. Create virtual environment and install dependencies:
   - `python -m venv .venv`
   - `.venv\\Scripts\\activate`
   - `pip install -r requirements.txt`
3. Start API:
   - `uvicorn app.main:app --reload --host 0.0.0.0 --port 8000`

## Phase 1 Endpoints
- `GET /health`
- `GET /api/v1/system/health`
- `GET /api/v1/auth/google/url`
- `GET /api/v1/auth/google/callback?code=...`
- `GET /api/v1/integrations/gmail/recent?email=you@example.com&limit=10`
- `GET /api/v1/integrations/calendar/upcoming?email=you@example.com&limit=5`
- `POST /api/v1/integrations/calendar/test-event?email=you@example.com`

## Phase 2 Endpoints
- `POST /api/v1/agents/email/run?email=you@example.com`
- `GET /api/v1/agents/calendar/free-slots?email=you@example.com`
- `POST /api/v1/agents/calendar/focus-block?email=you@example.com&duration_minutes=60`
- `POST /api/v1/tasks/`
- `GET /api/v1/tasks/?email=you@example.com`
- `PATCH /api/v1/tasks/{task_id}`
- `DELETE /api/v1/tasks/{task_id}?email=you@example.com`
- `GET /api/v1/tasks/commitments/overdue?email=you@example.com`

## Notes
- Run OAuth URL once in browser, complete consent, then callback stores tokens in `users`.
- Set `GEMINI_API_KEY` to enable Gemini extraction mode for Email Agent. Without it, heuristic extraction is used.
- Supabase schema lives in `sql/001_phase1_schema.sql`.
