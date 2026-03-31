# JarvisMax — Modèle d'Exécution

> Version : 2.0 | Date : 2026-03-19

---

## Vue d'ensemble

L'exécution dans JarvisMax suit un modèle en 3 niveaux :

```
NIVEAU 1 — Mission (MissionSystem)
  └─ NIVEAU 2 — Session (JarvisOrchestrator)
       └─ NIVEAU 3 — Action (ActionExecutor/SupervisedExecutor)
```

---

## Niveau 1 — Mission

### Cycle de vie

```
SUBMITTED → ANALYZING → PENDING_VALIDATION (mode MANUAL)
                      → APPROVED (mode SUPERVISED/AUTO)
                             → EXECUTING
                             → DONE / REJECTED / BLOCKED
```

### Persistance
- SQLite (primary) : table `missions`
- JSON fallback : `workspace/missions.json`
- Rotation automatique à 200 missions (purge DONE les plus anciennes)

---

## Niveau 2 — Session Agent

### États de session

```
PENDING    → session créée, pas encore traitée
RUNNING    → orchestrateur en cours
COMPLETED  → toutes les tâches terminées
ERROR      → erreur non récupérable
CANCELLED  → annulé par l'utilisateur
```

### Timeout par mode

| Mode | Timeout |
|------|---------|
| chat | 60s |
| auto | 600s (10 min) |
| improve | 900s (15 min) |
| night | 1800s (30 min) |

### Exécution parallèle des agents

Les agents sont groupés par priorité et exécutés en parallèle dans chaque groupe :

```
Groupe P1 : [vault-memory]                    → séquentiel
Groupe P2 : [scout-research, shadow-advisor]  → parallèle
Groupe P3 : [lens-reviewer, pulse-ops]        → parallèle
```

Implémenté par `agents/parallel_executor.py` avec timeout individuel de 90s et global de 300s.

---

## Niveau 3 — Action

### Types d'actions supportés

| Type | Description | Risque par défaut |
|------|-------------|-------------------|
| `read_file` | Lecture d'un fichier | LOW |
| `write_file` | Écriture (avec backup auto) | MEDIUM |
| `create_file` | Création de fichier | MEDIUM |
| `replace_in_file` | Remplacement dans fichier | MEDIUM |
| `run_command` | Commande shell (whitelist) | MEDIUM-HIGH |
| `list_dir` | Liste d'un répertoire | LOW |
| `analyze_dir` | Analyse récursive | LOW |
| `backup_file` | Backup manuel | LOW |
| `delete_file` | Suppression (backup auto) | HIGH |
| `move_file` | Déplacement (backup src) | MEDIUM |
| `copy_file` | Copie | LOW |

### Flux d'exécution d'une action

```
ActionSpec
  │
  ▼
RiskEngine.analyze()
  │
  ├─ LOW  → ActionExecutor.execute() → ExecutionResult
  ├─ MEDIUM → Notification + validation (ou auto en supervised mode)
  └─ HIGH → Bloqué (notification, log WARNING)
```

---

## RetryEngine (Nouveau en v2)

### Principe

Utilise `tenacity` pour les retries avec exponential backoff :

```python
RetryConfig(
    max_attempts = 3,
    base_delay   = 2.0,   # secondes
    max_delay    = 30.0,  # secondes
    backoff_factor = 2.0,
    jitter = True,         # évite le thundering herd
)
```

### Erreurs retryables vs non-retryables

| Erreur | Retryable |
|--------|-----------|
| `asyncio.TimeoutError` | ✅ Oui |
| `httpx.ConnectError` | ✅ Oui |
| `ConnectionRefusedError` | ✅ Oui |
| `ValidationError` (Pydantic) | ❌ Non |
| `PermissionError` | ❌ Non |
| `blacklist/whitelist rejection` | ❌ Non |
| `RiskLevel.HIGH blocked` | ❌ Non |

### Séquence de retry

```
Tentative 1 → échec timeout
  wait 2s
Tentative 2 → échec timeout
  wait 4s
Tentative 3 → échec timeout
  → FAILED → DebugAgent analysé
```

---

## TaskQueue (Nouveau en v2)

### Structure

```python
@dataclass
class QueuedTask:
    task_id:     str        # UUID
    mission_id:  str        # Mission parente
    agent:       str        # Agent assigné
    task:        str        # Description
    priority:    int        # 1 = haute, 4 = basse
    status:      TaskState  # pending | assigned | running | ...
    created_at:  float
    started_at:  float | None
    completed_at: float | None
    retry_count: int        # nombre de tentatives
    error:       str | None # dernière erreur
```

### Opérations

| Méthode | Description |
|---------|-------------|
| `enqueue(task)` | Ajoute la tâche en file avec priorité |
| `dequeue()` | Prend la tâche de plus haute priorité |
| `mark_running(task_id)` | Marque comme en cours |
| `mark_done(task_id, result)` | Finalise avec succès |
| `mark_failed(task_id, error)` | Finalise en échec |
| `mark_retrying(task_id)` | Met en état de retry |
| `cancel(task_id)` | Annule si PENDING |
| `stats()` | Statistiques de la file |

---

## Isolation des Tâches

Chaque tâche agent est exécutée dans son propre try/except :

```python
try:
    result = await asyncio.wait_for(
        agent.run(session),
        timeout=task.timeout_s
    )
    task_queue.mark_done(task.task_id, result)
except asyncio.TimeoutError:
    task_queue.mark_failed(task.task_id, "Timeout")
    retry_engine.schedule_retry(task)  # si retryable
except Exception as e:
    task_queue.mark_failed(task.task_id, str(e))
    log.error("task_failed", task_id=task.task_id, err=str(e))
```

L'échec d'un agent n'arrête pas les agents des autres groupes de priorité.

---

## Gestion des Backups

Tout `write_file`, `replace_in_file`, `delete_file` crée automatiquement un backup :

```
workspace/.backups/
  └─ {filename}.{YYYYMMDD_HHMMSS_microseconds}.bak
```

Le backup est référencé dans `ExecutionResult.backup_path` et dans le log JSONL.

**Rollback** (via RecoveryAgent) :
```python
# Restore depuis backup
shutil.copy2(backup_path, original_path)
```

---

## Journal d'Exécution

### Format JSONL (`logs/executor.jsonl`)

```json
{
  "ts":          "2026-03-19T01:33:55.123456",
  "session_id":  "a1b2c3d4",
  "mission_id":  "xyz-789",
  "correlation_id": "corr-abc",
  "agent":       "pulse-ops",
  "success":     true,
  "action":      "write_file",
  "target":      "workspace/reports/analysis.md",
  "duration_ms": 45,
  "risk":        "MEDIUM",
  "error":       null,
  "backup":      "workspace/.backups/analysis.20260319_013355_123456.bak"
}
```

### Rotation des logs
- Taille max : 50MB (configurable via `LOG_MAX_SIZE`)
- Rotation : gzip automatique, conservation 7 jours

---

## Interruption et Reprise

### Annulation d'une mission
1. `orchestrator.cancel_session(session_id)` → `asyncio.CancelledError`
2. Session status → `CANCELLED`
3. Tâches en cours → `cancel()` dans TaskQueue
4. Tâches PENDING → purgées de la file

### Reprise partielle (RecoveryAgent)
1. Lire les résultats partiels depuis `session.outputs`
2. Identifier les tâches non complétées
3. Réenqueuer uniquement les tâches manquantes
4. Réexécuter depuis le point de reprise

---

## Métriques d'Exécution

| Métrique | Description |
|----------|-------------|
| `task_success_rate` | % de tâches réussies (par agent) |
| `task_retry_rate` | % de tâches ayant nécessité un retry |
| `avg_duration_ms` | Durée moyenne d'exécution par agent |
| `queue_wait_ms` | Temps moyen en file avant exécution |
| `action_risk_distribution` | Répartition LOW/MEDIUM/HIGH |
| `backup_count` | Nombre de backups créés |
