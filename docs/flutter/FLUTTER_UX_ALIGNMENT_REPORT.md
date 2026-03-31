# PART 9 — Flutter UX Alignment Report
**Date:** 2026-03-27 | **App:** JarvisMax v1.0.0+1

---

## 1. Alignement UI/Concept Jarvis

### Concept attendu
L'app doit permettre de:
1. Lancer des missions (commandes en langage naturel)
2. Suivre l'état des missions en temps-réel
3. Voir les traces d'exécution (agent outputs)
4. Approuver ou rejeter des actions proposées par Jarvis
5. Configurer le niveau d'autonomie (mode AUTO/SUPERVISED/MANUAL)

### Mapping Screens → Fonctionnalités

| Fonctionnalité | Screen | Statut UX |
|----------------|--------|-----------|
| Lancer mission | MissionScreen | ✅ Fonctionnel |
| Suivi temps-réel mission | MissionScreen (post-send) | ⚠️ Polling 2s seulement |
| Voir traces exécution | MissionDetailScreen (agent outputs) | ✅ Bon |
| Approuver actions | ActionsScreen/ValidationScreen | ✅ Fonctionnel |
| Historique missions | HistoryScreen | ✅ Bon |
| Configurer mode | ModeScreen | ✅ Bon |
| Voir score advisory | DashboardScreen + détail | ✅ Bon |

---

## 2. Navigation UX — 9 Onglets Bottom Nav

### Problème: surcharge cognitive
9 onglets dans une bottom nav bar sur mobile:
- Material Design recommande 3-5 items maximum
- Sur écran 360dp de largeur, chaque item fait ~40dp → labels tronqués
- L'ordre actuel n'est pas hiérarchisé par importance

### Ordre actuel (index 0-8)
0: Dashboard | 1: Mission | 2: Validation | 3: Mode
4: Historique | 5: Paramètres | 6: Insights | 7: Capacités | 8: Amélio.

### Recommandation — 5 onglets principaux
0: Dashboard (vue globale)
1: Mission (core action)
2: Validation (badge count)
3: Historique (liste missions)
4: Plus → sheet/drawer avec Mode, Paramètres, Insights, Capacités, Amélio.

---

## 3. Feedback Utilisateur

### Points positifs
✅ SnackBars pour confirmations/erreurs (couleur verte/rouge)
✅ CircularProgressIndicator sur les opérations async
✅ Badge count sur l'onglet Validation (actions en attente)
✅ Indicateur WS (vert/gris) dans MissionScreen
✅ Banner "HORS LIGNE" avec bouton Retry
✅ _UncensoredPill dans AppBar quand mode uncensored actif
✅ Badge "ACTIF" sur le mode courant dans ModeScreen

### Points négatifs
❌ "Approuver" dans SelfImprovementScreen → onPressed: null (bouton mort)
❌ Agent toggles dans SettingsScreen → visuels seulement, aucun effet
❌ Pas d'animation de progression pendant l'exécution de mission
❌ Pas de bouton Annuler/Retry dans MissionDetailScreen
❌ Le message de succès post-mission est identique que la mission soit DONE ou juste SOUMISE

---

## 4. Accessibilité et Lisibilité

### Thème dark cyber
✅ Contraste bon: textPrim (#E8F4FD) sur bg (#0A0E1A)
✅ Couleurs sémantiques cohérentes (vert=succès, rouge=erreur, orange=attention)
⚠️ Taille police minimale: textMut 9pt/10pt peut être trop petit sur certains écrans

### Fonts
Utilisation de 'monospace' (system font) pour les IDs et codes.
✅ Cohérent avec le thème cyber.

---

## 5. Suggestions Rapides (MissionScreen)

```dart
static const _suggestions = [
  'Analyser les logs du système',
  'Créer un rapport de performance',
  'Vérifier l\'état des agents',
  'Optimiser la mémoire vault',
  'Planifier une revue de code',
  'Rechercher les erreurs récentes',
];
```
✅ Suggestions pertinentes pour une app DevOps/IA.
⚠️ Hardcodées — ne s'adaptent pas au contexte ou à l'historique utilisateur.

---

## 6. Récapitulatif Issues UX

| ID | Sévérité | Description |
|----|----------|-------------|
| U9.1 | 🔴 BLOQUANT UX | Bouton "Approuver" mort dans SelfImprovementScreen |
| U9.2 | 🟠 MOYEN | 9 onglets bottom nav trop nombreux |
| U9.3 | 🟠 MOYEN | Agent toggles visuels seulement (settings screen) |
| U9.4 | 🟠 MOYEN | Pas de progression temps-réel mission post-submit |
| U9.5 | 🟡 FAIBLE | Pas de cancel/retry dans MissionDetailScreen |
| U9.6 | 🟡 FAIBLE | Suggestions missions hardcodées |
| U9.7 | 🟢 OK | Feedback offline/online bien géré |
| U9.8 | 🟢 OK | Couleurs sémantiques cohérentes |

---

## 7. Recommandations UX Prioritaires

1. Fix immédiat: implémenter ou désactiver proprement le bouton "Approuver" en SelfImprovementScreen
2. Ajouter progression temps-réel via SSE dans MissionScreen
3. Réduire la bottom nav à 5 items (regrouper les secondaires)
4. Implémenter les agent toggles dans SettingsScreen (appel API enable/disable)
