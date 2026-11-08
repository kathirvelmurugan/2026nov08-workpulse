# WorkPulse SDLC — Unified Software Development Lifecycle Platform

AI-powered development platform combining project management with autonomous code generation. Built on lessons from WorkPulse and the Automated Software Factory.

## Architecture

```
React Frontend (Vite + Tailwind)  ←→  Python Backend (Flask + SQLite)  ←→  Qwen Code CLI (AI agents)

Pipeline: architect → reviewer → backend → frontend → database → tests → qa
```

## Quick Start

```bash
# Backend
cd server
pip install flask flask-cors
python server.py

# Frontend (dev mode)
cd frontend
npm install
npm run dev

# Open http://localhost:5173
```

## Work Item Types

| Type | Pipeline | Example |
|---|---|---|
| `feature` | Full 7-phase | "Build CRM dashboard" |
| `bug` | Research → Fix → Test → QA | "Login fails on Safari" |
| `research` | Research only | "Evaluate GraphQL vs REST" |
| `maintenance` | Fix → Test | "Update dependencies" |

## API Endpoints

```
GET  /api/heartbeat
GET  /api/projects
POST /api/projects
GET  /api/work-items
POST /api/work-items
GET  /api/work-items/:id
POST /api/pipeline/:phase_id/run
GET  /api/runs
```

## Status

Alpha — backend complete, frontend in progress, Qwen agent integration ready.