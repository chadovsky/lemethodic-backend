# DEPLOY.md — production runbook

Manual provisioning sequence for the FluentPath backend (F-078). Run once at first deploy. Subsequent deploys are automatic — push to `master` and App Platform builds + ships.

---

## Prerequisites

- DO account with billing enabled.
- `doctl` installed and authenticated (`doctl auth init`) — optional but useful.
- GitHub repo `chadovsky/fluentpath-backend` exists, master branch is the deploy branch.
- Local dev verified: F-077 fixtures + F-075a/F-075b/F-083 harnesses pass.

---

## Step 1 — Create the DO Spaces bucket

DO console → **Spaces Object Storage** → **Create a Spaces Bucket**.

- **Region:** `Frankfurt (fra1)` (closest to Morocco).
- **Bucket name:** `fluentpath-storage` (must be globally unique within the region; pick an alternative if taken and update `.do/app.yaml` + production env to match).
- **File listing:** Restricted (default).
- **CDN:** Disabled (not needed for soft beta).

---

## Step 2 — Generate Spaces access keys

DO console → **API** → **Spaces Object Storage Keys** → **Generate New Key**.

- Name: `fluentpath-backend`.
- Copy the **Access Key** and **Secret** immediately — the secret is shown only once.
- These map to `DO_SPACES_KEY` and `DO_SPACES_SECRET` in App Platform.

---

## Step 3 — Create the App

Pick one:

**Via doctl:**
```bash
doctl apps create --spec .do/app.yaml
```

**Via console:**
1. **Apps** → **Create App** → **GitHub** source.
2. Select `chadovsky/fluentpath-backend`, branch `master`.
3. App Platform parses `.do/app.yaml` automatically. Confirm the detected service + database, click **Next**.

The first deploy provisions the managed PostgreSQL cluster (~3–5 minutes), builds the Python service (~2–3 minutes), runs `alembic upgrade head` against the empty database, then starts uvicorn. Total: 5–10 minutes.

---

## Step 4 — Set the SECRET-typed env vars

DO console → **App** → **Settings** → **App-Level Environment Variables**. The `.do/app.yaml` declared these as `type: SECRET` with no value — fill them in now:

| Key | Source |
|---|---|
| `SECRET_KEY` | `python -c "import secrets; print(secrets.token_urlsafe(64))"` |
| `ANTHROPIC_API_KEY` | https://console.anthropic.com/ |
| `OPENAI_API_KEY` | https://platform.openai.com/api-keys |
| `ASSEMBLYAI_API_KEY` | https://www.assemblyai.com/dashboard |
| `DO_SPACES_KEY` | from Step 2 |
| `DO_SPACES_SECRET` | from Step 2 |

Save → App Platform redeploys automatically.

`DATABASE_URL` is auto-injected (template `${db.DATABASE_URL}` in the spec). Don't set it manually.

`FRONTEND_ORIGIN` stays empty until F-079 ships and the Vercel URL is known.

---

## Step 5 — Verify the deploy

After the redeploy from Step 4 finishes (App Platform → **Activity** tab → green "Deployed"):

1. **Health check:** `curl https://<app-url>/health` → `{"status":"ok"}`.
2. **Migrations applied:** App Platform → **Logs** → look for `INFO  [alembic.runtime.migration] Running upgrade  -> 57c313935953, initial schema`.
3. **Register a test user:**
   ```bash
   curl -X POST https://<app-url>/api/auth/register \
     -H "Content-Type: application/json" \
     -d '{"email":"prod-smoketest@example.com","password":"smoketest1234","full_name":"Smoke Test"}'
   ```
   Expect `{"access_token":"...","user":{...}}`.
4. **Login round-trip:** same payload to `/api/auth/login` → expect new token.
5. **Upload a small test audio:**
   ```bash
   curl -X POST https://<app-url>/api/recordings/upload \
     -H "Authorization: Bearer $TOKEN" \
     -F "audio=@/path/to/short.webm" \
     -F "tache_mode=tache_3" \
     -F "duration_seconds=5"
   ```
   The recording row's `audio_path` will be a storage key like `uploads/<uuid>.webm`.
6. **Verify in Spaces:** DO console → **Spaces** → `fluentpath-storage` → confirm the new object appears under the `uploads/` prefix.
7. **Diagnostic returns:** the response body from step 5 includes the analysis payload — confirm it's structurally complete (couches scores, narrative summary if applicable).

If any step fails, App Platform → **Logs** → drill down. Common failure modes:
- Migration not applied → check `ALEMBIC` env section; the `run_command` order matters.
- 500 on register → DB binding wrong or `DATABASE_URL` empty (template syntax mismatch).
- Upload 500 → Spaces creds wrong (key, secret, or region) — boto3 will surface `SignatureDoesNotMatch` or `InvalidAccessKeyId` in logs.

---

## Step 6 — Hand off to F-079

Once `/health` is green and the smoke test passes, F-079 (frontend Vercel deploy) becomes implementable. Capture:

- **Backend production URL** (the App Platform–assigned `<app-id>.ondigitalocean.app` or the eventual custom domain).
- F-079 sets this in the frontend's `NEXT_PUBLIC_API_URL`.
- F-079 also updates `FRONTEND_ORIGIN` in App Platform with the Vercel URL so CORS lets it through.

---

## Rollback

App Platform → **Activity** → pick a prior green deploy → **Rollback**. Database stays put (Alembic's downgrade not run). If a migration is the problem, write a new migration that reverses the change and ship it forward; don't downgrade in place.

For storage: Spaces objects from a bad deploy are not auto-cleaned. They're cheap and accumulate harmlessly until F-078.x post-launch covers lifecycle policies.
