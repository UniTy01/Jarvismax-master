# PART 6 — Flutter Realtime Report (WebSocket + SSE)
**Date:** 2026-03-27 | **App:** JarvisMax v1.0.0+1

---

## 1. Architecture Temps-Réel

### Deux mécanismes disponibles
1. **WebSocket** (/ws/stream) — global, toutes notifications système
2. **SSE** (/api/v1/missions/{id}/stream) — ciblé, événements d'une mission spécifique
3. **Auto-refresh polling** (30s interval) — fallback pour les données statiques

---

## 2. Analyse WebSocketService

### Implémentation
```dart
// dart:io WebSocket direct — PAS web_socket_channel
_socket = await WebSocket.connect(uri)
    .timeout(const Duration(seconds: 5));
```

### Connexion et reconnexion
```dart
void _onDisconnect() {
  if (_connected) {
    _connected = false;
    notifyListeners();
  }
  _reconnectTimer?.cancel();
  _reconnectTimer = Timer(const Duration(seconds: 3), connect);
}
```

### Problèmes identifiés

#### P6.1 — dart:io WebSocket inutilisable sur Flutter Web
dart:io n'est pas disponible sur Flutter Web. Si l'app est portée sur web, le WS
sera entièrement cassé. pubspec.yaml déclare web_socket_channel (multi-plateforme)
mais le code utilise dart:io WebSocket directement.
Fix: Migrer vers web_socket_channel.WebSocketChannel.

#### P6.2 — Pas de backoff exponentiel
Reconnexion fixe à 3 secondes quelle que soit la cause de déconnexion.
Si le backend est down, l'app tentera de se reconnecter indéfiniment toutes les 3s.
Recommandation: Backoff exponentiel (3s, 6s, 12s, max 60s).

#### P6.3 — Pas de protection contre les événements dupliqués
Aucun mécanisme de déduplication des événements WS.
Si la reconnexion arrive pendant qu'un événement est en transit, il peut être
reçu deux fois.

#### P6.4 — URL WS depuis baseUrl avec remplacement de schème
```dart
final wsUrl = baseUrl
    .replaceFirst('http://', 'ws://')
    .replaceFirst('https://', 'wss://');
```
✅ Logique correcte.
⚠️ Si baseUrl contient un chemin (ex: http://host:8000/api), le remplacement
produira ws://host:8000/api/ws/stream — chemin double /api.
En pratique baseUrl = 'http://host:port' sans chemin → OK actuellement.

#### P6.5 — Token en query param dans URL WS
```dart
final uri = '$wsUrl/ws/stream${token.isNotEmpty ? "?token=$token" : ""}';
```
⚠️ Token JWT dans l'URL est exposé dans les logs serveur et proxies intermédiaires.
Recommandation: Envoyer le token via le premier message WebSocket ou via header
Authorization lors de l'upgrade HTTP→WS (si le backend le supporte).

---

## 3. Analyse SSE (streamMissionLogs)

### Implémentation
```dart
Stream<Map<String, dynamic>> streamMissionLogs(String missionId, {int maxRetries = 5}) async* {
  int attempt = 0;
  while (attempt <= maxRetries) {
    final client = http.Client();
    bool receivedDone = false;
    try {
      final req = http.Request('GET', Uri.parse('$_base/api/v1/missions/$missionId/stream'));
      req.headers['Accept'] = 'text/event-stream';
      // ...
      await for (final chunk in resp.stream.transform(utf8.decoder).transform(LineSplitter())) {
        if (chunk.startsWith('data: ')) { buf = chunk.substring(6); }
        else if (chunk.isEmpty && buf.isNotEmpty) { yield jsonDecode(buf); }
      }
    } catch (_) {}
    // ...
    attempt++;
    await Future.delayed(const Duration(seconds: 2));
  }
}
```

### Points positifs
✅ Auto-reconnect avec maxRetries configurable
✅ Détection de l'événement 'done'/'timeout' pour arrêter la stream proprement
✅ Fermeture du client HTTP dans finally

### Problèmes
#### P6.6 — streamMissionLogs() jamais appelé depuis un screen
La méthode est implémentée mais aucun screen ne l'utilise.
MissionScreen._send() utilise un Future.delayed(2s) au lieu du SSE stream.
Fix: Connecter streamMissionLogs à MissionScreen pour afficher la progression.

---

## 4. Utilisation du WebSocket dans les Screens

### MissionScreen affiche un indicateur WS
```dart
Consumer<WebSocketService>(
  builder: (_, ws, __) => Container(
    // Point vert/gris + "WS" label
    color: ws.isConnected ? JvColors.green : JvColors.textMut,
  ),
)
```
✅ Feedback visuel de la connexion WS.

### Aucun screen ne consomme les events WebSocket
Le stream `wsService.stream` est créé mais aucun screen ne s'y abonne.
Les événements temps-réel du backend (mission_update, action_pending, etc.)
ne déclenchent PAS de refresh de l'UI.

---

## 5. Résumé Issues Temps-Réel

| ID | Sévérité | Description |
|----|----------|-------------|
| P6.1 | 🟡 FAIBLE | dart:io WS inutilisable sur Flutter Web (pas ciblé actuellement) |
| P6.2 | 🟡 FAIBLE | Pas de backoff exponentiel reconnexion |
| P6.3 | 🟡 FAIBLE | Pas de déduplication events WS |
| P6.4 | 🟢 OK | URL construction correcte |
| P6.5 | 🟡 FAIBLE | Token JWT exposé dans URL WS |
| P6.6 | 🔴 IMPORTANT | streamMissionLogs jamais utilisé — SSE non exploité |
| P6.7 | 🔴 IMPORTANT | WS stream non consommé — events temps-réel perdus |

---

## 6. Recommandations

1. Abonner ActionsScreen/DashboardScreen au wsService.stream pour déclencher refresh sur événements
2. Connecter streamMissionLogs dans MissionScreen pour suivi temps-réel
3. Implémenter backoff exponentiel dans WebSocketService._onDisconnect
4. Migrer de dart:io WebSocket vers web_socket_channel pour portabilité
