# JARVIS MAX — AI Agent Orchestration System

> Multi-agent autonomous system: planning, secure execution,
> persistent memory, self-improvement — controlled via the Jarvis app or API.

---

## Quick Start

```bash
# 1. Install (generates secrets, pulls images)
bash scripts/install.sh

# 2. Configure .env
nano .env
# Required: OPENAI_API_KEY

# 3. Launch
python main.py
# Or via Docker:
docker compose up jarvis
```

The Jarvis app connects to `http://<server>:8000`.

---

## Architecture

```
Jarvis App / API (port 8000)  ← PRIMARY INTERFACE
  └── MetaOrchestrator  ← SINGLE orchestration entry point
        ├── Planner      → steps + objective_context + difficulty
        ├── AgentCrew    → 9 agents (P1 → P2 → P3)
        ├── RiskEngine   → LOW (auto) / MEDIUM / HIGH (API approval)
        ├── Executor     → atomic actions + backup + rollback
        └── Self-Improvement → weakness → candidates → score → execute
              (core/self_improvement/ — MAX=1, COOLDOWN=24h)
```

**Couches du code source :**
```
api/                  → FastAPI + routes (objectives, self-improvement, missions)
core/                 → Orchestration + planner + memory + self-improvement
core/self_improvement/→ CANONICAL self-improvement pipeline
agents/               → 9 agents + crew parallèle
executor/             → Secure execution + retry + mission_result
tests/                → 280+ tests
```

> Voir [ARCHITECTURE.md](ARCHITECTURE.md) pour le schéma complet des couches.

---

## Stack Docker

| Service      | Rôle                        | Port  |
|--------------|-----------------------------|-------|
| jarvis_core  | Orchestrateur Python        | 8000  |
| postgres     | Base de données principale  | —     |
| redis        | Cache / sessions            | —     |
| qdrant       | Mémoire vectorielle         | 6333  |
| ollama       | LLM local                   | 11434 |
| n8n          | Automatisation workflows    | 5678  |
| open_webui   | Interface modèles locaux    | 3001  |

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v2/missions/submit` | Submit a mission |
| GET | `/api/v2/missions/{id}` | Mission status |
| POST | `/api/v2/tasks/{id}/approve` | Approve action |
| POST | `/api/v2/tasks/{id}/reject` | Reject action |
| GET | `/api/v2/status` | System status |
| GET | `/api/v2/agents` | Agent registry |
| POST | `/api/v2/self-improve/run` | Trigger self-improvement |

### Approval Flow

For MEDIUM/HIGH risk actions, JarvisMax requests approval via the API:
- `POST /api/v2/tasks/{id}/approve` → execute
- `POST /api/v2/tasks/{id}/reject` → cancel

---

## Risk Levels

| Level | Examples | Behavior |
|-------|----------|----------|
| 🟢 LOW | Read, create workspace, analyze | Auto-executed |
| 🟡 MEDIUM | Modify files, scripts | Approval required |
| 🔴 HIGH | Delete, install, network | Approval required |

---

## Les 9 agents

| Agent            | Rôle                        | LLM            |
|------------------|-----------------------------|----------------|
| AtlasDirector    | Chef d'orchestre / planning | GPT-4o         |
| ScoutResearch    | Recherche et synthèse       | GPT-4o-mini    |
| MapPlanner       | Plans et roadmaps           | GPT-4o-mini    |
| ForgeBuilder     | Code, scripts, fichiers     | Claude/GPT-4o  |
| LensReviewer     | Contrôle qualité            | Claude/GPT-4o  |
| VaultMemory      | Mémoire long terme          | Ollama (local) |
| ShadowAdvisor    | Perspectives alternatives   | Ollama (local) |
| PulseOps         | Préparation d'actions       | GPT-4o-mini    |
| NightWorker      | Missions longues            | GPT-4o         |

---

## Workspace

```
workspace/
├── projects/     ← Projets créés par Jarvis
├── reports/      ← Rapports et analyses
├── missions/     ← Résultats Night Worker
│   └── <session_id>/
│       ├── cycle_01.json
│       ├── cycle_02.json
│       └── rapport_final.md
├── patches/      ← Patches auto-amélioration
└── .backups/     ← Backups avant modification
```

---

## Configuration LLM

Jarvis choisit automatiquement le meilleur modèle par rôle :

```
director  → OpenAI GPT-4o    (ou Ollama si pas d'API)
builder   → Anthropic Claude  (ou GPT-4o si pas d'API Anthropic)
reviewer  → Anthropic Claude
advisor   → Ollama local      (toujours local, isolation des données)
memory    → Ollama local
```

Fonctionne **sans aucune API externe** (tout sur Ollama).

---

## Modules avancés

### n8n Bridge

```python
from tools.n8n.bridge import N8nBridge
bridge = N8nBridge(settings)

# Créer un workflow HTTP
wf = await bridge.create_simple_http_workflow("Mon workflow", "https://api.example.com")

```

### Browser Automation (Playwright)

```python
from tools.browser.scraper import BrowserTool
async with BrowserTool(settings) as browser:
    text    = await browser.get_text("https://example.com")
    results = await browser.search_and_scrape("intelligence artificielle")
    data    = await browser.extract_structured(url, {"title": "h1", "price": ".price"})
```

### System Observer

```python
from observer.watcher import SystemObserver
obs     = SystemObserver(settings)
snap    = await obs.snapshot_workspace()     # État du workspace
changes = await obs.detect_changes(since_minutes=60)  # Fichiers modifiés
analysis = await obs.analyze_logs(n=50)     # Analyse des logs
```

---

## Ajouter un agent personnalisé

```python
from agents.crew import BaseAgent, AgentCrew
from core.state import JarvisSession

class MyAgent(BaseAgent):
    name, role = "my-agent", "research"

    def system_prompt(self) -> str:
        return "Tu es un agent spécialisé en..."

    def user_message(self, session: JarvisSession) -> str:
        return f"Mission : {session.mission_summary}"

# Enregistrer dans le crew
crew = AgentCrew(settings)
crew.add(MyAgent(settings))
```

---

## Variables .env clés

| Variable                    | Description                    | Requis |
|-----------------------------|--------------------------------|--------|
| `OPENAI_API_KEY`            | OpenAI API key                 | ✅     |
| `POSTGRES_PASSWORD`         | PostgreSQL password             | ✅     |
| `REDIS_PASSWORD`            | Mot de passe Redis             | ✅     |
| `OPENAI_API_KEY`            | Clé API OpenAI                 | ⚡     |
| `ANTHROPIC_API_KEY`         | Clé API Anthropic              | —      |
| `DRY_RUN`                   | `true` = simuler sans exécuter | —      |

⚡ = Au moins un provider LLM requis (OpenAI ou Ollama seul suffit)

---

## Debugging

```bash
# Logs en temps réel
docker compose logs -f jarvis

# Logs d'un service
docker compose logs -f ollama

# API health
curl http://localhost:8000/health

# Dernières actions
curl http://localhost:8000/logs?n=20

# Snapshot workspace
curl http://localhost:8000/workspace

# Redémarrer uniquement Jarvis (sans toucher aux autres services)
docker compose restart jarvis

# Accéder au shell du conteneur
docker compose exec jarvis bash

# Voir les modèles Ollama
docker compose exec ollama ollama list
```

---

## Roadmap évolutive

Voir [ROADMAP.md](ROADMAP.md) pour la roadmap complète.

Prochaines étapes clés :
- Synchronisation guards FORBIDDEN_SELF_MODIFY ↔ PROTECTED_FILES
- Dashboard web (monitoring objectifs + workspace)

---

## Docs

| Document | Description |
|---|---|
| [ARCHITECTURE.md](ARCHITECTURE.md) | Schéma complet des couches, pipeline, SI loop |
| [ROADMAP.md](ROADMAP.md) | Phases complétées et prochaines étapes |
| [CHANGELOG.md](CHANGELOG.md) | Historique des changements |
| [AUDIT_REPO.md](AUDIT_REPO.md) | Inventaire CANONICAL/LEGACY/ARCHIVE |
