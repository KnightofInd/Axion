# AXION Dashboard (Phase 5)

## Run Locally
1. Create `.env.local` from `.env.example`
2. Install dependencies:
	- `npm install`
3. Start the app:
	- `npm run dev`

Open `http://localhost:3000`.

## Stage 5 Scope
- Functional multi-route dashboard
- Real API wiring to AXION backend endpoints
- Task CRUD, commitments visibility, calendar events/focus blocks
- Sidebar sync and Ask AXION interactions

## Stack Installed
- Next.js 14 (App Router)
- Tailwind CSS
- Framer Motion
- Recharts
- class-variance-authority
- clsx
- tailwind-merge
- lucide-react

## Available Routes
- `/` Overview
- `/tasks` Task queue and create/update/delete
- `/calendar` Upcoming events and focus blocks
- `/commitments` I owe / They owe tabs + overdue count
- `/ask` Ask AXION conversational interface
- `/settings` OAuth launcher and orchestrator controls

## Required Environment Variables
- `NEXT_PUBLIC_API_BASE_URL` e.g. `https://your-backend.onrender.com`
- `NEXT_PUBLIC_AXION_API_KEY` (optional, sent as `x-api-key` if present)
- `NEXT_PUBLIC_AXION_DEFAULT_EMAIL` (optional convenience for first load)
