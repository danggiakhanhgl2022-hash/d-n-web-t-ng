# Security Policy

## Reporting a vulnerability

Please do not open a public issue for security problems. Email the maintainer privately with a description, steps to reproduce and the affected version. You will get an acknowledgement and a fix timeline.

## Controls in place

| Area | Control |
|---|---|
| Passwords | PBKDF2-HMAC-SHA256, 600 000 rounds, per-user random salt, constant-time compare; minimum 12 characters; unknown usernames are timed like known ones |
| Sessions | Random 256-bit token, only its SHA-256 stored server-side; 12 h expiry; `HttpOnly`, `SameSite=Strict`, `Secure` in production |
| CSRF | `X-CSRF-Token` required on every authenticated state-changing request |
| Brute force | 8 failed logins per 5 min per IP + username; public intake start limited per IP and globally |
| Authorization | Role checks (`ADMIN`, `PM`, `ACCOUNT`, `VIEWER`) and tenant scoping on the server for every route |
| Client links | Unguessable tokens, expiry, revocation, per-link file and size caps |
| Uploads | Extension allow-list, per-type size limits, file-signature check, random UUID storage names, SHA-256 re-verified on download, no remote URL fetching |
| Transport | HSTS in production (both layers); `APP_ENV=production` forces secure cookies |
| Headers | `nosniff`, frame denial, referrer and permissions policy, COOP; API responses `Cache-Control: no-store`; API docs hidden in production |
| CSP | Shipped as `Content-Security-Policy-Report-Only` because the 3D scenes need workers, WebAssembly and `blob:`. Review violations, tighten (nonces instead of `unsafe-inline`), then switch to enforcing |
| Audit | Append-only audit events; passwords are never logged |
| Secrets | `.env`, local credentials and runtime data are git-ignored; `.env.example` holds placeholders only |

## Before deploying to the internet

1. Serve only over HTTPS; set `APP_ENV=production`, `COOKIE_SECURE=true`; set `TRUST_PROXY=true` only behind a proxy you control.
2. Use a managed PostgreSQL with a strong password and network restrictions; keep backups off the server.
3. Put upload storage on a volume that is not web-served; consider malware scanning for uploads.
4. Replace the in-memory rate limiter with a shared one (Redis or the proxy/WAF) if you run more than one instance.
5. Turn the CSP from report-only to enforcing after reviewing reports.
6. Run `pip audit` / `npm audit` regularly and keep Next.js, FastAPI and dependencies updated.
7. Rotate any credential that was ever shared in chat, email or screenshots.
