# LeadPilot AI — Version 2
Modular lead discovery and management platform for CanberraAI.

## Milestone 1: Foundation
This initial scaffold provides a React + TypeScript frontend shell, FastAPI backend, PostgreSQL, Redis, container definitions, and service health checks. Google OAuth, user approvals, and full RBAC are the next implementation slice.

## Run locally
1. Copy `.env.example` to `.env` and set strong secrets.
2. From this directory run `docker compose up --build`.
3. Frontend: http://localhost:5173
4. API health: http://localhost:8000/health
5. API readiness: http://localhost:8000/ready

Never commit `.env`, OAuth client secrets, or provider API keys.
