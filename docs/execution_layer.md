# Execution Layer — JarvisMax v2

## 1. Architecture Overview

```
         ┌─────────────────────────────────────────────────────────┐
         │                   ExecutionEngine                        │
         │                  (singleton, daemon)                     │
         │                                                          │
         │  submit(task) ─► _heap (heapq, priorité + created_at)   │
         │                        │                                 │
         │                 _worker_loop() [poll 2s]                 │
         │                        │                                 │
         │            ┌───────────▼──────────────┐                 │
         │            │  _process_batch()         │                 │
         │            │  (max 4 tâches/cycle)     │                 │
         │            └───────────┬──────────────┘                 │
         │                        │  [thread par tâche]             │
         │            ┌───────────▼──────────────┐                 │
         │            │  _execute_task()          │                 │
         │            │  retry + timeout          │                 │
         │            └───────────┬──────────────┘                 │
         │                        │  [thread handler]               │
         │            ┌───────────▼──────────────┐                 │
         │            │  _dispatch_with_timeout() │                 │
         │            │  handlers.get_handler()   │                 │
         │            └──────────────────────────┘                 │
         │                                                          │
         │  cancel(task_id) ─► flag ou statut CANCELLED             │
         │  status(task_id) ─► dict tâche                           │
         │  list_tasks()    ─► list[dict]                           │
         │  stats()         ─► counters par statut                  │
         └─────────────────────────────────────────────────────────┘

Fichiers :
  executor/execution_engine.py  — moteur central
  executor/task_model.py        — ExecutionTask, ExecutionResult
  executor/retry_policy.py      — RetryPolicy, compute_delay, is_retryable
  executor/handlers.py          — handlers par type (research, review, plan, …)
  executor/__init__.py          — exports publics
```

---

## 2. Task Lifecycle

```
          ┌──────────┐
          │ PENDING  │◄──────────────────────────────────────────┐
          └────┬─────┘                                           │
               │  worker_loop dépile                             │
               ▼                                                 │
          ┌──────────┐                                           │
          │ RUNNING  │                                           │
          └────┬─────┘                                           │
               │                                                 │
     ┌─────────┼──────────────────────┐                         │
     │         │                      │                         │
     ▼         ▼                      ▼                         │
┌─────────┐ ┌──────────┐  ┌───────────────┐                    │
│SUCCEEDED│ │ FAILED   │  │  TIMED_OUT    │                    │
└─────────┘ └──────────┘  └───────────────┘                    │
                                   │                            │
                            retryable? ──── oui ───────────────┘
                                   │
                                  non
                                   │
                             ┌──────────┐
                             │  FAILED  │
                             └──────────┘

Depuis PENDING ou RUNNING :
  cancel(task_id) → CANCELLED

Garanties :
  - Aucune transition silencieuse (chaque changement de statut est logué)
  - Toutes les tâches restent dans _tasks (pas de purge automatique)
  - FAILED final = soit erreur non-retryable, soit max_attempts épuisé
```

---

## 3. Retry Policy

### Configuration

```python
from executor.retry_policy import RetryPolicy

policy = RetryPolicy(
    max_attempts   = 3,       # nombre total de tentatives
    base_delay     = 1.0,     # délai initial en secondes
    max_delay      = 30.0,    # délai maximum en secondes
    backoff_factor = 2.0,     # multiplicateur exponentiel
)
```

### Calcul du délai

```
délai(n) = min(base_delay * backoff_factor^(n-1), max_delay) ± jitter(30%)
```

Exemples avec base=1.0, factor=2.0, max=30.0 :
- Tentative 1 → ~1.0s
- Tentative 2 → ~2.0s
- Tentative 3 → ~4.0s
- Tentative 6 → ~30.0s (plafond)

### Erreurs retryables vs non-retryables

| Retryable                        | Non-retryable                     |
|----------------------------------|-----------------------------------|
| `TimeoutError`                   | `ValueError`                      |
| `ConnectionError`                | `TypeError`                       |
| `OSError`                        | `AssertionError`                  |
| Messages contenant "timeout",    | `KeyboardInterrupt`               |
| "connect", "unavailable", "503"… | `NotImplementedError`             |

Les erreurs non-retryables mènent immédiatement à FAILED (0 retry).

### Presets disponibles

```python
from executor.retry_policy import DEFAULT_POLICY, FAST_POLICY, AGGRESSIVE_POLICY

DEFAULT_POLICY    = RetryPolicy(max_attempts=3, base_delay=1.0, max_delay=30.0)
FAST_POLICY       = RetryPolicy(max_attempts=2, base_delay=0.5, max_delay=5.0)
AGGRESSIVE_POLICY = RetryPolicy(max_attempts=5, base_delay=2.0, max_delay=60.0)
```

---

## 4. Handlers

### Handler existants

| Nom        | Fonction            | Description                                |
|------------|---------------------|--------------------------------------------|
| `research` | `handle_research`   | Vault memory + scan workspace              |
| `review`   | `handle_review`     | Audit système (API, DB, workspace)         |
| `plan`     | `handle_plan`       | Génération de plan contextuel              |
| `improve`  | `handle_improve`    | Scan TODO/FIXME dans le code               |
| `generic`  | `handle_generic`    | Fallback universel                         |

### Ajouter un nouveau handler

```python
# Dans executor/handlers.py (ou tout autre module chargé au démarrage)
from executor.handlers import HANDLER_REGISTRY

def handle_deploy(task):
    """Mon handler personnalisé."""
    target = task.payload.get("target", "")
    # … logique …
    return f"Deployed to {target}"

HANDLER_REGISTRY["deploy"] = handle_deploy
```

Ou via le décorateur :

```python
from executor.handlers import register_handler

@register_handler("deploy")
def handle_deploy(task):
    return "deployed"
```

### Contrat d'un handler

```python
def handle_xxx(task: ExecutionTask) -> str:
    """
    - Lit task.description, task.payload, task.mission_id
    - Retourne un string résultat (peut être vide)
    - Lève une exception si échec (déclenche le retry selon RetryPolicy)
    """
```

---

## 5. API Reference

### ExecutionEngine

```python
engine = get_engine()  # singleton, démarre automatiquement
```

#### `submit(task: ExecutionTask) -> str`
Soumet une tâche. Retourne le `task_id`.

#### `cancel(task_id: str) -> bool`
Annule une tâche PENDING ou RUNNING. Retourne `True` si l'annulation a eu lieu ou a été demandée.

#### `status(task_id: str) -> dict | None`
Retourne l'état courant d'une tâche sous forme de dict, ou `None` si inconnue.

Champs retournés :
```python
{
    "id": "abc123",
    "mission_id": "...",
    "correlation_id": "...",
    "description": "...",
    "handler_name": "research",
    "status": "SUCCEEDED",   # PENDING/RUNNING/SUCCEEDED/FAILED/CANCELLED/TIMED_OUT
    "created_at": 1710000000.0,
    "started_at": 1710000001.0,
    "finished_at": 1710000002.5,
    "attempts": 1,
    "max_attempts": 3,
    "result": "...",
    "error": "",
    "priority": 5,
    "timeout_seconds": 30.0,
}
```

#### `list_tasks(status=None, mission_id=None, limit=50) -> list[dict]`
Liste les tâches avec filtres optionnels. Triées par `created_at` décroissant.

#### `stats() -> dict`
Statistiques globales :
```python
{
    "total": 42,
    "pending": 2,
    "running": 1,
    "succeeded": 35,
    "failed": 3,
    "cancelled": 1,
    "timed_out": 0,
    "started_at": 1710000000.0,
    "engine_running": True,
}
```

---

## 6. Monitoring

### Logs structurés (structlog)

Chaque événement inclut systématiquement : `task_id`, `correlation_id`, `mission_id`, `attempt`.

| Event                        | Level   | Description                              |
|------------------------------|---------|------------------------------------------|
| `task_submitted`             | INFO    | Tâche soumise à la queue                 |
| `task_attempt_start`         | INFO    | Début d'une tentative                    |
| `task_succeeded`             | INFO    | Succès (avec durée ms et preview)        |
| `task_retry_scheduled`       | WARNING | Retry planifié (delay, erreur)           |
| `task_failed_non_retryable`  | ERROR   | Échec non-retryable                      |
| `task_failed_max_attempts`   | ERROR   | Max tentatives épuisées                  |
| `task_timed_out`             | ERROR   | Timeout dépassé                          |
| `task_cancelled_pending`     | INFO    | Annulation avant démarrage               |
| `task_cancel_requested_running` | INFO  | Annulation demandée (en cours)           |
| `task_engine_crash`          | ERROR   | Crash inattendu (filet de sécurité)      |

### Stats en temps réel

```python
from executor import get_engine
print(get_engine().stats())
```

---

## 7. Examples

### Soumettre une tâche

```python
from executor import get_engine, ExecutionTask, RetryPolicy

engine = get_engine()

task = ExecutionTask(
    description="Analyser le workspace",
    handler_name="research",
    mission_id="mission-42",
    priority=2,               # 1=haute, 9=basse
    max_attempts=3,
    timeout_seconds=30.0,
    payload={"target": "workspace/"},
    retry_policy=RetryPolicy(max_attempts=3, base_delay=1.0),
)

task_id = engine.submit(task)
print(f"Tâche soumise : {task_id}")
```

### Vérifier le statut

```python
import time

while True:
    s = engine.status(task_id)
    print(f"Status: {s['status']} — attempts: {s['attempts']}")
    if s["status"] in {"SUCCEEDED", "FAILED", "CANCELLED", "TIMED_OUT"}:
        break
    time.sleep(0.5)
```

### Annuler une tâche

```python
cancelled = engine.cancel(task_id)
print(f"Annulation {'effectuée' if cancelled else 'impossible'}")
```

### Lister les tâches d'une mission

```python
tasks = engine.list_tasks(mission_id="mission-42", limit=20)
for t in tasks:
    print(f"{t['id']} — {t['status']} — {t['description'][:40]}")
```

### Ajouter un handler depuis un autre module

```python
# Dans votre code applicatif, avant de soumettre des tâches :
from executor.handlers import HANDLER_REGISTRY

def handle_my_custom_action(task):
    data = task.payload
    # traitement...
    return "Résultat de mon action"

HANDLER_REGISTRY["my_custom"] = handle_my_custom_action
```
