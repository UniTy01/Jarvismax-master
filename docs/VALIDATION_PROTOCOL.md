# JARVIS MAX — Protocole de Validation (Phase 4)

## Tests automatiques

### Sans dépendances externes (sans Docker ni LLM)

```bash
# Depuis le répertoire jarvismax/
python3 tests/validate.py
```

Les tests couvrent :
- Unicité de RiskLevel (source unique dans core/state.py)
- TaskRouter : 9 patterns de routing + mode explicite
- RiskEngine : 19 cas de classification + bulk + highest_risk
- ActionSpec : sérialisation to_dict() + brief()
- JarvisSession : attributs déclarés + set/get_output + summary_dict
- VaultMemory : isolation d'instances (pas d'attribut de classe partagé)
- Executor : whitelist (13 OK) + blacklist (3 bloquées)
- SelfImprove : fichiers protégés (4 interdits + 1 autorisé)
- Telegram : TTL validations (15 min)
- LLMFactory : LOCAL_ONLY_ROLES chain + fallback director

### Résultats attendus
```
BILAN : 50+ PASS | 0 FAIL
```

---

## Protocole de validation humaine progressive (6 étapes)

### ETAPE 1 — Démarrage en DRY_RUN
```bash
# .env
DRY_RUN=true
```
Jarvis analyse et prépare TOUT, n'exécute RIEN.  
Valide que le routing, les agents et les prompts fonctionnent.

### ETAPE 2 — Test /auto simple
```
/auto Analyse l'état du workspace et donne-moi un résumé
```
- Attendu : message de plan, résultats agents, rapport final
- Aucune action exécutée (DRY_RUN=true)
- Vérifier que VaultMemory, ScoutResearch, LensReviewer tournent

### ETAPE 3 — Test routing automatique
Envoyer des messages libres et vérifier la détection :
```
"bonjour"              → CHAT (réponse directe)
"analyse le marché"    → RESEARCH (agents mobilisés)
"planifie le MVP"      → PLAN (MapPlanner prioritaire)
"écris un script"      → CODE (ForgeBuilder prioritaire)
"améliore-toi"         → IMPROVE (SelfImprove pipeline)
```

### ETAPE 4 — Test validation MEDIUM (passer DRY_RUN=false)
```bash
DRY_RUN=false
```
```
/auto Crée un fichier workspace/test_validation.md avec le contenu "Test JarvisMax"
```
- Attendu : action `create_file` → LOW → auto-exécuté
- Vérifier que le fichier existe dans `workspace/`
- Vérifier log dans `logs/executor.jsonl`

### ETAPE 5 — Test validation MEDIUM obligatoire
```
/auto Déplace workspace/test_validation.md vers workspace/reports/
```
- Attendu : action `move_file` → MEDIUM → carte Telegram avec boutons
- TTL visible : "(expire dans 15 min)"
- Tester APPROUVER → fichier déplacé
- Tester REFUSER → rien exécuté

### ETAPE 6 — Test /improve supervisé
```
/improve Analyse le code et propose 3 améliorations concrètes
```
- Attendu :
  - ETAPE 1/8 : Audit
  - ETAPE 2/8 : Fichiers chargés
  - ETAPE 3-5/8 : Génération et review
  - ETAPE 6/8 : Cartes de validation
- Tester APPLIQUER sur une amélioration LOW/MEDIUM
- Vérifier backup créé dans `workspace/.backups/`
- Vérifier rapport ETAPE 8 envoyé après application

---

## Vérifications de sécurité

### Test blacklist shell
Envoyer via API (non via Telegram) :
```python
from executor.runner import ActionExecutor, _BLACKLIST
dangerous = ["rm -rf /", "sudo dd if=/dev/zero", ":(){ :|:& };:"]
for cmd in dangerous:
    assert _BLACKLIST.search(cmd), f"MANQUE blacklist: {cmd}"
```

### Test fichiers protégés SelfImprove
```python
from self_improve.engine import Improvement
for f in [".env", "docker-compose.yml", "config/settings.py", "risk/engine.py"]:
    imp = Improvement("T", f, "p", "s", {}, "r", "high", "i")
    assert imp.is_forbidden(), f"ECHEC: {f} devrait être protégé"
```

### Test LOCAL_ONLY isolation
```python
from core.llm_factory import LLMFactory, LOCAL_ONLY_ROLES
f = LLMFactory(settings)
for role in LOCAL_ONLY_ROLES:
    chain = f._build_chain(role, "openai")
    assert chain == ["ollama"], f"{role} NE DOIT PAS avoir de fallback cloud"
```

---

## /status — Checklist minimale

```
[OK] Ollama                   → modèles disponibles
[OK] Redis                    → ping OK
[OK] Qdrant                   → collections accessibles
[OK] Jarvis API               → http://localhost:8000/health
Mode production               → DRY_RUN=false
Tâches actives : 0            → aucune session bloquée
Validations en attente : 0    → aucun TTL expiré
LLM director : openai         → provider actif
LLM advisor  : ollama         → toujours local
```

---

## Cas limites à tester

| Cas | Action | Comportement attendu |
|-----|--------|---------------------|
| Ollama down | Lancer /auto | Agents local-only échouent gracieusement, cloud continue |
| OpenAI key invalide | Lancer /auto | Fallback Ollama, log warning |
| Validation expirée (>15 min) | Cliquer APPROUVER | Message "Validation expirée" |
| 2 sessions en parallèle | /auto A + /auto B | Sessions isolées, outputs non mélangés |
| /cancel en pleine mission | /cancel | Task annulée, message confirmé |
| action HIGH sans backup | write_file /etc | Bloqué par RiskEngine + SYS_PATHS |
| self_improve sur .env | /improve modifie .env | Bloqué par FORBIDDEN_SELF_MODIFY |
| Night worker crash cycle 3 | Kill container | Cycles 1-2 persistés dans workspace/missions/ |
