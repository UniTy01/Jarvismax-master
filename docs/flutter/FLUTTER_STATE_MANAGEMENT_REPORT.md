# PART 5 — Flutter State Management Report
**Date:** 2026-03-27 | **App:** JarvisMax v1.0.0+1

---

## 1. Architecture State

### Notifiers globaux (montés dans main.dart)
```dart
MultiProvider(
  providers: [
    ChangeNotifierProvider.value(value: apiConfig),       // Config persistée
    ChangeNotifierProvider.value(value: apiService),      // State principal
    ChangeNotifierProvider.value(value: uncensoredNotifier), // Mode uncensored
    ChangeNotifierProvider.value(value: wsService),       // WebSocket state
  ],
```

### State local (setState dans screens)
- MissionScreen: _sending, _lastMission, _missionActions, _loadingActions
- ActionsScreen: TabController (via SingleTickerProviderStateMixin)
- HistoryScreen: _filter (filtre statut actif)
- ModeScreen: _selected (mode sélectionné), _changing
- SettingsScreen: _uncensored, _saving, _agents, _agentEnabled, _policyMode
- InsightsScreen: _stats, _recent, _loading, _error
- CapabilitiesScreen: _data, _loading, _error
- SelfImprovementScreen: _suggestions, _loading, _error
- MissionDetailScreen: _detail, _loadingDetail, _showOutputs

---

## 2. Cohérence des États Entre Screens

### Cas 1: Missions partagées via ApiService
```dart
// DashboardScreen, HistoryScreen, MissionScreen lisent api.missions
final missions = api.missions; // source unique via Provider
```
✅ Cohérence garantie: tous les screens lisent la même liste.
✅ Refresh universel via api.refresh() → tous les Consumer<ApiService> se rebuildet.

### Cas 2: Uncensored mode — État dupliqué
SettingsScreen._uncensored (local setState) vs UncensoredModeNotifier.isUncensored (global).
```dart
// settings_screen.dart _toggleUncensored
await context.read<ApiService>().setUncensoredMode(val);
final prefs = await SharedPreferences.getInstance();
await prefs.setBool('uncensored_mode', val);  // ← SharedPrefs local
setState(() => _uncensored = val);             // ← État local screen

// UncensoredModeNotifier.setUncensored (mode_screen.dart)
await _api.setUncensoredMode(enabled);
_isUncensored = enabled;
notifyListeners();  // ← État global Provider
```
⚠️ L'état uncensored est géré à DEUX endroits différents:
  - SettingsScreen: ApiService.setUncensoredMode() + SharedPreferences + setState local
  - ModeScreen via UncensoredModeNotifier: ApiService.setUncensoredMode() uniquement
Les deux appellent l'API mais SettingsScreen persiste aussi en SharedPrefs, UncensoredModeNotifier non.
La source de vérité est le backend; SharedPrefs local peut diverger.

### Cas 3: _loadActions normalise EXECUTING → EXECUTED
```dart
if (e['status'] == 'DONE' || e['status'] == 'EXECUTING') {
  e['status'] = 'EXECUTED';
}
```
Mais Mission.isApproved retourne true pour 'EXECUTING'.
Un objet avec status='EXECUTING' sera traité différemment selon qu'il vient de
_missions (Mission) ou _actions (ActionModel). Incohérence de sémantique.

---

## 3. Async State Handling

### Loading states
```dart
bool _loading = false;
bool _isChecking = true;
```
_isChecking est utilisé pour le spinner initial (avant la première vérification health).
_loading est pour les opérations courantes.
✅ Deux niveaux de loading distincts — bonne pratique.

### Error state
```dart
String? _lastError;
```
Une seule variable d'erreur pour TOUTES les opérations.
Si loadMissions() et loadActions() échouent simultanément, seule la dernière erreur est visible.
⚠️ Non bloquant mais suboptimal.

### Race condition potentielle au démarrage
```dart
// main.dart:initState
api.checkHealth();
api.refresh();
api.startAutoRefresh();
context.read<UncensoredModeNotifier>().init();
context.read<WebSocketService>().connect();

// dashboard_screen.dart:initState (IndexedStack → screen TOUJOURS monté)
final api = context.read<ApiService>();
await api.autoLogin();
await api.checkHealth();  // ← DOUBLE checkHealth
api.refresh();            // ← DOUBLE refresh
```
⚠️ checkHealth() et refresh() sont appelés DEUX FOIS au démarrage: une fois depuis
main.dart et une fois depuis dashboard_screen.dart. Cela génère deux séries de
requêtes HTTP inutiles dès le lancement.

---

## 4. Rebuilds et Performance

### Consumer vs context.watch
Utilisation cohérente dans tous les screens:
- context.watch<ApiService>() dans les build() → rebuilds sur tout changement ApiService
- Consumer<ApiService> dans DashboardScreen.body → rebuild ciblé
- context.read<ApiService>() dans les callbacks → pas de rebuild

⚠️ DashboardScreen a un Consumer<ApiService> qui rebuild toute la ListView sur chaque
notifyListeners() de ApiService. Avec auto-refresh 30s, ce n'est pas critique.

### ScoreChart shouldRepaint
```dart
@override
bool shouldRepaint(_ScoreChartPainter old) => old.scores != scores;
```
⚠️ Comparaison par référence, pas par valeur. Si une nouvelle liste est créée avec
les mêmes valeurs, le chart se repeintera inutilement.

---

## 5. Récapitulatif Issues State

| ID | Sévérité | Description |
|----|----------|-------------|
| S5.1 | 🟠 MOYEN | État uncensored dupliqué entre SettingsScreen et UncensoredModeNotifier |
| S5.2 | 🟠 MOYEN | Double checkHealth + refresh au démarrage |
| S5.3 | 🟡 FAIBLE | EXECUTING normalisé EXECUTED dans _actions mais pas dans _missions |
| S5.4 | 🟡 FAIBLE | ScoreChart shouldRepaint par référence |
| S5.5 | 🟡 FAIBLE | _lastError unique pour toutes les opérations |

---

## 6. Recommandations

1. Supprimer le double refresh dans DashboardScreen.initState (main.dart gère déjà ce cas)
2. Centraliser la gestion uncensored: utiliser uniquement UncensoredModeNotifier
3. Fix ScoreChart.shouldRepaint: utiliser listEquals() ou DeepCollectionEquality
4. À terme: séparer les erreurs par domaine (missionError, actionError, statusError)
