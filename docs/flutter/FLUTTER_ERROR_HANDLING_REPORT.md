# PART 7 — Flutter Error Handling Report
**Date:** 2026-03-27 | **App:** JarvisMax v1.0.0+1

---

## 1. Stratégie de Gestion d'Erreurs

### Niveau HTTP (_parse)
```dart
Map<String, dynamic> _parse(http.Response resp) {
  try {
    final body = utf8.decode(resp.bodyBytes);
    final decoded = jsonDecode(body);
    final json = decoded is Map<String, dynamic>
        ? decoded
        : <String, dynamic>{'data': decoded};
    if (resp.statusCode >= 400) {
      throw Exception(
        json['error']?.toString() ??
        json['detail']?.toString() ??
        'HTTP ${resp.statusCode}',
      );
    }
    return json;
  } on FormatException {
    throw Exception('Réponse invalide du serveur (HTTP ${resp.statusCode})');
  }
}
```
✅ FormatException catchée → message lisible.
✅ Extraction erreur depuis json['error'] ou json['detail'] (FastAPI format).
✅ Encapsule les JSON array en {data: list} → pas de crash sur réponse liste.

### Niveau ApiResult
```dart
try {
  // ...opération...
  return ApiResult.success(data);
} catch (e) {
  _lastError = _friendly(e);
  notifyListeners();
  return ApiResult.failure(_lastError);
}
```
✅ Aucune exception n'échappe vers les screens.
✅ Tous les screens vérifient result.ok avant d'utiliser result.data.

### _friendly() — Messages utilisateur
```dart
String _friendly(Object e) {
  final msg = e.toString();
  if (msg.contains('SocketException') || msg.contains('Connection refused')) {
    return 'Impossible de joindre le serveur Jarvis.\nVérifiez que l\'API tourne sur $_base';
  }
  if (msg.contains('TimeoutException')) {
    return 'Délai dépassé. Le serveur ne rÃ©pond pas.';
  }
  return msg.replaceFirst('Exception: ', '');
}
```
✅ Messages human-friendly pour les cas courants.
⚠️ PROBLÈME D'ENCODING: 'rÃ©pond' → caractère 'é' mal encodé dans la source.
   'DÃ©lai dÃ©passÃ©' → trois occurrences de mauvais encoding.
   Ces chaînes s'afficheront avec des caractères corrompus sur Android.

---

## 2. Backend Unavailable

### checkHealth() — Double fallback
```dart
for (final path in ['/health', '/']) {
  try {
    final resp = await http.get(Uri.parse('$_base$path'), ...).timeout(8s);
    if (resp.statusCode >= 200 && resp.statusCode < 300) {
      _status = _status.copyWith(isOnline: true);
      _isChecking = false;
      return true;
    }
  } catch (_) { continue; }
}
_status = _status.copyWith(isOnline: false);
```
✅ Essaie /health puis / avant de déclarer offline.
✅ isChecking utilisé pour afficher spinner initial.

### UI Offline
```dart
// Full screen offline state (pas de données cache)
if (!api.status.isOnline && api.missions.isEmpty && api.actions.isEmpty) {
  return _OfflineState(onRetry: api.refresh);
}
// Banner offline mais données en cache affichées
if (!api.status.isOnline)
  _OfflineBanner(onRetry: api.refresh),
```
✅ Deux niveaux d'état offline bien gérés.
✅ Bouton "RÉESSAYER" visible.

---

## 3. Erreurs d'Encoding dans les Messages

**Fichier:** api_service.dart:_friendly()
```dart
// Lignes avec mauvais encoding UTF-8 (probablement édité en latin-1 puis re-sauvé)
return 'DÃ©lai dÃ©passÃ©. Le serveur ne rÃ©pond pas.';
// Devrait être:
return 'Délai dépassé. Le serveur ne répond pas.';
```
Ces caractères dégradés viennent d'un problème d'encoding lors d'une édition.
Le fichier commence par un BOM UTF-8 (\xEF\xBB\xBF visible dans le diff).

**CRITIQUE (qualité):** Les messages d'erreur afficheront des caractères corrompus.
Fix: Ré-encoder correctement les commentaires et messages avec caractères accentués.

---

## 4. Timeouts

| Opération | Timeout | Correct |
|-----------|---------|---------|
| GET général | 8 secondes | ✅ Raisonnable |
| POST général | 15 secondes | ✅ Correct pour missions longues |
| Login | 10 secondes | ✅ OK |
| checkHealth | 8 secondes | ✅ OK |
| WS connect | 5 secondes | ✅ OK |
| SSE stream | Aucun | ⚠️ Risque de hang indefini si stream ne finit pas |

---

## 5. Crashs UI

### mounted checks
```dart
if (!mounted) return;
setState(() => _sending = false);
```
✅ Tous les callbacks async vérifient mounted avant setState.
✅ Aucun setState sur widget démonté détecté.

### Null safety
Models utilisent des helpers défensifs:
```dart
static String _s(dynamic v, [String d = '']) => v?.toString() ?? d;
static double _d(dynamic v, [double d = 0.0]) => double.tryParse(v?.toString() ?? '') ?? d;
```
✅ Aucun crash null possible dans les modèles.

---

## 6. Récapitulatif Issues Error Handling

| ID | Sévérité | Description |
|----|----------|-------------|
| E7.1 | 🔴 CRITIQUE | Credentials hardcodés ('admin', 'JarvisSecretKey2026!') dans _loadJwt() |
| E7.2 | 🟠 MOYEN | Mauvais encoding UTF-8 dans _friendly() → messages corrompus |
| E7.3 | 🟡 FAIBLE | SSE stream sans timeout → risque de hang |
| E7.4 | 🟢 OK | checkHealth double fallback |
| E7.5 | 🟢 OK | mounted checks présents |
| E7.6 | 🟢 OK | Null safety défensive dans les modèles |

---

## 7. Fix Critique: Credentials Hardcodés

### Problème
```dart
// api_service.dart:_loadJwt() — LIGNE À SUPPRIMER
await login('admin', 'JarvisSecretKey2026!');
```
Le mot de passe admin est visible en clair dans l'APK. N'importe qui peut extraire
le secret avec `strings app.apk | grep Jarvis`.

### Fix recommandé
Supprimer l'auto-login silencieux. L'utilisateur doit saisir ses identifiants.
Ou: charger les credentials depuis un fichier de config sécurisé non versionné.
Minimum: passer par flutter_secure_storage qui est déjà déclaré en dépendance.
