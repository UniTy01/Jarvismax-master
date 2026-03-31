# PART 10 — Flutter Build Readiness Report
**Date:** 2026-03-27 | **App:** JarvisMax v1.0.0+1

---

## 1. pubspec.yaml — Analyse

### Version
```yaml
version: 1.0.0+1
environment:
  sdk: ^3.6.2
```
✅ SDK Flutter 3.6.2+ requis (null-safety complet).
✅ Version applicative correcte pour un premier release.

### Dépendances déclarées
```yaml
dependencies:
  flutter: sdk: flutter
  http: ^1.2.0                    # ✅ Utilisé
  shared_preferences: ^2.2.3     # ✅ Utilisé
  provider: ^6.1.2               # ✅ Utilisé
  intl: ^0.19.0                  # ⚠️ Potentiellement inutilisé
  web_socket_channel: ^2.4.0     # ❌ Non utilisé (dart:io WebSocket à la place)
  flutter_secure_storage: ^9.0.0 # ❌ Non utilisé (JWT dans SharedPrefs)
```

### Issues dépendances
- web_socket_channel: déclaré mais code utilise dart:io WebSocket → dépendance orpheline
- flutter_secure_storage: déclaré mais JWT stocké dans SharedPreferences → sécurité dégradée
- intl: pas d'import visible dans le code audité → peut-être transitif

---

## 2. android/app/build.gradle — Analyse

```gradle
android {
  namespace = "com.jarvismax.jarvismax_app"
  compileSdk = flutter.compileSdkVersion
  minSdk = flutter.minSdkVersion        // généralement 21 (Android 5.0)
  targetSdk = flutter.targetSdkVersion  // dépend de la version Flutter

  buildTypes {
    release {
      // TODO: Add your own signing config for the release build.
      signingConfig = signingConfigs.debug  // ⚠️ DEBUG KEY EN RELEASE
    }
  }
}
```

### Problèmes critiques build

#### B10.1 — signingConfig debug en release (BLOQUANT POUR PUBLICATION)
```gradle
signingConfig = signingConfigs.debug
```
Commentaire TODO présent dans le fichier. L'APK release sera signé avec la clé debug.
- APK fonctionnel pour tests
- Impossible de publier sur Google Play avec la clé debug
- L'APK ne sera pas accepté par certains MDM en entreprise

Fix obligatoire avant publication:
```gradle
signingConfigs {
  release {
    keyAlias keystoreProperties['keyAlias']
    keyPassword keystoreProperties['keyPassword']
    storeFile file(keystoreProperties['storeFile'])
    storePassword keystoreProperties['storePassword']
  }
}
buildTypes {
  release {
    signingConfig signingConfigs.release
    minifyEnabled true
    shrinkResources true
    proguardFiles getDefaultProguardFile('proguard-android.txt'), 'proguard-rules.pro'
  }
}
```

---

## 3. AndroidManifest.xml — Permission INTERNET

### Vérification requise
Pour les requêtes HTTP/HTTPS et WebSocket, l'app DOIT déclarer:
```xml
<uses-permission android:name="android.permission.INTERNET" />
```
Flutter ajoute généralement cette permission automatiquement via le plugin http,
mais il faut VÉRIFIER que AndroidManifest.xml la contient explicitement.

---

## 4. Null Safety

### Analyse
Tous les fichiers Dart utilisent la syntaxe null-safe (operateurs ?, ??, ??=, !).
Helpers défensifs dans les modèles:
```dart
static String _s(dynamic v, [String d = '']) => v?.toString() ?? d;
static double _d(dynamic v, [double d = 0.0]) => double.tryParse(v?.toString() ?? '') ?? d;
```
✅ Null safety correctement implémentée.
✅ Pas de late variables non initialisées détectées.

---

## 5. Warnings Potentiels

### 1. withOpacity deprecated → withValues(alpha:)
Le code utilise déjà la nouvelle API:
```dart
color.withValues(alpha: 0.15)  // ✅ Nouveau
```
✅ Pas de warnings withOpacity.

### 2. Caractères encodage corrompus dans api_service.dart
```dart
return 'DÃ©lai dÃ©passÃ©. Le serveur ne rÃ©pond pas.';
```
Ce n'est pas un warning Dart, mais ces chaînes seront affichées corrompues.

---

## 6. Récapitulatif Build Readiness

| ID | Sévérité | Description | Bloquant Release |
|----|----------|-------------|-----------------|
| B10.1 | 🔴 CRITIQUE | signingConfig debug pour release build | ✅ Oui (publication) |
| B10.2 | 🟠 MOYEN | flutter_secure_storage inutilisé (+APK size) | Non |
| B10.3 | 🟠 MOYEN | web_socket_channel inutilisé | Non |
| B10.4 | 🟡 FAIBLE | intl potentiellement inutilisé | Non |
| B10.5 | 🟡 FAIBLE | Vérifier INTERNET permission dans AndroidManifest | Possible |
| B10.6 | 🟢 OK | Null safety complète | N/A |
| B10.7 | 🟢 OK | withValues(alpha) utilisé (pas de withOpacity) | N/A |

---

## 7. Score APK Readiness

| Critère | Score |
|---------|-------|
| Compile sans erreur | 9/10 (supposition — encoding warnings) |
| Null safety | 10/10 |
| Dépendances valides | 7/10 (2 inutilisées, 1 non utilisée) |
| Signing config | 3/10 (debug key en release) |
| Sécurité credentials | 2/10 (hardcoded password) |
| Android permissions | 8/10 (à vérifier) |
| **Total estimé** | **65/100** |
