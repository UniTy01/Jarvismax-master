# PART 3 — Flutter Mission Flow Report
**Date:** 2026-03-27 | **App:** JarvisMax v1.0.0+1

---

## 1. Cycle de Vie Mission — Statuts

### Statuts backend connus (depuis StatusBadge + History filtres)
PENDING / PENDING_VALIDATION → ANALYZING → APPROVED / EXECUTING → DONE
                                          → REJECTED
                                          → BLOCKED

### Getters dans Mission.dart
```dart
bool get isPending  => status == 'PENDING_VALIDATION';
bool get isBlocked  => status == 'BLOCKED';
bool get isDone     => status == 'DONE';
bool get isApproved => status == 'APPROVED' || status == 'EXECUTING';
```
✅ Couvre les statuts principaux.
⚠️ 'PENDING' (initial) et 'ANALYZING' n'ont pas de getter dédié.

---

## 2. Flux de Création Mission

### Étapes dans MissionScreen._send()
1. Utilisateur entre texte + appuie "ENVOYER"
2. api.submitMission(input) → POST /api/mission
3. Backend retourne {task_id: "..."} (réponse immédiate)
4. Flutter recharge toutes les missions + toutes les actions
5. Flutter attend 2 secondes fixes: await Future.delayed(Duration(seconds: 2))
6. Recharge les actions et filtre par missionId
7. Affiche le résultat dans _MissionResult

### Problèmes Identifiés

#### P3.1 — Polling fixe post-submit (2 secondes)
```dart
await Future.delayed(const Duration(seconds: 2));
await api.loadActions();
```
Problème: 2 secondes est arbitraire. Si le backend est lent, les actions ne seront pas prêtes.
Impact: Affiche "Traitement en cours..." même si la mission a déjà un résultat.
Fix recommandé: Utiliser le SSE stream /api/v1/missions/{id}/stream déjà implémenté dans streamMissionLogs().

#### P3.2 — Pas de suivi temps-réel de la mission en cours
Après soumission, l'utilisateur voit le statut figé. L'auto-refresh (30s) est trop lent
pour du feedback en temps réel.

#### P3.3 — Mission soumise via endpoint legacy
```dart
final raw = await _post('/api/mission', {'input': input, 'mode': 'auto', 'priority': 2});
```
Le backend expose /api/v2/missions/submit comme endpoint v2 préféré.
Les deux fonctionnent, mais le v2 peut avoir plus de champs de réponse.

---

## 3. Affichage des Statuts

### StatusBadge.forStatus() — Mapping couleur
| Statut | Couleur | Correct |
|--------|---------|---------|
| PENDING / PENDING_VALIDATION | Orange | ✅ |
| APPROVED / EXECUTING | Cyan | ✅ |
| DONE / EXECUTED | Vert | ✅ |
| REJECTED / BLOCKED / FAILED | Rouge | ✅ |
| ANALYZING | CyanDark | ✅ |
| Inconnu | TextMut (gris) | ✅ |

---

## 4. Flux de Détail Mission

### MissionDetailScreen._fetchDetail()
```dart
final result = await api.fetchMissionDetail(widget.mission.id);
// GET /api/v2/missions/{id}
```
✅ Charge le détail frais depuis le backend.
✅ Fallback sur widget.mission (données partielles) si erreur.

### Problème P3.4 — Mauvaise clé dans _PlanStepCard
```dart
// MissionDetailScreen._PlanStepCard: INCORRECT
final desc = step['description'] as String? ??
    step['action'] as String? ??
    step.toString();

// HistoryScreen._MissionItem._PlanStepRow: CORRECT
final desc = (step['task'] ?? step['description'] ?? step['action'])?.toString();
```
Problème: MissionDetailScreen n'utilise pas 'task' comme clé primaire alors que
c'est ce que le backend retourne. Les étapes de plan afficheront les fallbacks.

---

## 5. Retry / Cancel

### Retry
Pas de bouton "Retry" visible pour les missions BLOCKED ou FAILED.
L'utilisateur doit remettre manuellement la même commande.
Recommandation: Ajouter bouton "Relancer" dans MissionDetailScreen quand status == 'BLOCKED'.

### Cancel
Pas de bouton annuler dans l'UI. Le backend expose /api/v2/missions/{id}/abort.
Recommandation: Ajouter bouton "Annuler" pour les missions EXECUTING/APPROVED.

---

## 6. Récapitulatif Issues Mission Flow

| ID | Sévérité | Description | Fix |
|----|----------|-------------|-----|
| P3.1 | 🟠 MOYEN | Polling fixe 2s post-submit | Utiliser SSE streamMissionLogs |
| P3.2 | 🟡 FAIBLE | Pas de suivi temps-réel | Connecter WS events au mission courant |
| P3.3 | 🟡 FAIBLE | Endpoint legacy pour soumission | Migrer vers /api/v2/missions/submit |
| P3.4 | 🟠 MOYEN | Mauvaise clé planStep dans détail | Ajouter 'task' comme clé primaire |
| P3.5 | 🟡 FAIBLE | Pas de retry/cancel UI | Ajouter boutons dans MissionDetailScreen |
