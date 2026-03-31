# JarvisMax — Référence API v2

> Version : 2.0 | Base URL : `http://localhost:7070`

---

## Authentification

L'auth est optionnelle. Si `JARVIS_API_TOKEN` est défini dans `.env`,
toutes les routes (hors `/health`) requièrent le header :
```
X-Jarvis-Token: <votre-token>
```

---

## Tâches

### POST /api/v2/task
Soumettre une nouvelle tâche/mission.

**Request :**
```json
{
  "input":    "Analyse le code de l'orchestrateur",
  "mode":     "auto",    // auto | chat | research | plan | code | night | improve
  "priority": 2          // 1-4 (1=haute)
}
```

**Response 201 :**
```json
{
  "ok": true,
  "data": {
    "task_id":    "abc123",
    "mission_id": "xyz789",
    "status":     "pending",
    "mode":       "auto",
    "created_at": "2026-03-19T01:33:55"
  }
}
```

---

### GET /api/v2/task/{id}
Récupérer le statut d'une tâche.

**Response 200 :**
```json
{
  "ok": true,
  "data": {
    "task_id":    "abc123",
    "status":     "succeeded",
    "agent":      "scout-research",
    "result":     "## Synthèse\n...",
    "duration_ms": 2340,
    "retry_count": 0,
    "created_at":  "2026-03-19T01:33:55",
    "completed_at": "2026-03-19T01:34:15"
  }
}
```

---

### GET /api/v2/tasks
Lister les tâches avec filtres.

**Query params :** `status`, `agent`, `mission_id`, `limit` (défaut 20)

---

### POST /api/v2/missions/{id}/abort
Annuler une mission en cours.

---

## Agents

### GET /api/v2/agents
Liste tous les agents enregistrés avec leur statut.

**Response 200 :**
```json
{
  "ok": true,
  "data": {
    "agents": [
      {
        "name":       "scout-research",
        "role":       "research",
        "status":     "idle",
        "success_rate": 0.94,
        "avg_latency_ms": 1820
      }
    ],
    "total": 12
  }
}
```

---

### POST /api/v2/agents/{id}/trigger
Déclencher un agent manuellement avec une mission.

**Request :**
```json
{
  "mission": "Analyse les logs d'erreur",
  "context": {}
}
```

---

## Santé & Observabilité

### GET /api/v2/health
Health check complet.

**Response 200 :**
```json
{
  "ok": true,
  "data": {
    "status": "healthy",
    "components": {
      "llm":      {"status": "ok", "latency_ms": 850},
      "memory":   {"status": "ok", "backend": "sqlite"},
      "executor": {"status": "ok", "queue_size": 0},
      "api":      {"status": "ok", "uptime_s": 3600}
    },
    "checked_at": "2026-03-19T01:33:55"
  }
}
```

---

### GET /api/v2/metrics
Métriques du système.

**Response 200 :**
```json
{
  "ok": true,
  "data": {
    "runs_total":    42,
    "runs_success":  38,
    "success_rate":  0.905,
    "avg_duration_s": 12.4,
    "agents": {
      "scout-research": {"runs": 42, "success_rate": 0.95, "avg_ms": 1820}
    },
    "missions": {"total": 15, "done": 12, "pending": 2, "blocked": 1}
  }
}
```

---

### GET /api/v2/diagnostics
Diagnostics détaillés pour le debug.

---

### GET /api/v2/logs?n=50
Dernières N lignes de logs.

---

## Contrôle

### GET /api/v2/status
Statut global du système.

### POST /api/v2/restart
Redémarrage contrôlé (arrêt propre, vidage de la queue, redémarrage).

---

## Missions (v1 compatible)

### POST /api/v2/missions
Équivalent à POST /api/v2/task (alias).

### GET /api/v2/missions
Liste des missions.

### GET /api/v2/missions/{id}
Détail d'une mission.

---

## Codes d'erreur

| Code | Signification |
|------|--------------|
| 200 | Succès |
| 201 | Créé |
| 400 | Requête invalide (champ manquant) |
| 401 | Token invalide ou manquant |
| 404 | Ressource introuvable |
| 409 | Conflit (mission déjà en cours) |
| 500 | Erreur interne serveur |

**Format d'erreur :**
```json
{"ok": false, "error": "Champ 'input' requis."}
```

---

## Compatibilité v1

Les anciennes routes `/api/` restent fonctionnelles :

| Ancien route | Nouveau équivalent |
|--------------|-------------------|
| POST /api/mission | POST /api/v2/task |
| GET /api/missions | GET /api/v2/missions |
| GET /api/health | GET /api/v2/health |
| GET /api/stats | GET /api/v2/metrics |
