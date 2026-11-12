# Video OS — Client Intake & Information Gate

> 🇻🇳 Bản tiếng Việt: [README.vi.md](README.vi.md)

![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white)
![Next.js 16](https://img.shields.io/badge/Next.js-16-000000?logo=nextdotjs)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-17-4169E1?logo=postgresql&logoColor=white)
![License: MIT](https://img.shields.io/badge/license-MIT-green)

<!-- Add a screenshot or GIF, then uncomment: ![Demo](docs/images/intake-demo.gif) -->

A self-hosted web application for a video-ad studio. It turns the messy first step of a production — collecting what a client wants — into a structured, auditable workflow: **questionnaire → answers and evidence → confirmation → information folder → review and approval**.

The front end is a scroll-driven, 3D "cinema" experience (Next.js + three.js); the back end is a typed FastAPI service with strict role-based access, CSRF protection and a full audit trail.

## Highlights

- **Structured intake.** 51 versioned questions (16 core + 35 branch questions) covering deliverables, language, timeline, budget, rights and AI usage. Clients can fill everything in themselves, including uploads of images, video, audio and reference files.
- **Evidence, not guesses.** Source files are stored with SHA-256 checksums that are re-verified on use. Prefill extracts only explicitly marked answers (`CORE-02: ...`) from TXT/MD/DOCX/PDF; nothing is silently inferred and no LLM is called.
- **Review gate.** PM/Admin confirm answers, then approve, request changes or reject an immutable snapshot (canonical JSON + SHA-256). Editing after approval marks the snapshot historical and blocks hand-off.
- **Exports.** Information folder as ZIP (with checksummed manifest), JSON, DOCX and PDF; Excel export for the studio's working sheets.
- **Role-based access.** `ADMIN`, `PM`, `ACCOUNT`, `VIEWER`, enforced on the server and scoped per tenant.
- **Cinematic front end.** WebGL scenes with an aperture opening transition, 3D chapters, torn-paper sections and GPU-friendly motion.

## Architecture

```
 Browser ──HTTPS──▶ Next.js 16 (UI, security headers, /api rewrite)
                         │ same-origin /api/v1/*
                         ▼
                    FastAPI (auth, validation, review, export)
                    │                       │
                    ▼                       ▼
             PostgreSQL (SQLAlchemy,   Local file storage
             Alembic migrations)       (UUID names + checksums)
```

| Path | Purpose |
|---|---|
| `backend/` | FastAPI app, models, validation, parsing, review/snapshot/export, Alembic migrations |
| `frontend/` | Next.js / TypeScript UI, three.js scenes |
| `tests/` | Integration tests with isolated QA data |
| `scripts/` | Launcher (`manage.py`), bootstrap, verification helpers |
| `docs/` | Decisions, contracts, scope and verification evidence |
| `runtime/` | Local data, logs and files — **never committed** |
| `render.yaml` | One-click Render Blueprint (database + API + web) |
| `compose.yaml` | Local PostgreSQL for development |

## Getting started

Requirements: Python 3.11+, Node.js compatible with Next.js 16, npm, Docker Desktop (for PostgreSQL).

```powershell
python scripts/manage.py setup      # venv, locked dependencies, PostgreSQL, migrations, owner account
python scripts/manage.py start      # backend :8100, frontend :3100
```

Open <http://127.0.0.1:3100>. The owner credentials are generated at bootstrap and written to a local, git-ignored file; there are no default accounts or passwords in the source. On Windows, `CAP-NHAT-VA-CHAY.bat` rebuilds and starts the app, and `DUNG-UNG-DUNG.bat` stops it.

### Configuration

Copy `.env.example` to `.env` and set real values. Never commit `.env`.

| Variable | Purpose | Default |
|---|---|---|
| `DATABASE_URL` | PostgreSQL connection string | — (required) |
| `STORAGE_DIR` | Where uploaded source files live | `./runtime/storage` |
| `APP_ENV` | `production` turns on secure cookies, HSTS and hides API docs | `development` |
| `COOKIE_SECURE` | Force the `Secure` flag on the session cookie | `true` in production |
| `TRUST_PROXY` | Trust `X-Forwarded-For` (only behind a proxy you control) | `false` |
| `PDF_FONT_PATH` | Unicode font for PDF export | system default |
| `BACKEND_URL` | (frontend) Address of the API for the `/api` proxy | `http://127.0.0.1:8100` |

### Tests

```powershell
.\.venv\Scripts\python.exe -m pytest
cd frontend; npm run typecheck; npm run build
```

Pytest uses an isolated temporary SQLite database; it never touches real data.

## Deployment

`render.yaml` provisions PostgreSQL, the API and the web app in one step. Step-by-step instructions, the pre-publication checklist and post-deploy checks are in [docs/DEPLOY.md](docs/DEPLOY.md).

## Security

Security is part of the design, not an afterthought. Summary (details in [SECURITY.md](SECURITY.md)):

- Passwords hashed with PBKDF2-HMAC-SHA256 (600 000 rounds, per-user salt); verification is constant-time and unknown usernames cost the same time as known ones.
- Server-side sessions; cookies are `HttpOnly`, `SameSite=Strict` and `Secure` in production; every state-changing request requires a CSRF token.
- Login throttling per IP + username; the public "start intake" endpoint is rate-limited and uploads are capped per client link.
- Strict per-tenant data isolation and server-side authorization on every route.
- Upload validation by extension, size limit per media type and file-signature check; stored under random UUID names and re-verified by checksum.
- Security headers on both layers (nosniff, frame denial, referrer and permissions policy, HSTS in production); Content-Security-Policy is shipped in report-only mode first.
- Append-only audit trail; passwords never logged.

## Status and scope

Stage 01 (information gate) is implemented. Later stages (generation, rendering, delivery) are intentionally out of scope. File storage is the local filesystem; for internet deployment use HTTPS, a managed PostgreSQL, off-box backups and a shared rate limiter.

## Third-party assets

The scroll-driven 3D presentation was built as a study of a published web experience. Some bundled 3D scenes and textures under `frontend/public/renaissance/` originate from a third party and are **not** covered by this project's licence. Replace them with your own assets before redistributing or deploying publicly; see [NOTICE.md](NOTICE.md).

## License

Source code: [MIT](LICENSE). Third-party assets are excluded (see above).
