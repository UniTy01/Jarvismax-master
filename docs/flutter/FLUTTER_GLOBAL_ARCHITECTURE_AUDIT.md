# PART 1 — Flutter Global Architecture Audit
**Date:** 2026-03-27 | **App:** JarvisMax v1.0.0+1 | **Auditeur:** Claude Sonnet 4.6

---

## 1. Structure du Projet

```
lib/
├── config/api_config.dart          # Config host/port persistée (SharedPreferences)
├── main.dart                        # Entry point, MultiProvider, BottomNav (9 onglets)
├── models/
│   ├── action_model.dart            # ActionModel (statut, risk, approval)
│   ├── mission.dart                 # Mission (30+ champs, DQ v2)
│   └── system_status.dart           # SystemStatus (immutable, copyWith)
├── screens/ (11 screens)
├── services/
│   ├── api_service.dart             # ChangeNotifier + HTTP + timer refresh (500+ lignes)
│   ├── uncensored_notifier.dart     # ChangeNotifier uncensored mode
│   └── websocket_service.dart       # dart:io WebSocket + reconnect
├── theme/app_theme.dart             # JvColors, AppTheme.darkTheme
└── widgets/
    ├── cyber_card.dart              # CyberCard + SectionLabel + ScoreBar (inline)
    ├── score_bar.dart               # re-export uniquement (fichier inutile)
    ├── score_chart.dart             # CustomPainter sans dépendances externes
    └── status_badge.dart            # StatusBadge.forStatus / forRisk
```

---

## 2. State Management

### Pattern utilisé: Provider (ChangeNotifier)
Trois notifiers globaux montés dans main.dart:
- **ApiService**: 500+ lignes, gère missions + actions + status + timer + HTTP
- **UncensoredModeNotifier**: 40 lignes, délègue à ApiService
- **WebSocketService**: 90 lignes, gestion connexion WebSocket

### Évaluation
✅ Correct pour l'échelle du projet. Provider est suffisant pour une app mobile mono-utilisateur.
⚠️ Anti-pattern: responsabilité mixte dans ApiService. Ce service combine:
  - State (missions, actions, status, loading, error)
  - Network calls (HTTP GET/POST)
  - Business logic (normalisation de statuts, fusion de données)
  - Timer management (auto-refresh)

Recommandation: À terme, séparer en MissionRepository (network) + AppState (state). Non bloquant pour le release actuel.

---

## 3. API Service Layer

### Structure ApiResult<T>
```dart
class ApiResult<T> {
  final T? data;
  final String? error;
  bool get ok => error == null;
}
```
✅ Pattern propre, toutes les méthodes publiques retournent ApiResult<T>.

### Helpers HTTP
- `_get(path)` — 8s timeout
- `_post(path, body)` — 15s timeout
- `_parse(resp)` — JSON decode défensif, tolère array encapsulé en {data: list}

### Problèmes identifiés
1. **`_base` fallback hardcodé**: `_config?.baseUrl ?? 'http://10.0.2.2:8000'`
   Si config est null (race au démarrage), l'app tente 10.0.2.2 silencieusement.

2. **Auto-login avec credentials hardcodés** (CRITIQUE):
   ```dart
   await login('admin', 'JarvisSecretKey2026!');
   ```
   Mot de passe en clair dans le binaire APK. Extractible par reverse engineering.

3. **Normalisation de statut dans _loadActions**:
   ```dart
   if (e['status'] == 'DONE' || e['status'] == 'EXECUTING') {
     e['status'] = 'EXECUTED';
   }
   ```
   Or Mission.isApproved retourne true pour 'EXECUTING'. Incohérence entre ActionModel et Mission pour ce statut.

---

## 4. Navigation

9 onglets dans le BottomNavigationBar:
Dashboard | Mission | Validation | Mode | Historique | Paramètres | Insights | Capacités | Amélio.

⚠️ 9 onglets est excessif pour une bottom nav bar (recommandé max 5).
Sur petits écrans (320dp), les labels seront tronqués ou illisibles.
Recommandation: regrouper les écrans secondaires (Insights, Capacités, Amélio) dans un drawer ou page "Plus".

Architecture navigation: IndexedStack ✅ (préserve l'état des sous-arbres).
Routing manuel via Navigator.push pour MissionDetailScreen et ActionsScreen.

---

## 5. Séparation des Responsabilités

| Composant | Responsabilité | Rating |
|-----------|----------------|--------|
| api_config.dart | Config persistée uniquement | ✅ Propre |
| api_service.dart | State + Network + Timer | ⚠️ Trop de responsabilités |
| websocket_service.dart | WS uniquement | ✅ Propre |
| uncensored_notifier.dart | Wrapper état uncensored | ✅ Propre |
| Screens | UI + appels directs ApiService | ✅ Acceptable |
| Models | Parsing JSON défensif | ✅ Robuste |

---

## 6. Anti-patterns Détectés

1. **Credential hardcoding** (CRITIQUE) — api_service.dart:_loadJwt()
2. **Dead button** — SelfImprovementScreen: bouton "Approuver" avec onPressed: null
3. **Agent toggles visuels seulement** — settings_screen.dart: switch enable/disable agent sans appel API
4. **Fichier re-export inutile** — score_bar.dart fait uniquement un re-export de ScoreBar depuis cyber_card.dart
5. **Double refresh au démarrage** — main.dart appelle refresh() ET dashboard_screen.dart:initState appelle aussi checkHealth() + refresh()
6. **JWT stocké en SharedPreferences** malgré flutter_secure_storage déclaré en dépendance

---

## 7. Recommandations Architecture

### Priorité HAUTE (avant release)
- Fix credentials hardcodés (voir PART 7)
- Ajouter INTERNET permission dans AndroidManifest.xml
- Fix endpoint /api/image/generate → /api/multimodal/image

### Priorité MOYENNE (après release)
- Regrouper les 9 onglets nav en 5 max
- Extraire réseau de ApiService vers Repository
- Utiliser flutter_secure_storage pour JWT (déjà en dépendance)

### Priorité BASSE (tech debt)
- Supprimer score_bar.dart (re-export inutile)
- Implémenter les agent toggles en settings
