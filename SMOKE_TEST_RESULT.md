# SMOKE_TEST_RESULT.md — Jarvis Max Mobile
_Cycle 19 — Week 3 device validation_
_APK built: 2026-04-03 — app-debug.apk (~90 MB)_

---

## Build status

| Step | Result |
|------|--------|
| `flutter build apk --debug` | ✅ SUCCESS |
| APK path | `jarvismax_app/build/app/outputs/flutter-apk/app-debug.apk` |
| APK size | ~90 MB (debug) |
| Compilation errors | None |
| gradle.properties fix | Removed Linux-only `org.gradle.java.home` — now cross-platform |

---

## Device test checklist

> Fill in results after installing the APK on a real Android device or emulator.
> Server target: `https://jarvis.jarvismaxapp.co.uk` (production, default)
> Or use Tailscale `100.109.1.124:8000` for local VPN access.

### 1. Auth

| Test | Expected | Result |
|------|----------|--------|
| App opens → Login screen shows | French UI: "Entrez votre token d'accès…" | ⬜ |
| Enter invalid token → error | "Token invalide. Vérifiez et réessayez." | ⬜ |
| Enter valid token → Home screen | Tab bar: Accueil / Missions / Approbations / Historique / Paramètres | ⬜ |
| "Se souvenir de moi" checked → reopen app | Auto-login, skips login screen | ⬜ |

### 2. Home screen — task type selector

| Test | Expected | Result |
|------|----------|--------|
| Chip bar visible below greeting | 17 chips: Libre + 16 business types | ⬜ |
| Tap "Recherche marché" | Chip highlights blue, composer shows badge "Recherche marché" | ⬜ |
| Tap active chip again | Chip deselects, badge disappears | ⬜ |
| System status shown | "En ligne" / "Hors ligne" with correct color | ⬜ |
| Recent missions list renders | Shows last missions with status pills | ⬜ |

### 3. Mission submission

| Test | Expected | Result |
|------|----------|--------|
| Select "Recherche marché" + enter "Marché des outils IA en France" + tap Lancer | `[market_research] Marché des outils IA en France` sent to backend | ⬜ |
| Mission appears in list with status "En cours" | Spinner / pending state visible | ⬜ |
| Mission reaches COMPLETED | Status pill turns green "Terminé" | ⬜ |
| "Libre" mode: plain text goal sent without prefix | Goal text not prefixed with `[...]` | ⬜ |

### 4. Mission detail + result export

| Test | Expected | Result |
|------|----------|--------|
| Tap completed mission → detail screen | Full result text visible | ⬜ |
| Tap "Copier" button next to "Réponse de Jarvis" | Snackbar "Résultat copié" — clipboard contains result | ⬜ |
| Long result renders without overflow | Scrollable, no truncation | ⬜ |

### 5. Approbations tab

| Test | Expected | Result |
|------|----------|--------|
| Submit a mission that triggers approval gate | Appears in Approbations tab as "EN ATTENTE" | ⬜ |
| Tap "Approuver" | Snackbar "Approuvé", card moves to resolved | ⬜ |
| Tap "Refuser" | Snackbar "Refusé", card moves to resolved | ⬜ |
| No pending approvals → empty state | "Tout est bon" message | ⬜ |

### 6. Paramètres → Panneau Admin

| Test | Expected | Result |
|------|----------|--------|
| Tap Paramètres tab | French labels: Serveur / WebSocket / Adresse | ⬜ |
| Tap "Panneau Admin" | Admin panel loads | ⬜ |
| Health banner shows | Green = "Système OK", amber = "Dégradé", red = "Critique" | ⬜ |
| Mission stats show | Soumises / Réussies / Échouées counts | ⬜ |
| Cost today shows | USD cost with color coding | ⬜ |
| Refresh button works | Data reloads without error | ⬜ |

### 7. WebSocket real-time updates

| Test | Expected | Result |
|------|----------|--------|
| Submit mission → stay on Home | Mission list updates automatically when status changes | ⬜ |
| WebSocket status in Paramètres | "Actif" (green) when connected | ⬜ |

---

## Issues found

> Record any bugs, unexpected behavior, or UX friction here.

| # | Screen | Description | Severity |
|---|--------|-------------|----------|
| — | — | — | — |

---

## Sign-off

| | |
|---|---|
| Tested by | |
| Device | |
| Android version | |
| Server | production / tailscale / local |
| Date | |
| Overall result | ⬜ PASS  ⬜ FAIL  ⬜ PARTIAL |

---

_Next after passing: first internal user session (founder feedback)._
