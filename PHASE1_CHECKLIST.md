# AXION Phase 1 Checklist

## Completed in Repo
- Next.js 14 dashboard scaffolded in `dashboard/`
- FastAPI backend scaffolded in `backend/`
- Supabase schema created in `backend/sql/001_phase1_schema.sql`
- Environment templates created (`backend/.env.example`)

## External Setup You Need To Do
1. Google Cloud project and APIs
   - Create project `axion-prod`
   - Enable Gmail API, Calendar API, Tasks API, Gemini API, Vertex AI API, Cloud Run API
2. OAuth
   - Configure consent screen
   - Add your test users
   - Create OAuth Client ID (Web)
   - Add redirect URI: `http://localhost:8000/api/v1/auth/google/callback`
3. Supabase
   - Create project
   - Run SQL in `backend/sql/001_phase1_schema.sql`
   - Copy `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY`

## Credentials Needed From You (for live integration tests)
- `GOOGLE_CLIENT_ID`
- `GOOGLE_CLIENT_SECRET`
- `SUPABASE_URL`
- `SUPABASE_SERVICE_ROLE_KEY`
- `AXION_INTERNAL_API_KEY` (you choose any long random string)

## Next Step After You Provide Credentials
- Fill `backend/.env`
- Run backend locally
- Validate:
  - OAuth URL generation
  - Read 10 Gmail emails
  - Read 5 upcoming calendar events
  - Write one test calendar event
