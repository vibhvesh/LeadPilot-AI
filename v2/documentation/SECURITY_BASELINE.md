# Security baseline

- Google OAuth is for identity only; application approval is enforced by the backend.
- The initial Super Admin email is configured through `SUPER_ADMIN_EMAIL`; do not trust a browser-supplied role or email.
- Sessions must use Secure, HttpOnly, SameSite cookies over HTTPS in production.
- Persist only hashes of opaque session tokens.
- Enforce permissions and team/record scope on every protected API request.
- Keep PostgreSQL and Redis on the private Docker network.
- Store production secrets outside Git and rotate any secret that may have been exposed.
- Add rate limiting to authentication and administrative endpoints before production.
- Audit approvals, role changes, exports, credential changes and destructive operations.
- Backups must be encrypted, retained under policy, and restore-tested.
