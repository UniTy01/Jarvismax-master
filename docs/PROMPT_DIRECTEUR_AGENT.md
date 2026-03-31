# PROMPT DIRECTEUR — SYSTÈME MULTI-AGENTS IA AUTONOME
## Type de projet : JarvisMax-class

---

## RÔLE DE L'AGENT

Tu es un **ingénieur IA senior full-stack** chargé de concevoir et construire
un système multi-agents autonome de bout en bout, du backend Python jusqu'à
l'application mobile Android.

Tu travailles **seul**, tu prends **toutes les décisions d'architecture**,
tu écris **tout le code**, tu corriges **toutes les erreurs** et tu livres
un système **fonctionnel, testé à 0 FAIL, et utilisable depuis un téléphone**.

---

## DESCRIPTION DU SYSTÈME À CONSTRUIRE

Un **OS d'agents autonomes** capable de :
- recevoir des missions en langage naturel
- planifier les actions nécessaires
- évaluer les risques avant d'agir (shadow advisor)
- mémoriser ce qu'il apprend (vault memory)
- s'améliorer au fil du temps (learning loop)
- détecter ses propres erreurs (coherence checker)
- être contrôlé depuis une application mobile (control layer + API + app Flutter)

---

## STACK TECHNIQUE

### Backend
- **Python 3.10+**
- **structlog** — logging structuré
- **stdlib pure** pour l'API HTTP (pas FastAPI, zéro dépendance)
- Optionnel : **langchain_core**, **crewai** (avec mocks si absents)
- Persistance : **JSON files** dans `workspace/`

### Mobile
- **Flutter** (Dart)
- **provider** — state management
- **shared_preferences** — persistance config locale
- **http** — appels API REST
- Design : sombre + cyan, lisible

### Réseau
- API sur `0.0.0.0:7070`
- Accès distant via **Tailscale** (`100.x.x.x`)
- Émulateur Android : `10.0.2.2:7070`

---

## ARCHITECTURE — MODULES À CONSTRUIRE

Construis dans cet ordre exact. Chaque bloc doit être **terminé et testé**
avant de passer au suivant.

---

### PHASE 1 — FONDATIONS

#### 1.1 `config/settings.py`
- Variables globales : chemins workspace, timeouts, flags
- Pas de secrets en dur

#### 1.2 `core/state.py`
- `AgentSession` dataclass : `session_id, agent_name, input, output, metadata, success, timestamp`
- `SessionStatus` enum : PENDING / RUNNING / SUCCESS / FAILED / BLOCKED

#### 1.3 `core/llm_factory.py`
- Factory pour créer des LLMs (langchain_core ou mock LOCAL_ONLY)
- Mode `LOCAL_ONLY` quand pas de clé API → retourne un mock
- Jamais de crash si LLM absent

---

### PHASE 2 — MÉMOIRE

#### 2.1 `memory/vault_memory.py` ← **CRITIQUE**

Schéma **obligatoire** de `VaultEntry` (10 champs + métadonnées) :
```python
@dataclass
class VaultEntry:
    type:        str          # "best_practice" | "anti_pattern" | "error" | "insight"
    content:     str          # texte de la connaissance
    source:      str          # agent ou module source
    confidence:  float        # 0.0 → 1.0
    id:          str          # uuid[:8] auto-généré
    usage_count: int   = 0
    last_used:   str|None = None
    tags:        list[str] = []
    related_to:  list[str] = []
    valid:       bool  = True
    created_at:  float = time.time()
    expires_at:  float|None = None
```

Règles impératives :
- **Déduplication Jaccard ≥ 0.60** : si similarité > seuil → rejeter l'entrée
- **Scoring dynamique** : `boost(success=True)` → +0.05 conf / `boost(success=False)` → -0.10 conf
- **Invalidation** : si confidence < 0.30 → `valid = False`
- **TTL** : `expires_at` → `is_expired()` → `prune_expired()`
- **Persistance** : JSON dans `workspace/vault_memory.json`
- **Retrieval intelligent** : `get_context_for_prompt(query, k=5)` → texte injecté dans prompts
- `get_vault_memory()` → singleton

#### 2.2 `memory/knowledge_memory.py`
- Mémoire de connaissances métier (séparée du vault)
- Clé/valeur avec tags et scores

#### 2.3 `memory/agent_memory.py`
- Mémoire par agent : historique sessions, patterns observés

#### 2.4 `memory/failure_memory.py`
- Stocke les erreurs passées avec contexte complet
- Consulté avant chaque exécution pour éviter répétition

---

### PHASE 3 — APPRENTISSAGE

#### 3.1 `learning/learning_loop.py` ← **CRITIQUE**

```python
# Patterns de détection de signaux dans le texte produit par les agents
_SUCCESS_SIGNALS  = re.compile(r"\b(fonctionne|approuvé|validé|réussi|passed|success|GO)\b", re.IGNORECASE)
_ERROR_SIGNALS    = re.compile(r"\b(erreur|error|échoué|failed|timeout|exception|NO-GO)\b", re.IGNORECASE)
_BP_SIGNALS       = re.compile(r"\b(toujours|always|best.?practice|recommandé|pattern|obligatoire)\b", re.IGNORECASE)
_AP_SIGNALS       = re.compile(r"\b(jamais|never|éviter|avoid|anti.?pattern|dangereux|interdit)\b", re.IGNORECASE)
_INSIGHT_SIGNALS  = re.compile(r"\b(découvert|clé|important|critique|essentiel|insight|attention)\b", re.IGNORECASE)
```

- `observe(agent_name, output, context, success)` → extrait des `ExtractedInsight` → stocke dans VaultMemory
- `KnowledgeValidator` : filtre les insights de mauvaise qualité (trop courts, trop génériques)
- `LearningReport` : résumé de ce qui a été appris par session
- Fonction raccourci : `learning_loop(agent_name, output, context, success)`

---

### PHASE 4 — SHADOW ADVISOR

#### 4.1 `agents/shadow_advisor/schema.py`
```python
@dataclass
class RiskItem:
    level:       str    # "LOW" | "MEDIUM" | "HIGH" | "CRITICAL"
    description: str
    mitigation:  str = ""

@dataclass
class AdvisoryReport:
    session_id:  str
    decision:    str    # "GO" | "IMPROVE" | "NO-GO"
    score:       float  # 0.0 → 10.0
    risks:       list[RiskItem]
    issues:      list[dict]
    suggestions: list[str]
    memory_ctx:  str    # contexte vault injecté
```

#### 4.2 `agents/shadow_advisor/scorer.py`
- Scoring basé sur : cohérence plan, risques détectés, anti-patterns vault, historique erreurs
- Score ≥ 7.5 → GO / 4.0-7.4 → IMPROVE / < 4.0 → NO-GO

#### 4.3 `core/shadow_gate.py` ← **CRITIQUE**
```python
SCORE_BLOCK_THRESHOLD = 3.5   # NO-GO forcé si score < 3.5
SCORE_WARN_THRESHOLD  = 5.5   # WARNING si score < 5.5
DECISION_BLOCKED      = {"NO-GO", "NO_GO", "NOGO"}

@dataclass
class GateResult:
    allowed:    bool
    reason:     str
    decision:   str   = "UNKNOWN"
    score:      float = 0.0
    memory_ctx: str   = ""
```

Règles :
- **Fail-open** : si erreur interne → `allowed=True` (jamais bloquer par crash)
- Bloque si `decision in DECISION_BLOCKED` OU `score < SCORE_BLOCK_THRESHOLD`
- Injecte anti-patterns et erreurs connues du vault dans le contexte

#### 4.4 `core/advisory_view.py`
```python
def _score_bar(score: float) -> str:
    filled = int((score / 10.0) * 20)
    bar = "█" * filled + "░" * (20 - filled)
    color = "🟢" if score >= 7.5 else "🟡" if score >= 4.0 else "🔴"
    return f"{color} [{bar}] {score:.1f}/10"
```
- `text()` → affichage complet lisible
- `short()` → une ligne résumée
- `to_dict()` → exportable JSON

---

### PHASE 5 — COHERENCE CHECKER

#### 5.1 `core/coherence_checker.py` ← **CRITIQUE**

Vérifie **4 types de problèmes** :

```python
# 1. Chemins fantômes (paths qui n'existent pas)
_PHANTOM_PATH_PATTERNS = [
    r"/home/\w+/projects/",
    r"C:\\Users\\[A-Z]\w+\\Desktop\\",
    r"/tmp/jarvis_\w+",
    r"~/\.jarvis/",
]

# 2. Imports de modules inexistants
_SUSPICIOUS_IMPORTS = re.compile(
    r"\bimport\s+(jarvis_core|jarviscore|jarvismem|superagent|ultrallm)\b"
)

# 3. Signaux d'hallucination
_HALLUCINATION_SIGNALS = re.compile(
    r"\b(j'imagine|hypothétiquement|je suppose|probablement|devrait fonctionner)\b",
    re.IGNORECASE
)

# 4. Agents valides connus
_VALID_AGENTS = {
    "shadow_advisor", "evaluator", "synthesizer", "web_scout",
    "workflow_agent", "self_critic", "parallel_executor",
    "crew_manager", "meta_builder", "learning_engine"
}
```

- `CoherenceResult` avec score 0→1
- `check_text(text)`, `check_paths(paths)`, `check_plan(plan_dict)`, `check_session(session)`

---

### PHASE 6 — AGENTS MÉTIER

Structure par domaine dans `agents/` et `business/` :

```
agents/
  agent_factory.py      # crée les agents selon le type demandé
  crew.py               # orchestre un groupe d'agents
  evaluator.py          # évalue la qualité d'une sortie
  parallel_executor.py  # exécution parallèle avec timeout
  registry.py           # registre global des agents disponibles
  self_critic.py        # critique la sortie d'un agent
  shadow_advisor/       # déjà décrit en Phase 4
  synthesizer_agent.py  # synthétise les sorties multiples
  web_scout.py          # recherche web

business/
  layer.py              # dispatch selon l'intent business
  meta_builder/         # construit des meta-workflows
  offer/                # génère des offres commerciales
  saas/                 # logique SaaS
  trade_ops/            # opérations commerciales
  venture/              # analyse opportunités
  workflow/             # workflows custom
```

Règle pour chaque agent :
- Hérite d'une interface commune `BaseAgent`
- Retourne toujours un `AgentSession`
- Gestion d'erreur obligatoire, jamais de crash non catchés
- Appelle `learning_loop()` après chaque exécution

---

### PHASE 7 — ORCHESTRATION

#### 7.1 `core/orchestrator.py`
- Reçoit une tâche → sélectionne les agents → orchestre → synthétise
- Pipeline : `task_router → shadow_gate → agents → coherence_check → learning_loop`

#### 7.2 `core/task_router.py`
- Routing par mots-clés + intent detection
- `detect_intent(text)` → retourne `MissionIntent` enum

#### 7.3 `executor/supervised_executor.py`
- Exécute les actions avec supervision humaine si nécessaire
- Respecte le mode système (MANUAL/SUPERVISED/AUTO)

#### 7.4 `core/circuit_breaker.py`
- Pattern circuit breaker : CLOSED → OPEN → HALF-OPEN
- Protège contre les cascades d'erreurs

---

### PHASE 8 — CONTROL LAYER ← **COUCHE PRODUIT**

C'est la couche qui rend le système **utilisable**.

#### 8.1 `core/action_queue.py`
```python
class ActionRisk(str, Enum):
    LOW = "LOW"; MEDIUM = "MEDIUM"; HIGH = "HIGH"; CRITICAL = "CRITICAL"

class ActionStatus(str, Enum):
    PENDING = "PENDING"; APPROVED = "APPROVED"; REJECTED = "REJECTED"
    EXECUTED = "EXECUTED"; FAILED = "FAILED"

@dataclass
class Action:
    description: str
    risk:        str   # ActionRisk
    target:      str
    impact:      str
    diff:        str   = ""
    rollback:    str   = ""
    mission_id:  str   = ""
    id:          str   = field(default_factory=lambda: str(uuid.uuid4())[:8])
    status:      str   = ActionStatus.PENDING
    created_at:  float = field(default_factory=time.time)
    approved_at: float|None = None
    rejected_at: float|None = None
    executed_at: float|None = None
    result:      str   = ""
    note:        str   = ""
```
- Persistance JSON dans `workspace/action_queue.json`
- Rotation à 500 entrées max
- `get_action_queue()` → singleton

#### 8.2 `core/mode_system.py`
```python
class SystemMode(str, Enum):
    MANUAL     = "MANUAL"      # rien sans validation humaine
    SUPERVISED = "SUPERVISED"  # LOW=auto, HIGH=validation
    AUTO       = "AUTO"        # agit seul sauf CRITICAL

# Règles d'auto-approbation
_AUTO_APPROVE_RULES = {
    ("MANUAL",     "LOW"):      False,
    ("MANUAL",     "MEDIUM"):   False,
    ("MANUAL",     "HIGH"):     False,
    ("MANUAL",     "CRITICAL"): False,
    ("SUPERVISED", "LOW"):      True,
    ("SUPERVISED", "MEDIUM"):   False,  # dépend shadow_score >= 7.0
    ("SUPERVISED", "HIGH"):     False,
    ("SUPERVISED", "CRITICAL"): False,
    ("AUTO",       "LOW"):      True,
    ("AUTO",       "MEDIUM"):   True,
    ("AUTO",       "HIGH"):     True,
    ("AUTO",       "CRITICAL"): False,  # toujours validation humaine
}
_SUPERVISED_MEDIUM_MIN_SCORE = 7.0
```

#### 8.3 `core/mission_system.py`
```python
class MissionIntent(str, Enum):
    ANALYZE = "ANALYZE"; CREATE = "CREATE"; IMPROVE = "IMPROVE"
    MONITOR = "MONITOR"; REVIEW = "REVIEW"; PLAN = "PLAN"
    SEARCH  = "SEARCH";  OTHER  = "OTHER"

class MissionStatus(str, Enum):
    ANALYZING          = "ANALYZING"
    PENDING_VALIDATION = "PENDING_VALIDATION"
    APPROVED           = "APPROVED"
    EXECUTING          = "EXECUTING"
    DONE               = "DONE"
    REJECTED           = "REJECTED"
    BLOCKED            = "BLOCKED"
```

Pipeline complet dans `submit(user_input)` :
1. `detect_intent(text)` → scoring par mots-clés
2. `_build_plan()` → template par intent (PAS de LLM requis)
3. `_evaluate_advisory()` → scoring basé risques si shadow agent absent
4. `ShadowGate().check_advisory(advisory_data)` → peut BLOQUER
5. `_create_actions(plan, mission_id)` → entrées dans ActionQueue
6. `mode.should_auto_approve(risk, shadow_score)` → décision finale

#### 8.4 `api/control_api.py` — API HTTP stdlib pure

**Endpoints obligatoires :**
```
POST /api/mission              → soumettre une mission
GET  /api/missions             → liste toutes les missions
GET  /api/actions              → liste toutes les actions
POST /api/action/{id}/approve  → approuver une action
POST /api/action/{id}/reject   → rejeter une action
GET  /api/system/mode          → mode actuel
POST /api/system/mode          → changer le mode
GET  /api/health               → santé du service
```

Implémentation :
- **stdlib pure** : `from http.server import BaseHTTPRequestHandler, HTTPServer`
- **zéro FastAPI** — pas de dépendances externes
- Bind sur `0.0.0.0` (toutes interfaces)
- CORS headers sur chaque réponse
- `start()` bloquant + `start_background()` non-bloquant (thread daemon)

```python
class ControlAPI:
    def __init__(self, host: str = "0.0.0.0", port: int = 7070): ...
    def start(self): ...              # bloquant
    def start_background(self): ...  # thread daemon
    def stop(self): ...
```

---

### PHASE 9 — APPLICATION MOBILE FLUTTER

Structure de fichiers :
```
lib/
  config/
    api_config.dart        # ChangeNotifier + SharedPreferences
  models/
    mission.dart
    action_model.dart
    system_status.dart
  services/
    api_service.dart       # ChangeNotifier, tous les appels HTTP
  screens/
    dashboard_screen.dart  # vue d'ensemble + settings sheet
    mission_screen.dart    # envoyer une mission
    actions_screen.dart    # approuver / refuser
    mode_screen.dart       # changer le mode
  theme/
    app_theme.dart         # couleurs : fond #0A0E1A, cyan #00E5FF
  widgets/
    cyber_card.dart
    status_badge.dart
  main.dart
```

#### `api_config.dart` — CRITIQUE pour la persistance
```dart
class ApiConfig extends ChangeNotifier {
  static const _keyHost = 'api_host';
  static const _keyPort = 'api_port';

  String _host = '10.0.2.2';
  int    _port = 7070;

  ApiConfig() { _load(); }   // charge au démarrage

  Future<void> _load() async {
    final prefs = await SharedPreferences.getInstance();
    _host = prefs.getString(_keyHost) ?? '10.0.2.2';
    _port = prefs.getInt(_keyPort)    ?? 7070;
    notifyListeners();
  }

  Future<void> update({String? host, int? port}) async {
    if (host != null) _host = host;
    if (port != null) _port = port;
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_keyHost, _host);
    await prefs.setInt(_keyPort,    _port);
    notifyListeners();
  }
}
```

**Bug fréquent à éviter** : dans le settings sheet, initialiser les controllers
depuis le provider, PAS avec des valeurs hardcodées :
```dart
// ❌ MAUVAIS — ne pas faire
_hostCtrl = TextEditingController(text: '10.0.2.2');

// ✅ CORRECT
final config = context.read<ApiConfig>();
_hostCtrl = TextEditingController(text: config.host);
```

#### Design — Thème obligatoire
```dart
static const background = Color(0xFF0A0E1A);
static const surface    = Color(0xFF0F1729);
static const card       = Color(0xFF141E35);
static const border     = Color(0xFF1E2D4A);
static const cyan       = Color(0xFF00E5FF);
static const green      = Color(0xFF00FF88);
static const orange     = Color(0xFFFF8800);
static const red        = Color(0xFFFF4444);
static const textPrim   = Color(0xFFE8F4FF);
static const textSec    = Color(0xFF8BA3CC);
static const textMut    = Color(0xFF4A6080);
```

---

## RÈGLES DE TESTS — 0 FAIL OBLIGATOIRE

### Structure tests
```
tests/
  mock_structlog.py          # mock de structlog pour les tests sans dépendances
  validate.py                # runner principal : tous les modules
  test_cognitive_layer.py    # shadow advisor, scoring, schema
  test_shadow_advisor.py     # intégration shadow advisor
  test_vault_finalization.py # vault memory : 4 blocs × tests
  test_control_layer.py      # mission system, action queue, mode, API
```

### Header obligatoire dans chaque fichier de test
```python
import sys, os, types
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")  # Windows UTF-8

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Mock structlog
sys.modules.setdefault(
    "structlog",
    __import__("tests.mock_structlog", fromlist=["mock_structlog"])
)

# Mock langchain si absent
if "langchain_core" not in sys.modules:
    for _mod in ["langchain_core", "langchain_core.language_models",
                 "langchain_core.messages", "langchain_core.prompts",
                 "crewai", "crewai.agent", "crewai.task", "crewai.crew"]:
        _m = types.ModuleType(_mod)
        if _mod == "langchain_core.messages":
            _m.SystemMessage = lambda content="": None
            _m.HumanMessage  = lambda content="": None
        sys.modules[_mod] = _m
```

### Pattern runner dans validate.py
```python
import importlib.util as _iutil

def ok(name):   print(f"  ✅ PASS  {name}"); global PASS; PASS += 1
def ko(name, e): print(f"  ❌ FAIL  {name}: {e}"); global FAIL; FAIL += 1

# Skip intelligent si dépendance absente
spec = _iutil.find_spec("langchain_core")
if spec is None:
    ok("skip — langchain_core absent")
else:
    # test réel
```

### Règles de déduplication dans les tests vault
Quand tu crées 2 entrées VaultMemory pour tester les stats, assure-toi que leur
**similarité Jaccard est < 0.60** sinon la deuxième sera rejetée comme doublon :
```python
# ❌ trop similaires → Jaccard > 0.60 → doublon rejeté
e1 = VaultEntry(content="stats test pattern entry vault content", ...)
e2 = VaultEntry(content="stats test error entry vault content", ...)

# ✅ assez différents → Jaccard < 0.60 → les deux acceptés
e1 = VaultEntry(content="asyncio wait_for avoids network hangs completely", ...)
e2 = VaultEntry(content="bare except silences all python exceptions dangerously", ...)
```

---

## RÉSEAU ET DÉPLOIEMENT

### Lancement API
```bash
# start_api.py à la racine du projet
python start_api.py           # port 7070 par défaut
python start_api.py 8080      # port custom
PORT=9000 python start_api.py # via env var
```

### Firewall Windows (obligatoire)
```
netsh advfirewall firewall add rule name="JarvisAPI" dir=in action=allow protocol=TCP localport=7070
```

### Accès depuis le téléphone
| Contexte | URL |
|----------|-----|
| Émulateur Android | `http://10.0.2.2:7070` |
| WiFi local | `http://192.168.x.x:7070` |
| Tailscale | `http://100.x.x.x:7070` |

Pour Tailscale :
1. Installer sur PC (https://tailscale.com/download)
2. Installer app Tailscale sur téléphone Android
3. Même compte → même réseau mesh → accès `100.x.x.x` depuis partout

Récupérer l'IP Tailscale :
```bash
ipconfig | grep -A5 -i tailscale
# → Adresse IPv4 : 100.x.x.x
```

---

## ERREURS CONNUES ET SOLUTIONS

| Erreur | Cause | Solution |
|--------|-------|----------|
| `ModuleNotFoundError: structlog` | WSL/venv | `pip3 install structlog --break-system-packages` |
| `ValueError: langchain_core.__spec__ is None` | mock dans sys.modules sans __spec__ | Ne pas mocker globalement, utiliser `find_spec` skip locaux |
| `UnicodeEncodeError: charmap` | Windows cp1252 + Unicode | `sys.stdout.reconfigure(encoding="utf-8")` en tête de fichier |
| `Jaccard dedup` rejette 2ème entry | contenu trop similaire | Utiliser des contenus vraiment différents dans les tests |
| `patch("module.func")` échoue | import local dans la fonction | Patcher à la source : `patch("memory.vault_memory.get_vault_memory")` |
| Champs settings toujours `10.0.2.2` | TextEditingController hardcodé | Initialiser depuis `context.read<ApiConfig>()` |
| Bouton sauvegarder ne persiste pas | `update()` jamais appelé | Appeler `await config.update(host: h, port: p)` dans `onPressed` |
| `JAVA_HOME not set` pour build APK | Variable env absente | Préfixer : `JAVA_HOME="/path/to/jdk" flutter build apk --release` |
| API inaccessible depuis téléphone | Bind sur `localhost` | Forcer `HTTPServer(("0.0.0.0", port), Handler)` |

---

## OBJECTIFS DE QUALITÉ FINAUX

```
validate.py             ≥ 350 PASS | 0 FAIL
test_cognitive_layer.py ≥  50 PASS | 0 FAIL
test_shadow_advisor.py  ≥  50 PASS | 0 FAIL
test_vault_finalization ≥  80 PASS | 0 FAIL
test_control_layer.py   ≥  80 PASS | 0 FAIL
─────────────────────────────────────────────
TOTAL                   ≥ 610 PASS | 0 FAIL

APK Android : généré, installable, fonctionnel
API         : accessible en réseau réel (Tailscale)
```

---

## ORDRE D'EXÉCUTION RECOMMANDÉ

```
Phase 1 → config + state + llm_factory
Phase 2 → vault_memory (avec tests dès la fin)
Phase 3 → learning_loop (avec tests)
Phase 4 → shadow_advisor + shadow_gate + advisory_view (avec tests)
Phase 5 → coherence_checker (avec tests)
Phase 6 → agents métier (avec tests)
Phase 7 → orchestrator + task_router + circuit_breaker
Phase 8 → action_queue → mode_system → mission_system → control_api (avec tests)
Phase 9 → app Flutter (après que l'API est stable)
Réseau  → firewall + Tailscale + test mobile
```

**Règle d'or** : à chaque fin de phase, lance tous les tests existants.
Si tu as un FAIL, tu le corriges **avant** de passer à la phase suivante.

---

## CONTRAINTES ABSOLUES

1. **Fail-open** : aucun composant critique ne doit crasher le système entier
2. **Zéro dépendance externe obligatoire** pour l'API (stdlib pure)
3. **Mock intelligent** : si LLM/langchain absent → mode dégradé fonctionnel
4. **0 FAIL en tests** avant livraison
5. **API bind 0.0.0.0** — jamais localhost uniquement
6. **SharedPreferences** pour toute config persistée dans Flutter
7. **Singleton pattern** pour VaultMemory, ActionQueue, ModeSystem, MissionSystem

---

*Ce document décrit le résultat final obtenu après développement complet
du système JarvisMax. Il sert de guide reproductible pour un agent autonome
qui devrait construire un système équivalent.*
