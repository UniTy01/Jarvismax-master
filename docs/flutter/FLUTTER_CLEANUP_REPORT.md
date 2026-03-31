# PART 11 — Flutter Cleanup Report
**Date:** 2026-03-27 | **App:** JarvisMax v1.0.0+1

---

## 1. Dead Code

### 1.1 score_bar.dart — Fichier re-export inutile
```dart
// lib/widgets/score_bar.dart — CONTENU COMPLET DU FICHIER:
export '../widgets/cyber_card.dart' show ScoreBar;
```
Ce fichier n'est qu'un re-export de ScoreBar depuis cyber_card.dart.
ScoreBar est déjà défini directement dans cyber_card.dart.
Action: Supprimer score_bar.dart. Les imports vers score_bar.dart doivent pointer vers cyber_card.dart.
Vérifier qu'aucun screen importe score_bar.dart directement.

### 1.2 getMCPList() — Méthode jamais appelée
```dart
// api_service.dart
Future<ApiResult<List<Map<String, dynamic>>>> getMCPList() async {
  try {
    final raw = await _get('/api/mcp/list');
    // ...
  }
}
```
Aucun screen n'appelle getMCPList(). L'endpoint /api/mcp/list n'existe pas au backend.
Action: Supprimer getMCPList() ou créer l'endpoint correspondant.

### 1.3 autoLogin() — Logique redondante avec _loadJwt()
```dart
Future<void> autoLogin() async {
  if (_jwtToken.isNotEmpty) return; // token déjà chargé par _loadJwt
  final prefs = await SharedPreferences.getInstance();
  final stored = prefs.getString('jwt_token') ?? '';
  if (stored.isNotEmpty) {
    _jwtToken = stored;
    notifyListeners();
  }
  // Pas de login supplémentaire ici — _loadJwt() gère le login initial
}
```
Cette méthode est un doublon partiel de _loadJwt(). Elle est appelée depuis
DashboardScreen.initState mais ne fait rien si _loadJwt() a déjà tout chargé.
Action: Supprimer autoLogin() ou le documenter comme no-op garanti après init.

---

## 2. Imports Potentiellement Inutilisés

### shared_preferences dans dashboard_screen.dart
DashboardScreen n'importe pas SharedPreferences directement (c'est ApiConfig/ApiService qui le font).
À vérifier: aucun import de shared_preferences visible dans le fichier.

### intl dans pubspec.yaml
```yaml
intl: ^0.19.0
```
Aucun import de 'package:intl/intl.dart' visible dans les fichiers audités.
Les formatages de dates utilisent DateTime natif Dart.
Action: Supprimer intl de pubspec.yaml si non utilisé ailleurs.

---

## 3. Boutons Non Fonctionnels

### 3.1 Bouton "Approuver" dans SelfImprovementScreen
```dart
OutlinedButton(
  onPressed: null,  // ← BOUTON MORT
  style: OutlinedButton.styleFrom(
    foregroundColor: JvColors.green,
    side: const BorderSide(color: JvColors.green),
  ),
  child: const Text('Approuver'),
),
```
Ce bouton est visible mais ne fait rien. L'utilisateur peut penser que c'est un bug.
Action: Implémenter l'action ou remplacer par un Text si intentionnellement désactivé.

### 3.2 Agent toggles dans SettingsScreen
```dart
Switch(
  value: enabled,
  onChanged: id.isEmpty
      ? null
      : (v) => setState(() => _agentEnabled[id] = v),  // ← SETSTATE SEUL
  activeColor: JvColors.cyan,
),
```
Le switch change l'état local _agentEnabled[id] mais ne fait aucun appel API.
Action: Ajouter appel API pour enable/disable agent ou supprimer les switches.

---

## 4. Données Hardcodées (Mock Data)

### 4.1 Suggestions de mission hardcodées
```dart
static const _suggestions = [
  'Analyser les logs du système',
  'Créer un rapport de performance',
  // ...
];
```
Ces suggestions sont statiques et ne reflètent pas les missions passées de l'utilisateur.
Non bloquant mais amélioration possible.

### 4.2 Profil Tailscale hardcodé
```dart
// dashboard_screen.dart _SettingsSheet
static const _tailscaleIp = '100.109.1.124';
```
Cette IP est spécifique à la machine de développement.
Action: Rendre cette valeur configurable (ou documentée comme valeur personnelle à changer).

### 4.3 URL Local hardcodée dans SettingsScreen et DashboardSheet
```dart
onPressed: () => _urlCtrl.text = 'http://192.168.129.20:8000',
```
IP locale personnelle hardcodée dans l'UI.
Non bloquant pour l'utilisateur final (il peut changer l'URL).

### 4.4 Descriptions d'agents hardcodées dans CapabilitiesScreen
```dart
static const _agentDescriptions = {
  'scout-research':  'Recherche et analyse d\'informations',
  'forge-builder':   'Génération et modification de code',
  // ...
};
```
Ces descriptions ne viennent pas du backend. Si de nouveaux agents sont ajoutés,
leurs descriptions ne s'afficheront pas.

---

## 5. Commentaires avec Encoding Corrompu

Plusieurs commentaires dans api_service.dart contiennent des caractères mal encodés:
```dart
/// Auto-login: utilise le token stockÃ© (dÃ©jÃ  chargÃ© par _loadJwt au dÃ©marrage).
/// Si le token est absent, _loadJwt() a dÃ©jÃ  tentÃ© un login â†' pas de doublon.
```
Ces commentaires ne causent pas d'erreur de compilation mais dégradent la lisibilité.

---

## 6. Récapitulatif Cleanup

| Priorité | Action | Fichier |
|----------|--------|---------|
| 🔴 HAUTE | Fix bouton "Approuver" mort | self_improvement_screen.dart |
| 🟠 MOYEN | Fix encoding UTF-8 commentaires/messages | api_service.dart |
| 🟡 FAIBLE | Supprimer score_bar.dart | widgets/ |
| 🟡 FAIBLE | Supprimer getMCPList() ou créer endpoint | api_service.dart |
| 🟡 FAIBLE | Supprimer web_socket_channel de pubspec | pubspec.yaml |
| 🟡 FAIBLE | Supprimer intl si inutilisé | pubspec.yaml |
| 🟢 OPTIONNEL | Rendre les profils IP configurables | settings_screen.dart |
| 🟢 OPTIONNEL | Charger descriptions agents depuis backend | capabilities_screen.dart |
