# PRODUCTIZATION_ROADMAP.md — Jarvis Max
_Last updated: 2026-04-03 — Cycle 18: Backend hardening complete. Track 1 blockers resolved. Shifting to product._

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

## TRACK 1 — External validation status (2026-04-03)

### 1.1 Docker live boot proof ✅ PROVEN (Cycle 17)
Mission `43147205-391` → `COMPLETED`, 521 chars real LLM output.
`verify_boot.sh` exits 0. Logs `mission_completed`. **No longer a blocker.**

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

---

## TRACK 5 — First Product Direction (2026-04-03, post-Cycle 18)

### Selected product: AI Business Consultant / Strategy Operator

**Why this is the right first product:**
- 16 business skills already built in `business/skills/`: market_research, competitor_analysis, positioning, pricing_strategy, growth_plan, funnel_design, value_proposition, offer_design, customer_persona, acquisition_strategy, copywriting, landing_structure, spec_writing, saas_scope, automation_opportunity, strategy_reasoning
- Backend can execute complex multi-step business analysis missions today
- No new agent code needed — mission routing handles skill selection
- Target user: entrepreneur, early-stage founder, consultant, solo operator

### Core user workflow

```
1. User opens app (mobile or web)
2. Selects a business task type (or free-text goal)
3. Submits: "Analyse le marché des outils IA pour PME en France"
4. Backend routes to appropriate business skills (market_research + competitor_analysis + positioning)
5. Multi-agent execution returns structured report
6. User reads, downloads, or shares the result
7. If risk level triggers approval gate → user reviews before execution continues
```

### Required frontend screens (minimum viable)

| Screen | Status | Priority |
|--------|--------|----------|
| Login | ✅ Done | — |
| Mission submit (free text) | ✅ Done | — |
| Mission list + status | ✅ Done | — |
| Mission detail + result display | ✅ Done | — |
| Approval card | ✅ Done | — |
| **Task type selector** (choose skill category) | ✅ Done (Cycle 18 mobile) | HIGH |
| **Result export** (copy / share / PDF) | ✅ Done (Cycle 18 mobile) | HIGH |
| **Admin panel** (metrics, model cost, system health) | ✅ Done (Cycle 18 mobile) | MEDIUM |
| **French-first UI** (all labels in French) | ✅ Done (Cycle 18 mobile) | MEDIUM |

### Backend capabilities already sufficient

| Capability | Status |
|---|---|
| Business skill execution | ✅ Active (`business/skills/`) |
| Multi-agent orchestration | ✅ Proven |
| Mission persistence | ✅ Proven |
| Approval gate | ✅ Proven |
| JWT auth | ✅ Proven |
| Model cost control | ✅ Proven |
| Structured output | ✅ Proven |

### Remaining product gaps (not backend gaps)

1. **Task type selector in mobile app** — let user pick a business domain before submitting
2. **Result export** — copy to clipboard / share sheet / export as markdown
3. **French UI** — all tab labels, messages, error strings in French
4. **Admin view** — model cost, recent missions summary, system health (for operator)
5. **Onboarding** — first-time user explanation (what can Jarvis do?)

### Sequencing (realistic, post-Cycle 18)

```
Week 1:  ✅ French UI labels + result copy/share button  (commit 1ecc357)
Week 2:  ✅ Task type selector (16 business skills) + admin panel  (in progress)
Week 3:  Mobile smoke test + first internal user / founder feedback
Week 4:  Iterate on product UX based on real usage
Month 2: Consider web frontend (Next.js) if mobile-only limits reach
```
