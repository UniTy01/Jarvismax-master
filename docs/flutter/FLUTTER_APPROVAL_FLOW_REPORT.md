# PART 4 — Flutter Approval Flow Report
**Date:** 2026-03-27 | **App:** JarvisMax v1.0.0+1

---

## 1. Vue d'Ensemble du Flux d'Approbation

### Screens impliqués
- ValidationScreen → wrapper trivial vers ActionsScreen
- ActionsScreen → 3 onglets: EN ATTENTE / EXÉCUTÉES / TOUTES
- DashboardScreen → badge badge count sur onglet Validation

### Endpoints approval
- GET /api/v2/tasks → charge les actions en attente
- POST /api/v2/tasks/{id}/approve → approuve une action
- POST /api/v2/tasks/{id}/reject → rejette avec raison optionnelle

---

## 2. Flux d'Approbation Utilisateur

### Étapes dans _ActionCard
1. Utilisateur voit l'action avec boutons REFUSER / APPROUVER
2. Click "APPROUVER" → api.approveAction(a.id)
   → POST /api/v2/tasks/{id}/approve
   → Recharge toutes les actions
3. Click "REFUSER" → dialog "Raison du refus" (optionnelle)
   → api.rejectAction(a.id, reason: reason)
   → POST /api/v2/tasks/{id}/reject {"note": reason}
   → Recharge toutes les actions

### Code d'approbation
```dart
Future<ApiResult<void>> approveAction(String id) async {
  try {
    await _post('/api/v2/tasks/$id/approve');
    await _loadActions();
    return const ApiResult.success(null);
  } catch (e) {
    try { await _loadActions(); } catch (_) {}
    return ApiResult.failure(_friendly(e));
  }
}
```
✅ Reload même en cas d'erreur (pour refléter l'état réel backend).
✅ Feedback visuel via SnackBar dans _ActionCardState.

---

## 3. Problèmes Identifiés

### P4.1 — Pas de gestion du timeout/expiration d'approbation
Si une action expire côté backend pendant que l'utilisateur consulte l'écran,
aucun mécanisme n'informe l'utilisateur. L'approbation échouera avec une erreur générique.
Recommandation: Afficher l'age de l'action (created_at → maintenant) + badge "EXPIRÉ".

### P4.2 — Badge count dans nav dépend uniquement de pendingActions
```dart
final pendingCount = context.watch<ApiService>().pendingActions.length;
```
```dart
List<ActionModel> get pendingActions =>
    _actions.where((a) => a.isPending).toList();
```
Or isPending est défini par:
```dart
bool get isPending  => status == 'PENDING';
```
Mais _loadActions() normalise DONE/EXECUTING → EXECUTED.
Il ne normalise pas les autres statuts. Les actions réellement en attente
(status == 'PENDING') seront comptées correctement.

### P4.3 — ActionsScreen auto-switch vers tab EXÉCUTÉES
```dart
if (api.pendingActions.isEmpty && api.actions.any((a) => a.isExecuted)) {
  _tabs.animateTo(1);
}
```
Ce comportement est déconcertant si l'utilisateur était intentionnellement sur le tab EN ATTENTE.

### P4.4 — Approbation sans confirmation pour actions HIGH/CRITICAL
Pour les actions MEDIUM/LOW, l'approbation est directe (un seul clic).
Pour HIGH/CRITICAL, il n'y a pas de dialog de confirmation supplémentaire.
Recommandation: Ajouter une confirmation avec affichage du risque pour HIGH/CRITICAL.

### P4.5 — /api/v2/tasks retourne des missions, pas des actions distinctes
Les objets "actions" dans ActionsScreen sont en réalité des missions normalisées.
Le champ "description" vient de plan_summary ou user_input, pas d'une vraie description d'action.
Le champ "diff" sera toujours vide car les missions n'ont pas de diff.
Impact UX: l'onglet EXÉCUTÉES montre des missions, pas des actions atomiques.

---

## 4. Résumé Issues Approval

| ID | Sévérité | Description |
|----|----------|-------------|
| P4.1 | 🟡 FAIBLE | Pas de gestion expiration/timeout approbation |
| P4.2 | 🟢 OK | Badge count correct |
| P4.3 | 🟡 FAIBLE | Auto-switch tab déconcertant |
| P4.4 | 🟠 MOYEN | Pas de confirmation pour actions HIGH/CRITICAL |
| P4.5 | 🟠 MOYEN | Sémantique action/mission confuse dans l'UI |

---

## 5. Recommandations

1. Ajouter confirmation dialog pour risque >= HIGH avant approbation
2. Afficher l'âge de l'action dans _ActionCard (calcul depuis created_at timestamp)
3. Désactiver l'auto-switch de tab (laisser l'utilisateur choisir)
4. Backend: créer un vrai endpoint /api/v2/actions avec ActionModel pur
