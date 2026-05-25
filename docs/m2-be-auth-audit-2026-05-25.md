# BE Auth-Coverage Audit — M2 Side-Effect
**Date:** 2026-05-25  
**Trigger:** M1 cleanup (d6744e3) added email-verify gate to `/api/writing/*`; the BE endpoint inventory (0975b1d) did not check auth-dependency coverage. This ticket fills that gap.  
**Scope:** All FastAPI routers, static analysis only. No prod hits.

---

## Auth Dependency Definitions

| Dependency | Behaviour |
|---|---|
| `get_current_user` | Resolves token (cookie → Bearer header) → loads User → **401** if missing/bad token → **403 `email_not_verified`** if `email_verified_at IS NULL`. Standard verified-user gate. |
| `get_current_user_allow_unverified` | Same token resolution + DB load → **401** on bad token, but **no email-verified check**. Used by /logout, /me, /verify-email/resend. |
| `get_current_user_optional` | Same as allow_unverified but returns `None` instead of raising on any failure. No email-verified check. |
| `require_admin` | Wraps `get_current_user` (verified user first), then checks `user.is_admin` → **403** if not admin. |
| `diagnostic_quota_required` | Wraps `get_current_user` (verified user first), then checks per-user-per-UTC-day counter by tier (free=5 / sub=30 / sprint=60 / premium=unlimited) → **429** when over quota. |
| `auth_rate_limit("x")` | Per-IP rate limiter. Applied as router-level `dependencies=[]` on register/login/etc. No user identity check — IP throttling only. |

---

## Endpoint Catalog

| Path | Method | Router File | Auth Dep | Intentional / Gap | Notes |
|---|---|---|---|---|---|
| `/health` | GET | `main.py` | none | intentional | DO App Platform health probe. No DB touch by design. |
| `/tts_audio/{filename}` | GET | `main.py` | `get_current_user` | intentional | TTS cache files keyed by SHA-256 of text+voice+model; any verified user may fetch any cached file. Filename guard prevents path traversal. |
| `/api/auth/register` | POST | `auth.py` | none + `auth_rate_limit('register')` (IP only) | intentional | Public registration. hCaptcha enforced when `HCAPTCHA_SECRET` set. Issues tokens so unverified user can reach /verify-email/resend. |
| `/api/auth/login` | POST | `auth.py` | none + `auth_rate_limit('login')` (IP only) | intentional | Public login. Returns access + refresh tokens via cookies. |
| `/api/auth/refresh` | POST | `auth.py` | none (reads refresh_token cookie manually) | intentional | Must be unauthenticated — this is how you get a new access token when old one expired. Token verified internally. |
| `/api/auth/logout` | POST | `auth.py` | `get_current_user_allow_unverified` | intentional | Intentionally allow_unverified so unverified users can log out. Revokes refresh token + clears cookies. |
| `/api/auth/me` | GET | `auth.py` | `get_current_user_allow_unverified` | intentional | FE uses this to read `email_verified` state and show verification banner before verification completes. |
| `/api/auth/verify-email` | POST | `auth.py` | none | intentional | User clicks link in email before they have a valid session. Token itself is the credential. |
| `/api/auth/verify-email/resend` | POST | `auth.py` | `get_current_user_allow_unverified` + `auth_rate_limit('verify_email_resend')` | intentional | Requires authenticated session so resend can't be abused as a free email-enumeration probe. |
| `/api/auth/password-reset/request` | POST | `auth.py` | none + `auth_rate_limit('password_reset_request')` (IP only) | intentional | Public: user is locked out. Anti-enumeration: always returns 200. |
| `/api/auth/password-reset/confirm` | POST | `auth.py` | none | intentional (see GAP-3 note) | Consumes one-time reset token (token is the credential). No rate limit on confirm — see GAP-3. |
| `/api/admin/dashboard` | GET | `admin.py` | `require_admin` | intentional | Admin only. |
| `/api/admin/users` | GET | `admin.py` | `require_admin` | intentional | Admin only. |
| `/api/admin/themes` | GET | `admin.py` | none | **GAP** | Under `/api/admin/` prefix but zero auth. Returns all active theme names + topic counts. See GAP-1. |
| `/api/admin/topics` | GET | `admin.py` | none | **GAP** | Under `/api/admin/` prefix but zero auth. Returns full topic catalog: id, title, theme, sous_theme. See GAP-1. |
| `/api/admin/topics` | POST | `admin.py` | `require_admin` | intentional | Admin only. Write path correctly guarded. |
| `/api/admin/topics/{topic_id}` | DELETE | `admin.py` | `require_admin` | intentional | Admin only. Delete path correctly guarded. |
| `/api/admin/random-topic` | GET | `admin.py` | none | **GAP** | Under `/api/admin/` prefix but zero auth. Returns one random active topic. See GAP-1. |
| `/api/analytics/dashboard` | GET | `analytics.py` | `get_current_user` | intentional | Scoped to `user.id`. |
| `/api/analytics/progress` | GET | `analytics.py` | `get_current_user` | intentional | Scoped to `user.id`. |
| `/api/analytics/recurring` | GET | `analytics.py` | `get_current_user` | intentional | Scoped to `user.id`. |
| `/api/analytics/coverage` | GET | `analytics.py` | `get_current_user` | intentional | Scoped to `user.id`. |
| `/api/analytics/pass` | GET | `analytics.py` | `get_current_user` | intentional | Scoped to `user.id`. |
| `/api/recordings/upload` | POST | `recordings.py` | `diagnostic_quota_required` | intentional | Verified user + daily quota check. |
| `/api/recordings/transcribe` | POST | `recordings.py` | `get_current_user` | intentional | Step 1 of 2-step flow. Not quota-gated per F-311 Q2c. |
| `/api/recordings/{recording_id}/confirm-transcript` | POST | `recordings.py` | `get_current_user` | intentional (by-design question — see GAP-2) | Triggers full Sonnet analysis but not quota-gated; per F-311 Q2c only /upload and /conversations/end are quota points. |
| `/api/recordings/tache3-topics` | GET | `recordings.py` | `get_current_user` | intentional | L'École gate applied internally. |
| `/api/recordings` | GET | `recordings.py` | `get_current_user` | intentional | Lean list scoped to `user.id`. |
| `/api/recordings/history` | GET | `recordings.py` | `get_current_user` | intentional | Scoped to `user.id`. |
| `/api/recordings/{recording_id}/detected-modules` | GET | `recordings.py` | `get_current_user` | intentional | Ownership check: recording_id AND user_id. |
| `/api/recordings/{recording_id}` | GET | `recordings.py` | `get_current_user` | intentional | Ownership check: recording_id AND user_id. |
| `/api/oral/generate-structure` | POST | `oral.py` | `get_current_user` | intentional | Not quota-gated (argument scaffold, not full diagnostic per F-311 Q2c). |
| `/api/conversations/scenarios` | GET | `conversations.py` | `get_current_user` | intentional | L'École gate applied internally. |
| `/api/conversations/start` | POST | `conversations.py` | `get_current_user` | intentional | Difficulty gate applied internally. |
| `/api/conversations/{conversation_id}` | GET | `conversations.py` | `get_current_user` | intentional | Ownership check via `_require_owner`. |
| `/api/conversations/{conversation_id}/turn` | POST | `conversations.py` | `get_current_user` | intentional | Mid-session turn, not quota-gated per F-311 Q2c. Ownership via `_require_owner`. |
| `/api/conversations/{conversation_id}/turn/{turn_number}/supersede` | POST | `conversations.py` | `get_current_user` | intentional | F-062.3 re-record flow. Ownership via `_require_owner`. |
| `/api/conversations/{conversation_id}/end` | POST | `conversations.py` | `diagnostic_quota_required` | intentional | Verified user + daily quota check. Analysis trigger for Tâche 1/2. |
| `/api/writing/prompts` | GET | `writing.py` | `get_current_user` | intentional | Fixed in M1 cleanup d6744e3 (was unguarded before). |
| `/api/writing/submit` | POST | `writing.py` | `diagnostic_quota_required` | intentional | Verified user + daily quota check. |
| `/api/writing/jobs/{job_id}` | GET | `writing.py` | `get_current_user` | intentional | Cross-user check: `job.user_id != user.id` raises 403 (unless admin). |
| `/api/writing/history` | GET | `writing.py` | `get_current_user` | intentional | Paramless alias, delegates to /history/{user_id} with `user.id`. |
| `/api/writing/history/{user_id}` | GET | `writing.py` | `get_current_user` | intentional | Cross-user check: 403 if `user_id != user.id` and not admin. |
| `/api/writing/submission/{submission_id}` | GET | `writing.py` | `get_current_user` | intentional | Ownership check: 403 if `sub.user_id != user.id` and not admin. |
| `/api/patterns/labels` | GET | `patterns.py` | none | intentional | Docstring: "static reference data, no auth required." Non-sensitive educational content fetched once on page load. |
| `/api/ecole/lessons` | GET | `ecole.py` | `get_current_user` | intentional | Returns per-user progress state. |
| `/api/ecole/progress` | GET | `ecole.py` | `get_current_user` | intentional | Lazily bootstraps progress rows. |
| `/api/ecole/lessons/{lesson_id}` | GET | `ecole.py` | `get_current_user` | intentional | Locked lesson gate enforced internally. |
| `/api/ecole/lessons/{lesson_id}/start` | POST | `ecole.py` | `get_current_user` | intentional | Locked lesson gate enforced internally. |
| `/api/ecole/lessons/{lesson_id}/quiz` | GET | `ecole.py` | `get_current_user` | intentional | Locked lesson gate enforced internally. |
| `/api/ecole/lessons/{lesson_id}/quiz/submit` | POST | `ecole.py` | `get_current_user` | intentional | Locked lesson gate enforced internally. Scores + unlocks next lesson. |
| `/api/users/me` | GET | `users.py` | `get_current_user` | intentional | Note: unlike `/api/auth/me` (allow_unverified), this uses verified-only gate. |
| `/api/users/me/level` | GET | `users.py` | `get_current_user` | intentional | P-201 self-reported + assigned level state. |
| `/api/users/onboarding` | POST | `users.py` | `get_current_user` | intentional | Deprecated. Sends `Deprecation` header. |
| `/api/users/me/recurring_modules` | GET | `users.py` | `get_current_user` | intentional | Scoped to `user.id`. |
| `/api/modules` | GET | `modules.py` | none | intentional | Docstring: "Public-read endpoints for the authored module library. No auth gate in V1 (modules are product-educational content, not per-user data)." |
| `/api/modules/{module_id}` | GET | `modules.py` | `get_current_user_optional` | intentional | Optional auth. Unauthenticated: module content + `user_context=null`. Authenticated: populates `user_context` with per-user detection history. Future public-glossary path (F-080d.y). |
| `/onboarding/questions` | GET | `onboarding.py` | none | intentional | Docstring: "Public — pre-auth flows render the questionnaire before signup completes." Static question copy, no user data. |
| `/onboarding/submit` | POST | `onboarding.py` | `get_current_user` | intentional | Verified user. Persists 11 onboarding answers + creates UserPathEnrollment. |
| `/api/diagnostic/state` | GET | `diagnostic.py` | `get_current_user` | intentional | Read-only diagnostic state machine (P-221). |
| `/api/users/me/today` | GET | `today.py` | `get_current_user` | intentional | P-240 today's recommended action. |
| `/api/clusters/{slug}` | GET | `clusters.py` | `get_current_user` | intentional | Curriculum content for a cluster. |
| `/api/users/me/clusters/{slug}` | GET | `clusters.py` | `get_current_user` | intentional | Per-user cluster state + history. |
| `/api/stripe/webhook` | POST | `stripe_webhook.py` | none | intentional | Stripe sends this — must be public. Auth is HMAC Stripe-Signature header verification. |
| `/api/vocab/topics` | GET | `vocab.py` | `get_current_user` | intentional | All topics with per-row locked flag. |
| `/api/vocab/topics/{slug}` | GET | `vocab.py` | `get_current_user` | intentional | Runtime tier gate for exam_tagged_* topics. |
| `/api/vocab/topics/{slug}/chunks` | GET | `vocab.py` | `get_current_user` | intentional | Runtime tier gate. Third-party rows excluded. |
| `/api/audio/upload` | POST | `audio.py` | `get_current_user` | intentional | F-050 Tâche 2 PTT upload+STT. Mid-session utility, not quota-gated per F-311 Q2c. |

---

## Summary Totals

| Auth State | Count |
|---|---|
| `none` — intentional public | 8 |
| `none` — **GAP** | **3** |
| `get_current_user_allow_unverified` | 3 |
| `get_current_user_optional` | 1 |
| `get_current_user` | 33 |
| `require_admin` | 3 |
| `diagnostic_quota_required` | 3 |
| **Total endpoints** | **54** |

**Confirmed auth gaps: 3** (all in `admin.py`, all GET read-only)  
**By-design questions flagged: 2** (GAP-2 quota skip, GAP-3 rate-limit omission)

---

## Gaps — Severity-Ranked

### GAP-1 — Three `/api/admin/` GET endpoints lack auth  
**Severity: MEDIUM (admin-read, proprietary content exposure)**  
**File:** `app/routers/admin.py`

The GET read paths under `/api/admin/` carry no auth dependency while the write paths on the same router are correctly gated with `require_admin`. This is an incomplete wiring — not an intentional decision.

| Method | Path | What leaks |
|---|---|---|
| GET | `/api/admin/themes` | All active theme names + topic counts |
| GET | `/api/admin/topics` | Full topic catalog: id, title, theme, sous_theme |
| GET | `/api/admin/random-topic` | One random active topic |

The topic catalog is proprietary content authored by Chadi. While not cryptographically sensitive, exposing it unauthenticated under a path named `/admin/` is a clear omission.

**Fix:** Add `Depends(require_admin)` to each of the three handlers, or add a router-level `dependencies=[Depends(require_admin)]` to the `APIRouter` declaration and selectively override the two endpoints that also need `Depends(get_db)`.

---

### GAP-2 — `/api/recordings/{id}/confirm-transcript` triggers Sonnet analysis without quota gate  
**Severity: LOW (by-design question, not a security breach)**  
**File:** `app/routers/recordings.py`

`/recordings/upload` is quota-gated via `diagnostic_quota_required`. `/recordings/{id}/confirm-transcript` uses only `get_current_user`. Both paths trigger full Sonnet-tier Claude analysis. F-311 Q2c lists the quota gates as `/upload`, `/conversations/end`, and `/writing/submit` — `/confirm-transcript` is not listed, suggesting this is intentional (quota counted at the upload step on the one-shot path only).

However: a verified user who always uses the 2-step transcribe → confirm flow bypasses the daily quota entirely. This may be an unspoken assumption rather than a deliberate decision. Worth a documented explicit choice before the quota system is tightened.

---

### GAP-3 — `/api/auth/password-reset/confirm` has no rate limit  
**Severity: LOW (computationally infeasible to exploit, but defence-in-depth missing)**  
**File:** `app/routers/auth.py`

`/password-reset/request` has `auth_rate_limit('password_reset_request')`. `/password-reset/confirm` has nothing — no IP rate limit, no attempt counter per token. The token is 32 random bytes from `secrets.token_bytes`, making brute-force computationally infeasible in practice, and the 1-hour TTL further bounds the window. Risk is very low but the asymmetry (request is limited, confirm is not) is worth correcting for defence-in-depth.

---

## Top 3 Fixes by Severity

1. **`app/routers/admin.py`** — Add `require_admin` to GET `/api/admin/themes`, `/api/admin/topics`, `/api/admin/random-topic`. Three-line fix. Severity: MEDIUM.
2. **`app/routers/recordings.py`** — Explicitly document (or gate) the confirm-transcript quota skip. Either add `diagnostic_quota_required` or add a code comment citing the F-311 Q2c decision. Severity: LOW.
3. **`app/routers/auth.py`** — Add `auth_rate_limit('password_reset_confirm')` to the confirm handler. Severity: LOW.
