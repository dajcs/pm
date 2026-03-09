# Kanban Studio

A Kanban project management app with AI-assisted board editing.

## Stack

- **Frontend:** Next.js 16 + React 19 + TypeScript + Tailwind CSS 4
- **Backend:** Python FastAPI + SQLite + JWT auth
- **AI:** OpenRouter API (`openai/gpt-oss-120b:free`)
- **Deployment:** Single Docker container

## Quick Start

```bash
# Linux/Mac
./scripts/start.sh       # Build and run at http://localhost:8000

# Windows
./scripts/start.ps1
```

Default credentials: `user` / `password`

## Development

**Frontend** (`frontend/`)
```bash
npm run dev              # http://localhost:3000
npm run test:unit
npm run test:e2e
```

**Backend** (`backend/`)
```bash
uvicorn main:app --reload   # http://localhost:8000
pytest
```

**Environment:** copy `.env.example` to `.env` and set `OPENROUTER_API_KEY`.
