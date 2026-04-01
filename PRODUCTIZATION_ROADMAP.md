# PRODUCTIZATION_ROADMAP.md — Jarvis Max
_Written: 2026-04-01 — Post backend-freeze (Cycles 8–14)_

This document defines the exact next steps to go from backend-frozen to a shippable product.
Backend is NOT touched. Everything here is product layer, external validation, and go-to-market.

---

## What the backend can support today

See `RELEASE_READINESS.md` — Backend Kernel Assessment section for the full table.
Short version:

- **Proven E2E**: submit goal → multi-agent execution → structured result
- **Auth**: JWT + admin password + API token
- **Persistence**: missions survive restart (SQLite write-through)
- **Model cost control**: evidence-driven model selection + A/B auto-trigger at 3 samples
- **Human oversight**: approval gate + outbound webhook to n8n/Zapier/Slack
- **Mobile**: Flutter app on canonical v3 API
- **CI**: 37 unit tests on every push; integration tests secrets-gated

---

## TRACK 1 — External validation (parallel with Track 2, week 1–2)

These are the three remaining backend blockers that require real environment, not code.

### 1.1 Docker live boot proof (priority: CRITICAL)
**Command (ready to run on any machine with Docker):**
```bash
export ANTHROPIC_API_KEY=sk-ant-...   # or OPENROUTER_API_KEY
export JARVIS_ADMIN_PASSWORD=mypassword
export JARVIS_SECRET_KEY=$(openssl rand -hex 32)
docker compose -f docker-compose.test.yml up --build -d
JARVIS_ADMIN_PASSWORD=mypassword bash scripts/verify_boot.sh
# Expected: "BOOT VERIFICATION PASSED" within 90s
```
**Success criteria**: `verify_boot.sh` exits 0. Logs `mission_completed` event.
**Owner**: needs Docker daemon (not available in dev env).

### 1.2 Mobile device smoke test
**Pre-requisites**: Android/iOS device or emulator + running Jarvis server (local or VPS).
**Steps**:
1. Build Flutter app: `cd jarvismax_app && flutter build apk --debug`
2. Point `baseUrl` in `api_service.dart` to server IP
3. Submit a mission from the app
4. Verify mission reaches `COMPLETED` in the app UI
5. Test approve/reject flow from app (uses v2 path — still valid)

**Success criteria**: Mission submitted from mobile → `COMPLETED` state shown in app.

### 1.3 Integration test suite pass
```bash
# Against Docker stack (after 1.1 passes):
pytest --run-infra-tests -m integration -v
```
Expected failures to classify and fix: unknown until run.
Time estimate: 1–2 days of classification + fixes.

---

## TRACK 2 — First product slice (start week 1)

**Product: "AI Mission Runner" — the minimal viable product the backend already supports.**

### 2.1 Define the one use case (day 1–2)
Pick ONE of these to ship first:

| Option | What it does | Effort to add |
|--------|-------------|---------------|
| A. Internal ops automation | Submit a goal → agents research + produce a structured report | Zero (already works) |
| B. AI writing assistant | Submit a topic → agents produce a document | Zero (already works) |
| C. Code review assistant | Submit a PR diff → agents analyze + produce recommendations | Small (prompt tuning) |

**Recommendation**: Option A or B. No new code needed. Just a clean UI.

### 2.2 Minimal frontend (week 1–2)
The backend is fully API-driven. A minimal frontend needs:

- Login screen (POST `/api/auth/token` with admin password)
- Mission submit form (POST `/api/v3/missions` with `{"goal": "..."}`)
- Mission list (GET `/api/v3/missions`)
- Mission detail with result (GET `/api/v3/missions/{id}`)
- Approval action buttons (POST `/api/v3/missions/{id}/approve|reject`)

**Tech options** (backend-agnostic):
- Flutter Web (reuse existing Flutter app code) — fastest if Flutter skills exist
- React/Next.js — standard SaaS frontend, 3–5 days for MVP
- Streamlit — internal tool in 1 day (no auth needed for internal use)

### 2.3 Deployment target (week 2)
The backend is Docker-ready. Pick one:

| Target | Effort | Cost |
|--------|--------|------|
| VPS (Hetzner/DigitalOcean) | 1–2h setup | ~€5/month |
| Railway / Render | 30min, zero-config | ~€10–20/month |
| Self-hosted | Already have server | 0 |

**Minimum env vars needed for production**:
```bash
ANTHROPIC_API_KEY=sk-ant-...    # or OPENROUTER_API_KEY
JARVIS_SECRET_KEY=$(openssl rand -hex 32)
JARVIS_ADMIN_PASSWORD=<strong_password>
JARVIS_PRODUCTION=1             # enforces secret validation, disables SI
```

---

## TRACK 3 — Growth features (week 3+, after MVP ships)

These unlock monetization and scale. Do NOT build before MVP is proven.

### 3.1 Multi-user auth
Current: single admin password.
Add: user table, per-user JWT, role-based mission visibility.
Effort: 2–3 days.

### 3.2 Webhook integrations
Current: approval webhook to n8n/Zapier is already wired.
Add: mission completion webhook (POST result to external URL).
Effort: 1 day (same pattern as approval_queue._fire_approval_webhook).

### 3.3 Persistent agent memory per user
Current: Qdrant vector memory per-session.
Add: user-scoped memory namespace (filter by `user_id` in Qdrant queries).
Effort: 2–3 days.

### 3.4 Scheduled missions
Current: missions are on-demand.
Add: cron-triggered mission submission via APScheduler.
Effort: 1 day.

### 3.5 Model cost dashboard
Current: `data/model_performance.json` accumulates evidence.
Add: `/api/v3/models/performance` endpoint exposing cost/quality by task class.
Effort: 1 day (endpoint wraps existing data).

---

## TRACK 4 — Business model (parallel with Track 3)

Choose one initial monetization path:

| Model | Implementation | Time to revenue |
|-------|---------------|-----------------|
| Internal SaaS (team subscription) | Add Stripe + user seats | 1 week after multi-user |
| API-as-a-service | Add API key management + rate limiting | 1 week |
| Consulting / custom deployment | No code needed — sell the Docker stack | Immediate |

**Recommended first step**: Consulting / custom deployment. Zero product risk.
Sell "AI task automation backend, self-hosted" to companies that want internal AI automation but don't want to build it. Backend is the product. Ship it as a Docker package.

---

## Sequencing (recommended)

```
Week 1:  1.1 Docker boot + 1.3 integration tests + 2.1 pick use case
Week 2:  1.2 mobile smoke + 2.2 minimal frontend + 2.3 deploy to VPS
Week 3:  First real user / internal team + 3.1 multi-user auth
Week 4+: 3.2–3.5 based on user feedback + Track 4 monetization
```

---

## What NOT to do next

- Do NOT refactor the backend (it is frozen and working)
- Do NOT add new agent types before MVP is proven with existing agents
- Do NOT implement Stripe before at least one paying customer
- Do NOT rebuild the Flutter app from scratch (migrate incrementally)
- Do NOT add Kubernetes / distributed infra before scale demands it
