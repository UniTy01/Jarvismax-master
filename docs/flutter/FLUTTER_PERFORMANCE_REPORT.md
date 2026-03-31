# PART 8 — Flutter Performance Report
**Date:** 2026-03-27 | **App:** JarvisMax v1.0.0+1

---

## 1. Rebuilds UI

### ApiService.notifyListeners() — fréquence
notifyListeners() est appelé dans:
- _setLoading(true/false) — 2x par opération
- _loadMissions() — après reload
- _loadActions() — après reload
- checkHealth() — après vérification
- getMode() — après chaque appel status
- refresh() → appelle tous les précédents

refresh() appelle en parallèle: _loadMissions, _loadActions, _loadStats, getMode
Chacun appelle notifyListeners → 4-5 notifications en cascade pour un seul refresh.

### Impact
Chaque notifyListeners() rebuild tous les Consumer<ApiService> et context.watch<ApiService>().
Avec 9 screens dans IndexedStack, tous les screens sont montés simultanément.
Un seul refresh génère ~5 notifications × ~9 screens = potentiellement ~45 rebuilds.

### Atténuation existante
✅ IndexedStack préserve l'état mais TOUS les widgets sont montés → tous reçoivent les notifications.
✅ Les primitives Flutter (Text, Container) sont rapides à rebuilder.
⚠️ Pas d'utilisation de Selector pour des rebuilds ciblés.

---

## 2. Auto-refresh Timer

### Configuration
```dart
void startAutoRefresh({Duration interval = const Duration(seconds: 30)}) {
  _refreshTimer?.cancel();
  _refreshTimer = Timer.periodic(interval, (_) => refresh());
}
```
✅ 30 secondes est raisonnable pour une app mobile.
✅ Timer annulé dans dispose().

### Double démarrage potentiel
main.dart:initState appelle startAutoRefresh() UNE fois.
Si DashboardScreen.initState appelait aussi startAutoRefresh, il y aurait deux timers.
Vérification: DashboardScreen n'appelle PAS startAutoRefresh → ✅ OK.

---

## 3. Memory Leaks

### Streams

#### WebSocketService._controller
```dart
final _controller = StreamController<Map<String, dynamic>>.broadcast();
```
✅ Fermé dans dispose() via disconnect() → _controller.close().
✅ Broadcast stream — plusieurs listeners peuvent s'abonner sans leak.

#### SSE streamMissionLogs
```dart
final client = http.Client();
try { ... }
finally { client.close(); }
```
✅ http.Client fermé dans finally même si erreur.

### TextEditingControllers
Vérifiés dans:
- MissionScreen: _controller.dispose() et _focus.dispose() ✅
- SettingsScreen: _urlCtrl.dispose() et _tokenCtrl.dispose() ✅
- DashboardScreen._SettingsSheet: _hostCtrl.dispose() et _portCtrl.dispose() ✅

### TabController (ActionsScreen)
```dart
@override
void dispose() {
  _tabs.dispose();
  super.dispose();
}
```
✅ Correctement disposé.

---

## 4. Opérations Longues sur le Main Thread

### _parse() — Decode JSON synchrone
```dart
Map<String, dynamic> _parse(http.Response resp) {
  final body = utf8.decode(resp.bodyBytes);
  final decoded = jsonDecode(body);
```
Pour de grandes listes de missions (100+), jsonDecode peut être lent sur main thread.
Fix potentiel: utiliser compute() pour les gros payloads.
Actuellement non critique (peu de missions en pratique).

### ScoreChart — CustomPainter
Le painter recalcule toutes les coordonnées à chaque repaint.
Pour max 10 points (scores list length > 10 → sublist), calcul trivial.
✅ Performance correcte.

---

## 5. Dépendances Inutilisées

### flutter_secure_storage déclaré mais non utilisé
```yaml
flutter_secure_storage: ^9.0.0  # dans pubspec.yaml
```
JWT stocké dans SharedPreferences, pas dans secure storage.
→ Poids APK augmenté inutilement (+1.5MB environ).

### web_socket_channel déclaré mais non utilisé
```yaml
web_socket_channel: ^2.4.0  # dans pubspec.yaml
```
Code utilise dart:io WebSocket directement.
→ Dépendance incluse mais jamais importée dans le code.

### intl déclaré mais usage minimal
```yaml
intl: ^0.19.0  # dans pubspec.yaml
```
Aucun import visible dans les fichiers Dart audités.
Si uniquement pour les dates: les _formatDate() utilisent DateTime natif.

---

## 6. Récapitulatif Issues Performance

| ID | Sévérité | Description |
|----|----------|-------------|
| P8.1 | 🟡 FAIBLE | 4-5 notifyListeners en cascade par refresh (×9 screens mountés) |
| P8.2 | 🟡 FAIBLE | ScoreChart shouldRepaint par référence |
| P8.3 | 🟡 FAIBLE | flutter_secure_storage inclus mais inutilisé (+taille APK) |
| P8.4 | 🟡 FAIBLE | web_socket_channel inclus mais inutilisé |
| P8.5 | 🟢 OK | Pas de memory leak détecté |
| P8.6 | 🟢 OK | Auto-refresh 30s correct |
| P8.7 | 🟢 OK | Tous les dispose() corrects |
