# VERDICT FINAL — Flutter Audit JarvisMax
**Date:** 2026-03-27 | **Auditeur:** Claude Sonnet 4.6 | **App:** v1.0.0+1

---

## 1. Qualité Architecture Globale

### Score: 7/10

L'architecture Flutter de JarvisMax est **solide pour sa taille et son objectif**.
Le pattern Provider (ChangeNotifier) est bien appliqué. Les modèles sont défensifs
(null-safety, parseFloat pour timestamps Unix). La séparation en services/screens/models
est claire.

Les principaux problèmes architecturaux sont:
- ApiService trop monolithique (réseau + état + timer dans un seul fichier de 500+ lignes)
- 9 onglets bottom nav (trop pour mobile)
- Credentials hardcodés (problème de sécurité grave)

---

## 2. Alignement Backend

### Score: 8/10

Sur 20 endpoints Flutter, 16 sont correctement alignés avec le backend.
4 problèmes:
- /api/image/generate → doit être /api/multimodal/image (404)
- /api/v2/status ne retourne pas le champ 'mode' → toujours 'AUTO'
- /api/mcp/list inexistant (méthode non appelée → pas d'impact utilisateur)
- Sémantique actions/missions confuse (/api/v2/tasks retourne des missions)

Le parsing JSON est robuste avec de nombreux fallbacks défensifs.

---

## 3. APK Readiness Level: 52%

### Décomposition

| Critère | Poids | Score | Points |
|---------|-------|-------|--------|
| Build compile | 20% | 85% | 17/20 |
| Endpoints corrects | 15% | 80% | 12/15 |
| Sécurité | 20% | 10% | 2/20 |
| UX fonctionnelle | 15% | 70% | 10.5/15 |
| Performance | 10% | 75% | 7.5/10 |
| Signing config | 10% | 30% | 3/10 |
| Error handling | 10% | 65% | 6.5/10 |
| **TOTAL** | **100%** | **52%** | |

Le score de sécurité (10%) est principalement plombé par les credentials hardcodés.
Le signing config (30%) reflète l'utilisation de la clé debug pour le release.

---

## 4. Issues Bloquantes (avant release utilisateur)

### 🔴 BLOQUANT 1 — Credentials hardcodés
**Fichier:** api_service.dart:_loadJwt()
**Problème:** `await login('admin', 'JarvisSecretKey2026!');` est visible en clair dans l'APK.
**Fix:** Supprimer l'auto-login ou demander les credentials à l'utilisateur.

### 🔴 BLOQUANT 2 — Signing config debug pour release
**Fichier:** android/app/build.gradle
**Problème:** `signingConfig = signingConfigs.debug` pour le buildType release.
**Fix:** Créer un keystore de production et configurer le release signing.

### 🟠 IMPORTANT 3 — Endpoint /api/image/generate → 404
**Fichier:** api_service.dart:generateImage()
**Problème:** L'endpoint est /api/multimodal/image sur le backend.
**Fix:** Changer l'URL dans generateImage().

### 🟠 IMPORTANT 4 — Messages d'erreur avec encoding corrompu
**Fichier:** api_service.dart:_friendly()
**Problème:** 'DÃ©lai dÃ©passÃ©' etc. s'afficheront avec des caractères dégradés.
**Fix:** Ré-encoder les strings accentuées en UTF-8.

### 🟠 IMPORTANT 5 — Bouton "Approuver" mort dans SelfImprovementScreen
**Fichier:** self_improvement_screen.dart
**Problème:** onPressed: null → bouton affiché mais non fonctionnel.
**Fix:** Implémenter l'action ou masquer le bouton.

### 🟠 IMPORTANT 6 — Mauvaise clé planStep dans MissionDetailScreen
**Fichier:** mission_detail_screen.dart:_PlanStepCard
**Problème:** Utilise 'description' au lieu de 'task' comme clé primaire du plan step.
**Fix:** Ajouter 'task' en premier dans la chaîne de fallback.

---

## 5. Fixes Recommandés Avant Release

### Fix 1 — Supprimer credentials hardcodés
```dart
// AVANT (api_service.dart:_loadJwt)
await login('admin', 'JarvisSecretKey2026!');

// APRÈS — supprimer cette ligne, l'utilisateur configurera son token via SettingsScreen
// Le token sera absent → l'app affichera une erreur d'auth → l'utilisateur saisit son token
```

### Fix 2 — Corriger endpoint image
```dart
// AVANT
final raw = await _post('/api/image/generate', {'prompt': prompt});
// APRÈS
final raw = await _post('/api/multimodal/image', {'prompt': prompt});
```

### Fix 3 — Fix encoding UTF-8 dans _friendly()
Réouvrir api_service.dart dans un éditeur configuré UTF-8 et corriger les chaînes corrompues.

### Fix 4 — Fix planStep dans MissionDetailScreen
```dart
// AVANT (_PlanStepCard)
final desc = step['description'] as String? ??
    step['action'] as String? ??
    step.toString();

// APRÈS
final desc = step['task']?.toString() ??
    step['description']?.toString() ??
    step['action']?.toString() ??
    step.toString();
```

### Fix 5 — Activer ou masquer le bouton Approuver
```dart
// SelfImprovementScreen — changer onPressed: null en:
onPressed: () {
  // TODO: Implémenter approbation auto-amélioration
  ScaffoldMessenger.of(context).showSnackBar(
    const SnackBar(content: Text('Suggestion approuvée')),
  );
  onDismiss();
},
```

---

## 6. Résumé Issues par Criticité

| Criticité | Count | Exemples |
|-----------|-------|---------|
| 🔴 BLOQUANT | 2 | Credentials hardcodés, Signing debug |
| 🟠 IMPORTANT | 4 | Image endpoint 404, Encoding, Bouton mort, PlanStep key |
| 🟡 MOYEN | 8 | WS non consommé, SSE non utilisé, Double refresh, 9 nav items... |
| 🟢 MINEUR | 6 | score_bar.dart, getMCPList(), intl inutilisé... |

**Total: 20 issues identifiées**

---

## 7. Verdict Final

L'application JarvisMax Flutter est **fonctionnellement avancée** pour un projet solo:
- Interface complète (9 screens bien intégrés)
- Models robustes avec défenses null-safety
- Gestion offline/online correcte
- Le pattern approval/mission est bien implémenté

Mais **deux blockers critiques** empêchent un release sécurisé:
1. Les credentials admin hardcodés (sécurité)
2. Le signing debug pour le release build (distribution)

**Après correction des 2 blockers + 4 importants: APK readiness estimée à ~78%.**
