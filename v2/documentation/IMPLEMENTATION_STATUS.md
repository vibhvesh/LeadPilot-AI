# Milestone 1 implementation status

## Included in initial scaffold
- React + TypeScript + Vite frontend shell
- FastAPI application entry point
- PostgreSQL and Redis Docker services
- API health and dependency readiness endpoints
- Environment-based configuration
- Initial container definitions

## Still required before production
- Google OAuth login and callback
- Secure server-side sessions and cookie policy
- Pending-user registration and approval queue
- Super Admin bootstrap and recovery procedure
- Role and permission schema and APIs
- Team/data-level authorisation
- Audit event persistence
- Automated tests
- HTTPS reverse proxy, backups, monitoring and deployment hardening

Do not expose this scaffold as a production service until authentication and authorisation are implemented and tested.
