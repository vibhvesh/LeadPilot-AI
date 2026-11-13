# CanberraAI multi-company authentication design

**MVP status:** Google sign-in, demo sign-in, approval, and per-module permissions are implemented. See the README. The multi-company Entra ID design below is not built yet.

**Status:** Approved architecture; multi-company Microsoft sign-in is not enabled yet.  
**Product:** CanberraAI Lead Generation System for TMS LLC  
**Repository:** LeadPilot-AI

## Decision

Support two sign-in providers for a multi-company SaaS deployment:

- Microsoft Entra ID (Microsoft 365 work/school accounts), using the multi-tenant `organizations` authority.
- Google OpenID Connect (Google Workspace and Google accounts), using Google's OIDC discovery metadata.

Both providers authenticate identity. CanberraAI remains the authority for company membership, approval, role assignment, and data access.

## Sign-in endpoints

- `GET /auth/microsoft/login`
- `GET /auth/microsoft/callback`
- `GET /auth/google/login`
- `GET /auth/google/callback`
- `POST /auth/logout`
- `GET /api/me`

Production redirect URI examples (must match provider console registrations exactly):

- `https://YOUR_CANBERRAAI_HOST/auth/microsoft/callback`
- `https://YOUR_CANBERRAAI_HOST/auth/google/callback`

Do not use localhost or plain HTTP redirect URIs in production. Local development may use provider-approved localhost redirect URIs.

## Protocol

Use server-side OpenID Connect Authorization Code Flow with PKCE, a cryptographically random state value, and OIDC nonce validation. Use a maintained OIDC library/provider adapter; do not hand-roll token validation or cryptography.

1. Browser requests a provider login endpoint.
2. Backend creates state, nonce and PKCE verifier/challenge, then redirects to the provider.
3. Provider authenticates the user (and performs MFA according to the user's organisation policy).
4. Provider redirects to the exact registered callback with a short-lived authorization code.
5. Backend validates state, exchanges the code server-to-server, validates signature, issuer, audience, expiry and nonce, and reads the identity claims.
6. Backend resolves the external identity to a CanberraAI user and company membership.
7. Only an active, approved membership receives an application session. New or unapproved users remain pending and see an access-pending page.
8. Backend issues a random opaque session identifier in a Secure, HttpOnly, SameSite=Lax cookie. Store session state server-side; rotate on login and revoke on logout.

Do not store provider passwords. Do not expose provider access/ID tokens to browser JavaScript. Do not request Microsoft Graph or Google API scopes unless a separately approved feature needs them.

## Multi-company identity and tenant isolation

Suggested relational entities:

- `companies`: company ID, display name, status, created timestamp.
- `company_domains`: normalized domain, company ID, verified flag, verification method/time. A domain must not be assigned to two active companies without an explicit supported shared-domain arrangement.
- `users`: internal user ID, display name, normalized contact email, status.
- `external_identities`: provider, issuer, provider subject, Microsoft tenant ID and object ID where present, internal user ID. Unique constraint on (provider, issuer, subject).
- `memberships`: company ID, user ID, role, approval status, team ID, created/approved by.
- `sessions`: hashed opaque session ID, user ID, active company ID, created/expiry/revoked timestamps.
- `audit_events`: actor, company, event, target, timestamp, safe metadata.

Use the provider's stable subject identifiers, not email, as the external identity key. For Microsoft, retain and validate the tenant ID (`tid`) and object ID (`oid`) where present; validate that the issuer corresponds to the tenant ID and the configured Microsoft metadata. A multitenant Microsoft app must handle tenant-specific issuer values correctly.

For Google, validate issuer, audience, expiry, signature, nonce, and `email_verified`. Treat `hd` as an organisation hint/claim to validate when Google Workspace-only access is required; do not treat a user-supplied email suffix as proof of domain ownership.

Email domains are used for company discovery/onboarding, not as the sole identity key or sufficient proof of company membership. Verify company domains (for example, DNS TXT challenge) before enabling automatic domain-based membership. Otherwise require an invitation or Super Admin approval.

Do not silently merge Microsoft and Google identities merely because their email strings match. Link a second provider only after the user has authenticated to the existing account, or after an explicit administrator-controlled verification process.

## Company onboarding and access policy

1. Super Admin creates a company record and invites its first Company Admin.
2. Company Admin verifies the company's email domain (DNS TXT challenge) or uses invitation-only onboarding.
3. Company Admin configures whether new users are invitation-only or may request access using a verified company domain.
4. A successful provider login without an approved membership creates/updates a pending access request, not an active account.
5. Company Admin approves membership and assigns a company-scoped role.
6. Super Admin can suspend a company, user, membership, domain, or session.

Recommended roles: Super Admin (platform-wide), Company Admin, Team Lead, Member. Every lead, note, feedback record, team, and query must be scoped by company ID. Never trust a company ID supplied by the browser without checking the active membership.

## Required security controls

- HTTPS in production; trusted proxy configuration and secure cookies.
- OIDC state, nonce, PKCE, exact redirect URI allowlists, and strict issuer/audience/signature/time validation.
- Secure secret storage; secrets only in server environment/secret manager, never in Git.
- Session rotation after login, idle/absolute expiry, logout revocation, and CSRF protection for state-changing cookie-authenticated requests.
- Rate limits on login/callback and access-request endpoints; generic error messages.
- Audit login success/failure, approvals, role changes, company switches, and revocations without logging tokens or secrets.
- Database constraints and automated tests for cross-company isolation.
- Default-deny authorization. The existing temporary `X-Admin-Key` gate is development-only and must be removed/replaced before enabling production login.
- Do not expose the current API publicly until authentication, authorization, HTTPS, migrations, and isolation tests are complete.

## Provider console setup

### Microsoft Entra ID

1. Register a Web application in Microsoft Entra admin center.
2. Set supported account types to **Accounts in any organizational directory** (multi-tenant; work/school accounts).
3. Add the exact HTTPS callback URI above.
4. Create a client secret for initial development or preferably use a certificate/managed secret mechanism in production.
5. Record Application (client) ID and Directory (tenant) configuration. Use the `organizations` authority for work/school tenants only.
6. Each customer's tenant may require admin consent according to its tenant policy and requested permissions. Request only `openid profile email` for sign-in unless a separately approved integration needs more.

### Google

1. Create/select a Google Cloud project and configure the OAuth consent screen / Google Auth Platform.
2. Create an OAuth client of type **Web application**.
3. Add the exact HTTPS callback URI above under Authorized redirect URIs.
4. Record the client ID and client secret.
5. Publish/verify the consent configuration as required for the intended external user audience. Request only `openid email profile`.

## Environment configuration

See `.env.example`. Provider secrets are optional until configured; the application must fail closed and hide/disable a provider button if its client ID/secret or public base URL is missing. Never put real secrets in the repository.

## Implementation sequence

1. Add OIDC provider adapters and login/callback/logout routes.
2. Add company, domain verification, user, external identity, membership, session, and audit models with Alembic migrations.
3. Replace the temporary admin-key dependency with session authentication and company-scoped RBAC.
4. Add company onboarding, invitation, approval, role management, and account linking.
5. Add provider callback, CSRF, session, and cross-company isolation tests.
6. Deploy behind HTTPS; configure both provider consoles and secrets; test with two separate Microsoft tenants and two Google Workspace organisations.

## Acceptance tests

- Users from two unrelated Microsoft Entra tenants can authenticate through the same CanberraAI application registration.
- Users from two unrelated Google Workspace organisations can authenticate.
- An authenticated but unapproved user cannot access company data.
- A user belonging to Company A cannot read, update, assign, or export Company B leads by changing request IDs or company IDs.
- Same email from two providers is not automatically merged.
- Expired, invalid-signature, wrong-audience, wrong-issuer, wrong-nonce, and state-mismatch callbacks are rejected.
- Logout revokes the CanberraAI session.
- Disabling a company or membership blocks subsequent requests.
