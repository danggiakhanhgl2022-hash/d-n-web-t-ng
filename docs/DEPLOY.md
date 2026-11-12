# Deploying online

Target layout (all on [Render](https://render.com) via `render.yaml`, one Blueprint):

```
Browser ──HTTPS──▶ video-os-web (Next.js)  ──/api/v1 proxy──▶ video-os-api (FastAPI) ──▶ PostgreSQL
                                                                   └── persistent disk (/var/data/storage)
```

The browser only ever talks to one origin, so the session cookie stays `SameSite=Strict` and no CORS configuration is needed.

## 1. Before you publish the repository

- [ ] Replace or remove the third-party assets in `frontend/public/renaissance/` (see [NOTICE.md](../NOTICE.md)).
- [ ] Confirm no secrets are tracked: `git ls-files | grep -E "\.env($|\.)|TAI-KHOAN|\.db$"` must list only `.env.example`.
- [ ] Rotate any password or token that was ever pasted into a chat, file or screenshot.
- [ ] Keep the repository **private** until the items above are done.

## 2. Create the stack

1. Push the repository to GitHub.
2. Render → **New → Blueprint** → select the repository. Render creates the database, `video-os-api` and `video-os-web` from `render.yaml`.
3. Wait for both services to be live. `video-os-api` runs `alembic upgrade head` on every start.

Notes on cost and storage: the persistent disk and `starter` plans are paid. Without a disk, uploaded files are lost on every redeploy, so do not run the API on a free plan with real client data.

## 3. Create the owner account

Open the `video-os-api` service → **Shell**, then:

```bash
cd backend && python -m app.bootstrap --username <owner> --display-name "<name>"
```

You are prompted for the password (12+ characters). There are no default accounts.

## 4. Environment variables

| Service | Variable | Value |
|---|---|---|
| api | `APP_ENV` | `production` (secure cookies, HSTS, API docs hidden) |
| api | `COOKIE_SECURE` | `true` |
| api | `TRUST_PROXY` | `true` (Render's proxy sets `X-Forwarded-For`) |
| api | `DATABASE_URL` | injected from the database; `postgres://` URLs are normalised automatically |
| api | `STORAGE_DIR` | `/var/data/storage` (on the persistent disk) |
| web | `BACKEND_URL` | injected from `video-os-api`; set manually to the API's `https://…` URL on other hosts |

## 5. Post-deploy checklist

- [ ] `https://<web>/` loads; `https://<api>/docs` returns 404 (docs hidden in production).
- [ ] Sign in, create a client, open its public link in a private window, upload a file.
- [ ] `curl -sI https://<web>/ | grep -i -E "strict-transport|content-security|x-frame"` shows the headers.
- [ ] Watch the browser console for CSP report-only violations for a few days, then switch `Content-Security-Policy-Report-Only` to `Content-Security-Policy` in `frontend/next.config.ts`.
- [ ] Enable database backups and test a restore.
- [ ] Add a custom domain and keep the default `*.onrender.com` host out of public links.

## Alternatives

- **Vercel (web) + Render/Railway/Fly (API):** works, but Vercel rewrites to an external API have request-size limits that can break large video uploads. Prefer hosting the web service next to the API, or upload through the API's own domain.
- **Single VPS:** `docker compose` for PostgreSQL, `uvicorn` and `next start` behind Caddy or nginx with automatic HTTPS. Set the same environment variables.
