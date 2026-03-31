# PART 2 — Flutter API Alignment Report
**Date:** 2026-03-27 | **App:** JarvisMax v1.0.0+1

---

## 1. Tableau d'Alignement Endpoints

| Endpoint Flutter | Méthode | Endpoint Backend réel | Statut |
|-----------------|---------|----------------------|--------|
| /api/mission | POST | /api/mission (legacy) | ✅ OK |
| /api/v2/missions | GET | /api/v2/missions | ✅ OK |
| /api/v2/missions/{id} | GET | /api/v2/missions/{mission_id} | ✅ OK |
| /api/v2/tasks | GET | /api/v2/tasks | ✅ OK |
| /api/v2/tasks/{id}/approve | POST | /api/v2/tasks/{task_id}/approve | ✅ OK |
| /api/v2/tasks/{id}/reject | POST | /api/v2/tasks/{task_id}/reject | ✅ OK |
| /api/v2/status | GET | /api/v2/status | ✅ OK |
| /api/v2/agents | GET | /api/v2/agents | ✅ OK |
| /api/system/mode | POST | /api/system/mode | ✅ OK |
| /api/system/mode/uncensored | GET/POST | /api/system/mode/uncensored | ✅ OK |
| /api/v2/system/policy-mode | GET/POST | /api/v2/system/policy-mode | ✅ OK |
| /api/v2/metrics/recent | GET | /api/v2/metrics/recent | ✅ OK |
| /api/v2/self-improvement/suggestions | GET | routes/self_improvement.py | ⚠️ À VÉRIFIER |
| /api/v2/system/capabilities | GET | Absent des routes listées | ⚠️ À VÉRIFIER |
| /api/mcp/list | GET | Absent de toutes les routes | ❌ MANQUANT |
| /api/image/generate | POST | /api/multimodal/image (réel) | ❌ MISMATCH |
| /api/v1/missions/{id}/stream | GET SSE | /api/v1/missions/{mission_id}/stream | ✅ OK |
| /health | GET | /health via system.py | ✅ OK |
| /auth/token | POST | /auth/token | ✅ OK |
| /ws/stream | WebSocket | /ws/stream | ✅ OK |

---

## 2. Mismatches Critiques

### 2.1 /api/image/generate → Mauvais chemin (CRITIQUE)
**Fichier:** api_service.dart:generateImage()
```dart
// Flutter envoie vers:
final raw = await _post('/api/image/generate', {'prompt': prompt});

// Backend expose réellement:
@app.post("/api/multimodal/image")
async def hf_image_generate(...)
```
**Impact:** La génération d'image échouera avec HTTP 404.
**Fix:** Changer '/api/image/generate' en '/api/multimodal/image'.

### 2.2 /api/mcp/list → Endpoint inexistant
**Fichier:** api_service.dart:getMCPList()
```dart
final raw = await _get('/api/mcp/list');
```
Aucune route /api/mcp/list dans les routers montés (main.py + routes/*.py).
**Impact:** getMCPList() retourne toujours une erreur 404.
**Note:** Cette méthode n'est appelée depuis aucun screen → impact utilisateur nul pour l'instant.

---

## 3. Structures de Données — Analyse

### 3.1 POST /api/mission (soumission)
Flutter envoie: {"input": "...", "mode": "auto", "priority": 2}
Backend retourne: {"task_id": "...", "mission_id": "..."} ou objet mission partiel
Parsing Flutter:
```dart
final taskId = missionJson['task_id']?.toString() ??
    missionJson['mission_id']?.toString() ?? '';
```
✅ Défensif, gère les deux clés.

### 3.2 GET /api/v2/missions
Backend retourne: {"missions": [...]} ou liste directe
Flutter:
```dart
if (data is Map && data.containsKey('missions')) {
  list = data['missions'] as List? ?? [];
} else if (data is List) {
  list = data;
}
```
✅ Double fallback correct.

### 3.3 GET /api/v2/tasks
Backend retourne des objets Mission dans la liste de tâches.
Flutter normalise:
```dart
e['id'] ??= e['task_id'] ?? e['mission_id'] ?? '';
e['description'] ??= e['plan_summary'] ?? e['user_input'] ?? '';
if (e['status'] == 'DONE' || e['status'] == 'EXECUTING') {
  e['status'] = 'EXECUTED';
}
```
⚠️ Le backend retourne des missions dans /api/v2/tasks, pas des actions distinctes.
L'ActionModel est utilisé pour représenter des Mission → mapping artificiel.

### 3.4 GET /api/v2/status — Champ mode absent
Backend payload: {"missions": {"total": 10, "by_status": {"DONE": 5...}}}
Flutter cherche data['mode'] → absent → défaut 'AUTO' systématiquement.
```dart
final String mode = data is Map ? (data['mode']?.toString() ?? 'AUTO') : 'AUTO';
```
⚠️ Le mode système n'est jamais lu correctement depuis ce endpoint.

---

## 4. Résumé des Risques

| Sévérité | Problème | Fichier |
|----------|----------|---------|
| 🔴 CRITIQUE | /api/image/generate → 404 | api_service.dart:generateImage |
| 🟠 MOYEN | /api/v2/status ne retourne pas 'mode' → toujours 'AUTO' | api_service.dart:getMode |
| 🟡 FAIBLE | /api/mcp/list inexistant (méthode non appelée) | api_service.dart:getMCPList |
| 🟡 FAIBLE | /api/v2/tasks retourne missions pas actions | api_service.dart:_loadActions |

---

## 5. Recommandations

1. Fix immédiat: '/api/image/generate' → '/api/multimodal/image'
2. Fix mode: Ajouter endpoint GET /api/system/mode au backend OU lire depuis /api/v2/status correctement
3. Supprimer getMCPList() ou implémenter l'endpoint backend correspondant
4. Clarifier sémantique actions/missions: créer vrai endpoint d'actions ou renommer le concept Flutter
