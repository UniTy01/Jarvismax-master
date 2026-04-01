# KERNEL_AUDIT.md — Audit Architectural Complet JarvisMax
> Auteur : Lead Architect + Principal Refactoring Engineer
> Date baseline : 2026-03-30 | Dernière mise à jour : 2026-03-31 (post-Pass 33 — observabilité + CI)
> Méthode : lecture directe du repo + tests automatisés

---

## ✅ CONVERGENCE COMPLÈTE + OBSERVABILITÉ + CI (Passes 8–33)

**État : JARVISMAX EST UN AI OS** — le kernel est le vrai cerveau cognitif.
Toutes les règles architecturales R1–R10 sont implémentées, testées et câblées end-to-end.

### Tableau de conformité R1–R10

| Règle | Libellé | Implémentation | Statut |
|-------|---------|----------------|--------|
| R1 | kernel never imports core/api/agents/tools | K1 scan automatisé Pass 22 — 0 violation | ✅ |
| R2 | missions via kernel.run() | kernel.execute(ExecutionRequest) Pass 14 | ✅ |
| R3 | sensitive actions via kernel.policy() | SecurityLayer + kernel.policy.evaluate() | ✅ |
| R4 | self-improvement via kernel.improvement.gate | ImprovementGate.check() + security check Pass 23 | ✅ |
| R5 | structured learning via kernel.learn() | JarvisKernel.learn() + KernelLearner Pass 23/24 | ✅ |
| R6 | memory via MemoryFacade unifiée | register_facade_store/search() Pass 19 | ✅ |
| R7 | agents sous contrat kernel, kernel autorité | KernelAgentContract Protocol + KernelStatusAgent boot-registered Pass 27 | ✅ |
| R8 | API = adaptateur pur, jamais décideur | api/routes/missions.py → KernelAdapter (Pass 26) | ✅ |
| R9 | business never bypasses policy | BusinessLayer._security_gate() Pass 17b | ✅ |
| R10 | security not decorative | AuditTrail + SecurityLayer + boot init Pass 17/21 | ✅ |

### Métriques actualisées (post-Pass 33)

```
kernel/ — fichiers              : 50 fichiers / ~7 507 lignes
security/ — fichiers            : 7 fichiers (nouveau)
interfaces/ — fichiers          : 2 fichiers (nouveau)
business/strategy/ + finance/   : 4 fichiers (nouveau)
agents/kernel_bridge.py         : 1 fichier (nouveau — Pass 27)
api/routes/security_audit.py    : 1 fichier (nouveau — Pass 31)
.github/workflows/kernel_ci.yml : 1 fichier (nouveau — Pass 32)
tests/integration Pass 22       : 31 tests / 240ms — 31/31 ✅
K1 violations                   : 0 (toutes couches auditées, CI automatisé)
Sous-systèmes kernel ✅          : 11/11 (+learner via kernel.learn())
Boot time kernel                : ~80ms (security init incluse)
ImprovementGate + security      : self_improvement → ESCALATE systématique
KernelAgentRegistry             : 1 agent enregistré au boot (kernel-status-agent)
API → KernelAdapter             : missions.py utilise adapter.submit() (R8 end-to-end)
Docker                          : COPY . . inclut tous nouveaux layers — 0 dep nouvelle
API observabilité kernel         : 5 routes /agents* + /adapter/status (Pass 30)
API observabilité security       : 5 routes /security/* (Pass 31)
CI GitHub Actions                : kernel_ci.yml — 7 steps, K1 + integration + routes
```

### Passes 16–33 — résumé rapide

| Pass | Fichier principal | Règle | |
|------|-----------------|-------|--|
| 16 | `kernel/contracts/agent.py` | R7 agents sous contrat | ✅ |
| 17 | `security/` (policies/risk/audit) | R3, R10 governance | ✅ |
| 17b | `business/strategy/` `finance/` `layer.py` | R9 business gate | ✅ |
| 18 | `core/meta_orchestrator.py` → `_run_kernel_cognitive_cycle()` | lisibilité | ✅ |
| 19 | `kernel/memory/interfaces.py` → facade slots | R6 MemoryFacade | ✅ |
| 20 | `interfaces/kernel_adapter.py` | R8 API adaptateur (déclaration) | ✅ |
| 21 | `kernel/runtime/boot.py` → security au boot | R3, R10 native | ✅ |
| 22 | `tests/test_integration_kernel_security_business.py` | 31 tests | ✅ |
| 23 | `kernel/runtime/kernel.py` → `learn()` + `gate.py` + security | R4, R5 | ✅ |
| 24 | Audit pipeline learning complet (3 scénarios) | R5 validation | ✅ |
| 25 | `KERNEL_AUDIT.md` mise à jour convergence finale | documentation | ✅ |
| 26 | `api/routes/missions.py` → `KernelAdapter.submit()` | R8 end-to-end | ✅ |
| 27 | `agents/kernel_bridge.py` → `KernelStatusAgent` boot-registered | R7 end-to-end | ✅ |
| 28 | Docker validation — 0 nouvelle dépendance, COPY . . suffit | déploiement | ✅ |
| 29 | `RUNTIME_TRUTH.md` + `KERNEL_AUDIT.md` mise à jour | documentation | ✅ |
| 30 | `api/routes/kernel.py` → `/agents*` + `/adapter/status` | R7/R8 observabilité | ✅ |
| 31 | `api/routes/security_audit.py` → `/security/*` (5 routes) | R3/R10 observabilité | ✅ |
| 32 | `.github/workflows/kernel_ci.yml` — CI K1 + integration + routes | automatisation | ✅ |
| 33 | `KERNEL_AUDIT.md` + `RUNTIME_TRUTH.md` mise à jour | documentation | ✅ |

---

## ⚡ MISE À JOUR POST-CONVERGENCE (Passes 8–14)

**L'executive summary initial (ci-dessous) décrit l'état AVANT la convergence kernel.**
Depuis, 7 passes de refactoring ont radicalement changé l'architecture :

| Pass | Résultat |
|------|---------|
| Pass 8  | kernel.evaluator autorité (KernelScore) |
| Pass 9  | kernel.planner autorité (registration pattern) |
| Pass 10 | kernel.learner autorité (KernelLesson) |
| Pass 11 | kernel.run_cognitive_cycle() — brain first, MetaOrchestrator coordinateur |
| Pass 12 | kernel.state K1-compliant (MissionStatus kernel-canonical) |
| Pass 13 | kernel.memory.retrieve_lessons() — boucle cognitive fermée |
| Pass 14 | kernel.execute() — API → kernel, ExecutionRequest/ExecutionResult |

**Réponse actuelle à la question centrale :**
> JarvisMax converge-t-il vers **A** (AI OS avec kernel cognitif) ou **B** (framework multi-agents) ?

**Réponse : CONVERGENCE AVANCÉE VERS A — kernel est maintenant le vrai cerveau cognitif.**

Métriques post-convergence (mises à jour Pass 25) :
```
kernel/ — fichiers              : 50 fichiers / ~7 507 lignes  (était 20/~1700)
security/ — nouveau             : 7 fichiers (governance native)
interfaces/ — nouveau           : 2 fichiers (adapter layer)
core/   — fichiers              : 366 fichiers / ~109k lignes
Ratio core/kernel               : 14:1 (était 30:1)
Sous-systèmes kernel ✅          : 11/11 (classifier, planner, router, gate,
                                          evaluator, learner, cognitive, state,
                                          memory, execute, security)
K1 violations restantes         : 0 dans kernel/ + security/
Pipeline cognitif kernel-driven : classify→plan→route→retrieve→execute→evaluate→learn
API entry point                 : kernel.execute(ExecutionRequest) → ExecutionResult
ImprovementGate                 : self_improvement → ESCALATE via security layer (R4)
kernel.learn()                  : autorité R5, via JarvisKernel.learn()
Tests intégration               : 31/31 Pass 22 (229ms) — K1+boot+security+memory+biz+agent+interfaces
```

---

## EXECUTIVE SUMMARY (baseline — état avant convergence)

JarvisMax était un **framework multi-agents complexe avec une couche decorative nommée "kernel"**, non un AI OS avec un noyau cognitif central.

Le répertoire `kernel/` était bien structuré mais architecturalement **inversé** : il fournissait des services d'infrastructure mais **ne contrôlait rien**. La cognition réelle, les décisions, l'état, le planning — tout se passait dans `core/`, qui est un namespace plat de **124 modules** sans discipline de couche.

*(Ce diagnostic reste valable pour les parties de core/ non encore migrées.)*

---

## PARTIE 1 — AUDIT DU REPO ACTUEL

### 1.1 Chiffres clés

```
Fichiers Python totaux          : 902+
Lignes de code totales          : ~268 000+
core/ — fichiers                : 366 fichiers / ~109 000 lignes
kernel/ — fichiers              : 49 fichiers / ~7 046 lignes  [POST-CONVERGENCE]
agents/ — fichiers              : ~40 fichiers
api/ — routes                   : ~50 fichiers
Ratio core/kernel               : 30:1 (le "core" est 30x plus gros que le "kernel")
```

Le kernel est **30x plus petit** que core. Ce n'est pas un noyau — c'est un satellite.

---

### 1.2 Où se trouve le vrai kernel aujourd'hui ?

Le vrai cerveau du système est réparti sur **5 composants** dans `core/` :

| Composant | Fichier | Lignes | Rôle réel |
|-----------|---------|--------|-----------|
| **MetaOrchestrator** | `core/meta_orchestrator.py` | 1 363 | Machine à états + orchestration des phases |
| **JarvisOrchestrator** | `core/orchestrator.py` | 1 120 | Moteur d'exécution effectif |
| **OrchestratorV2** | `core/orchestrator_v2.py` | 727 | Execution budget/DAG |
| **TaskRouter** | `core/task_router.py` | ~200 | Classification d'intention |
| **MissionPlanner** | `core/mission_planner.py` | ~200 | Décomposition de missions |

Ces 5 modules font **le travail de kernel** mais ne s'appellent pas kernel et ne sont pas traités comme un kernel.

---

### 1.3 Ce que le kernel/ fait vraiment

Le répertoire `kernel/` contient :

```
kernel/contracts/types.py         Contrats de données (Mission, Goal, Plan, Action...)
kernel/policy/engine.py           RiskEngine + KernelPolicyEngine + ApprovalGate
kernel/capabilities/registry.py   Registre des capacités disponibles
kernel/capabilities/performance.py Suivi des performances providers
kernel/memory/interfaces.py       Working memory (write/read par mission)
kernel/events/canonical.py        Émetteur d'événements système
kernel/runtime/boot.py            Boot des subsystèmes ci-dessus
kernel/convergence/               5 bridges vers core/ (optionnels, fail-open)
kernel/adapters/                  6 adaptateurs de traduction kernel↔core
```

**Ce que le kernel/ NE contient PAS :**
- Aucun planificateur
- Aucun raisonneur
- Aucun décomposeur de goal
- Aucun gestionnaire d'état de mission
- Aucune logique de routing cognitif
- Aucun contrôle d'agent
- Aucune boucle de feedback

Le kernel sait **initialiser ses services** mais ne sait pas **piloter une mission**.

---

### 1.4 Problème de dépendances circulaires

Audit des imports croisés :

```
kernel/ importe depuis core/     : 20 fois
core/ importe depuis kernel/     : 25 fois
```

**Il y a une dépendance circulaire.** Ni `core/` ni `kernel/` n'est structurellement au-dessus de l'autre. Un vrai kernel ne doit JAMAIS importer depuis les couches qu'il gouverne.

Exemples concrets de la circulaire :
```python
# kernel/ dépend de core/ :
kernel/adapters/capability_adapter.py  → from core.capability_routing.registry import ProviderRegistry
kernel/adapters/policy_adapter.py      → from core.policy_engine import PolicyEngine
kernel/capabilities/identity.py        → from core.tool_executor import ToolExecutor

# core/ dépend de kernel/ :
core/meta_orchestrator.py              → from kernel.convergence.policy_bridge import check_action_kernel
core/capability_routing/router.py      → from kernel.convergence.performance_routing import enrich_providers
```

C'est architecturalement incompatible avec un vrai OS kernel. Un kernel pilote — il n'est pas piloté.

---

### 1.5 Inventaire des redondances majeures

#### Redondance 1 — 3 orchestrateurs parallèles
```
core/meta_orchestrator.py    1363 lignes  ← façade + état
core/orchestrator.py         1120 lignes  ← moteur effectif (délégué interne)
core/orchestrator_v2.py       727 lignes  ← budget/DAG (délégué interne)
```
L'architecture est MetaOrchestrator → JarvisOrchestrator → agents. Mais JarvisOrchestrator a lui-même 20+ propriétés lazy-loaded (agents, risk, executor, memory, escalation, learning, metrics, llm, policy, goal_manager, system_state, replay, agent_memory...). C'est un deuxième orchestrateur complet imbriqué.

#### Redondance 2 — 4 systèmes d'auto-amélioration
```
core/self_improvement.py         SHADOWED (inaccessible)
core/self_improvement_engine.py  V2, superseded
core/self_improvement_loop.py    V3 partiel
core/self_improvement/           V3 canonique
```
Résolus en partie. Reste : loop.py à supprimer.

#### Redondance 3 — 2 registres de tools
```
tools/tool_registry.py       Executor registry (instances live)
core/tool_registry.py        Definition registry (metadata/ranking)
```
Deux registres différents, pas clairement documentés pour les nouveaux dev.

#### Redondance 4 — 20+ modules de planning dispersés
```
core/mission_planner.py
core/planner.py
core/planning/__init__.py
core/planning/execution_memory.py
core/planning/execution_plan.py
core/planning/input_resolver.py
core/planning/learning_memory.py
core/planning/mission_trace.py
core/planning/output_enforcer.py
core/planning/plan_runner.py
core/planning/plan_serializer.py
core/planning/plan_validator.py
core/planning/playbook.py
core/planning/run_state.py
core/planning/self_review.py
core/planning/skill_llm.py
core/planning/step_context.py
core/planning/step_executor.py
core/planning/step_retry.py
core/planning/workflow_templates.py
core/goal_decomposer.py
core/goal_manager.py
```
Aucun de ces modules ne vit dans `kernel/`. Le planning est une responsabilité kernel — elle est dans core/.

#### Redondance 5 — Mémoire fragmentée en couches non unifiées
```
memory/store.py              ← MemoryStore (base)
memory/vector_memory.py      ← VectorMemory
memory/memory_bus.py         ← MemoryBus
memory/agent_memory.py       ← AgentMemory
core/mission_memory.py       ← MissionMemory
core/improvement_memory.py   ← ImprovementMemory
core/memory_facade.py        ← MemoryFacade (unificateur, partiellement utilisé)
kernel/memory/interfaces.py  ← KernelWorkingMemory
core/self_improvement/lesson_memory.py ← LessonMemory (fraîchement extrait)
```
9 systèmes de mémoire. La MemoryFacade existe mais n'est utilisée que par MetaOrchestrator Phase 5.

#### Redondance 6 — Cognitif dispersé hors kernel
```
core/meta_cognition.py        Réflexion sur les capacités propres
core/cognitive_bridge.py      Pont cognitif (473 lignes)
core/reasoning_framework.py   Framework de raisonnement
core/orchestration_intelligence.py  Intelligence d'orchestration (681 lignes)
core/multi_mission_intelligence.py  Gestion multi-missions (988 lignes)
```
Tout ce qui devrait être au cœur du kernel vit dans core/ à plat.

---

### 1.6 Ce qui prétend être central mais ne l'est pas

| Module | Ce qu'il prétend | Réalité |
|--------|-----------------|---------|
| `kernel/runtime/boot.py` | "Le kernel démarre" | Boot de services, pas de contrôle |
| `kernel/convergence/*` | "Convergence kernel↔core" | Bridges optionnels fail-open, jamais authoritative |
| `core/aios_manifest.py` | "AI OS manifest central" | Agrégateur en lecture, pas de contrôle |
| `core/meta_orchestrator.py` | "Façade + état" | C'est le vrai kernel — mal nommé |
| `core/architecture_ownership.py` | "Gestion de l'architecture" | Module d'audit, pas de contrôle runtime |

---

## PARTIE 2 — VERDICT ARCHITECTURAL

### Q1: JarvisMax possède-t-il déjà un kernel ?

**Oui — mais il ne s'appelle pas kernel et ne se trouve pas dans kernel/.**

Le vrai kernel actuel est `core/meta_orchestrator.py` + `core/orchestrator.py`. Ce binôme est le seul endroit où l'état global des missions est maintenu et où les décisions d'exécution sont prises.

### Q2: Ce kernel est-il bon ?

**Non.** Trois problèmes majeurs :

1. **Il est trop gros** : 1363 + 1120 lignes = 2483 lignes pour 2 fichiers qui devraient ensemble faire ≤ 600 lignes si les responsabilités étaient bien séparées.

2. **Il fait trop de choses** : MetaOrchestrator contient en même temps la machine à états, le circuit breaker, la gestion des sessions, l'orchestration des phases 0a→5, les intégrations kernel, la résolution d'approbations, la récupération depuis la persistance. Ce sont 6+ responsabilités distinctes.

3. **Il délègue aveuglément** : JarvisOrchestrator charge 20+ services à la demande via des propriétés lazy. Il n'y a pas de contrat clair sur ce que chaque sous-service doit faire ou peut faire. C'est un service locator, pas un kernel.

### Q3: MetaOrchestrator est-il un vrai kernel ou un super-coordinateur ?

**Un super-coordinateur.** La différence est nette :

| Critère | Vrai kernel | MetaOrchestrator actuel |
|---------|-------------|------------------------|
| Contrôle le flux de décision | Oui | Partiellement |
| Maintient la cohérence globale | Oui | Via état de session |
| Définit les contrats vers agents | Oui | Non — agents importés directement |
| Arbitre les capacités | Non | Partiel (Phase 0c) |
| Gère la politique de sécurité | Non | Optionnel (Phase 3-kernel fail-open) |
| Contrôle la mémoire | Non | Optionnel (Phase 3-kmem fail-open) |
| Supervise l'auto-amélioration | Non | Non |
| Maintient la cohérence inter-missions | Non | Non (chaque mission isolée) |

Le kernel vrai doit contrôler TOUS ces aspects. MetaOrchestrator en contrôle ~2/8.

### Q4: Quelle est la frontière exacte du kernel actuel ?

```
DANS LE KERNEL (de facto) :
  core/meta_orchestrator.py    — état de mission
  core/orchestrator.py         — exécution
  core/task_router.py          — classification

DEVRAIT ÊTRE DANS LE KERNEL (mais dans core/ à plat) :
  core/mission_planner.py      — planning
  core/goal_manager.py         — goals
  core/reasoning_framework.py  — raisonnement
  core/evaluation_engine.py    — évaluation
  kernel/policy/engine.py      — politique (est dans kernel/ mais jamais authoritative)

DÉCORATIF / ORPHELIN :
  kernel/runtime/boot.py       — boot sans contrôle
  kernel/convergence/*         — bridges fail-open jamais critiques
  core/aios_manifest.py        — audit passif
  core/architecture_ownership.py — documentation runtime
```

---

## PARTIE 3 — ARCHITECTURE CIBLE

### 3.1 Périmètre exact du kernel cible

Le kernel doit être un seul répertoire cohérent (`kernel/`) avec exactement **6 responsabilités** :

```
kernel/
├── state/           ← Mission state machine (CREATED→DONE)
│     mission_state.py, session.py, transitions.py
├── planning/        ← Goal decomposition + plan generation
│     goal.py, planner.py, decomposer.py
├── policy/          ← Risk + policy + approval (DÉJÀ LÀ, bon)
│     engine.py (existant, garder)
├── memory/          ← Working memory + episodic index (DÉJÀ LÀ, étendre)
│     interfaces.py (existant), episodic.py (nouveau)
├── capabilities/    ← Capability arbitration (DÉJÀ LÀ, étendre)
│     registry.py (existant), arbiter.py (nouveau)
├── events/          ← Système d'événements (DÉJÀ LÀ, bon)
│     canonical.py (existant)
└── runtime/         ← Boot + handle (DÉJÀ LÀ, étendre)
      boot.py (existant), kernel.py (nouveau — point d'entrée unique)
```

**Ce que le kernel cible NE doit PAS contenir :**
- Logique d'agents spécifiques
- Implémentation concrète des tools
- Parsing d'intentions utilisateur
- Logique de business domain
- Routes API
- Gestion de sessions HTTP
- Code d'auto-amélioration (hors gating)

### 3.2 Interfaces kernel → agents

Le kernel doit exposer exactement **4 interfaces** vers les couches inférieures :

```python
# Interface 1 — Exécution d'une mission
kernel.execute(mission: Mission) -> ExecutionResult

# Interface 2 — Enregistrement d'une capacité
kernel.capabilities.register(cap: Capability) -> None

# Interface 3 — Requête de politique
kernel.policy.check(action: Action) -> PolicyDecision

# Interface 4 — Mémoire de contexte
kernel.memory.get_context(mission_id: str) -> MissionContext
```

Tout le reste (agents, tools, business logic, API) parle AU kernel via ces 4 interfaces. Le kernel ne parle pas aux couches inférieures directement — il délègue via des contrats formels.

### 3.3 Ce que le kernel ne doit pas faire

```
✗ Instancier des agents directement
✗ Appeler des tools spécifiques
✗ Lire/écrire sur le filesystem
✗ Connaître les providers LLM
✗ Gérer l'authentification HTTP
✗ Implémenter le business domain
✗ Contenir de la logique de retry spécifique à un agent
```

### 3.4 Comment garder le kernel petit mais puissant

Règle des **500 lignes par module** : aucun fichier dans kernel/ ne dépasse 500 lignes.
Règle des **10 modules** : kernel/ ne doit jamais avoir plus de 10 modules de premier niveau.
Règle des **0 import circulaire** : kernel/ n'importe JAMAIS depuis core/, agents/, api/, tools/.

---

## PARTIE 4 — ROADMAP DE REFACTOR (7 phases)

### Phase 1 — Vérité architecturale (FAIT en partie)
**Durée estimée : complétée à 60%**

| Tâche | Statut |
|-------|--------|
| Documenter le kernel réel dans RUNTIME_TRUTH.md | ✅ Fait (Pass 1+2) |
| Corriger les labels DEPRECATED erronés | ✅ Fait (Pass 2) |
| Extraire LessonMemory vers core/self_improvement/ | ✅ Fait (session actuelle) |
| Remonter les routes API orphelines | ✅ Fait (Pass 2) |
| Produire ce KERNEL_AUDIT.md | ✅ Fait |
| Identifier toutes les dépendances circulaires kernel↔core | ⬜ Reste à faire |

---

### Phase 2 — Suppression des redondances
**Durée estimée : 2-3 jours de travail**

Priorité décroissante :

**2.1 — Supprimer self_improvement_loop.py**
```
Prérequis : LessonMemory extrait ✅ (fait)
Action     : vérifier que SelfImprovementLoop dans le fichier n'est plus appelé
             supprimer le fichier
Risque     : faible (compat shim en place)
```

**2.2 — Absorber JarvisOrchestrator dans MetaOrchestrator**
```
Problème   : 1120 lignes de délégué avec 20+ lazy-loads = couplage opaque
Action     : déplacer _run_auto, _run_chat, _run_night, etc. directement
             dans MetaOrchestrator (ou dans des delegates formels avec contrat)
Gain       : supprimer une couche d'indirection, voir exactement ce qui s'exécute
Risque     : moyen — la délégation est implicite partout
```

**2.3 — Consolider les registres de tools**
```
Problème   : 2 registres distincts (executor vs definition)
Action     : créer tools/registry.py comme façade unique
             tools/tool_registry.py → executor (garder)
             core/tool_registry.py → definition (garder, renommer clairement)
Risque     : faible
```

**2.4 — Consolider la mémoire**
```
Problème   : 9 systèmes de mémoire dispersés
Action     : core/memory_facade.py devient obligatoire, pas optionnel
             agents/ et kernel/ utilisent tous MemoryFacade
             supprimer les imports directs de memory/store.py, memory/vector_memory.py
Risque     : moyen — beaucoup de callers à mettre à jour
```

---

### Phase 3 — Extraction / Recentrage du kernel
**Durée estimée : 3-5 jours de travail — c'est la phase critique**

**3.1 — Créer kernel/state/ (Mission State Machine)**
```
Déplacer : core/meta_orchestrator.py — la machine à états seulement
           (MissionStatus, _VALID_TRANSITIONS, _transition(), MissionContext)
Destination : kernel/state/mission_state.py
Résultat : MetaOrchestrator devient plus petit et délègue la machine à états au kernel
```

**3.2 — Créer kernel/planning/ (Goal → Plan)**
```
Déplacer : core/mission_planner.py → kernel/planning/planner.py
           core/goal_decomposer.py → kernel/planning/decomposer.py
           core/goal_manager.py    → kernel/planning/goal.py
Résultat : le planning vit dans le kernel — le cerveau planifie, pas un service core
```

**3.3 — Élever le kernel/policy/ comme autorité (non fail-open)**
```
Problème actuel : check_action_kernel() est appelé fail-open dans MetaOrchestrator Phase 3-kernel
                  si le kernel est down, la mission continue sans vérification de politique
Action          : rendre kernel/policy/engine.py synchrone, rapide, never-fail
                  supprimer le try/except dans MetaOrchestrator Phase 3-kernel
                  la politique kernel est maintenant obligatoire, pas optionnelle
Risque          : moyen — nécessite que le kernel soit stable avant cette étape
```

**3.4 — Supprimer les dépendances circulaires**
```
Règle : kernel/ n'importe JAMAIS depuis core/, agents/, api/
Action : kernel/adapters/capability_adapter.py → ne doit plus importer from core.capability_routing
         kernel/adapters/policy_adapter.py     → ne doit plus importer from core.policy_engine
         kernel/capabilities/identity.py       → ne doit plus importer from core.tool_executor
Solution : inversion de dépendance — core/ enregistre ses services dans kernel/ au boot
           (pattern registration, pas import direct)
```

---

### Phase 4 — Stabilisation des interfaces
**Durée estimée : 2-3 jours**

**4.1 — Définir les contrats formels kernel↔agents**
```python
# kernel/contracts/agent.py  (nouveau)
@dataclass
class AgentContract:
    """Ce que tout agent doit respecter pour travailler avec le kernel."""
    agent_id: str
    capability_type: str
    max_duration_s: int
    requires_approval: bool

    async def execute(self, task: Task) -> AgentResult: ...
    def health_check(self) -> HealthStatus: ...
```

**4.2 — Formaliser kernel/runtime/kernel.py**
```python
# kernel/runtime/kernel.py  (nouveau — point d'entrée unique)
class JarvisKernel:
    """
    Le kernel. Un seul objet. Une seule instance.
    Tous les agents et services passent par lui.
    """
    def __init__(self): ...
    async def submit(self, mission: Mission) -> ExecutionHandle: ...
    def register_capability(self, cap: Capability) -> None: ...
    def status(self) -> KernelStatus: ...
```

**4.3 — API = adapter sur le kernel, pas sur MetaOrchestrator**
```python
# api/main.py — actuellement :
from core.meta_orchestrator import get_meta_orchestrator

# api/main.py — cible :
from kernel.runtime.kernel import get_kernel
```

---

### Phase 5 — Consolidation mémoire + critique + feedback
**Durée estimée : 3-4 jours**

**5.1 — MemoryFacade obligatoire**
- Tous les accès mémoire passent par `core/memory_facade.py`
- Le kernel expose la MemoryFacade via `kernel.memory`
- Supprimer les imports directs de `memory/store.py` dans agents/

**5.2 — EvaluationEngine rattaché au kernel**
- `core/evaluation_engine.py` → `kernel/evaluation/engine.py`
- Le kernel évalue les résultats avant de les retourner à l'appelant
- Les scores d'évaluation alimentent `kernel/capabilities/performance.py`

**5.3 — Feedback loop fermée**
```
Résultat d'exécution → EvaluationEngine → PerformanceStore → CapabilityRouter
```
Cette boucle doit être fermée et déterministe, pas optionnelle.

---

### Phase 6 — Auto-amélioration contrôlée par le kernel
**Durée estimée : 2-3 jours**

**Principe** : l'auto-amélioration ne s'exécute QUE si le kernel la gate.

```python
# kernel/improvement/gate.py  (nouveau)
class ImprovementGate:
    """
    Seul le kernel décide si une amélioration peut s'exécuter.
    Aucun module ne peut déclencher une amélioration sans passer par ici.
    """
    def check(self) -> ImprovementDecision:
        # Vérifie : cooldown, consecutive failures, budget, risque
        ...
```

Le `check_improvement_allowed()` de `core/self_improvement/__init__.py` migre ici.
Le SelfImprovementEngine appelle `ImprovementGate.check()` avant toute exécution.

---

### Phase 7 — Montée vers AI OS mature
**Durée estimée : ongoing**

À ce stade, JarvisMax ressemblera à :

```
JarvisKernel (kernel/runtime/kernel.py)
    ├── kernel/state/          — état global cohérent
    ├── kernel/planning/       — goal → plan déterministe
    ├── kernel/policy/         — politique obligatoire non fail-open
    ├── kernel/memory/         — mémoire centralisée
    ├── kernel/capabilities/   — arbitrage des capacités
    ├── kernel/evaluation/     — critique et scoring
    ├── kernel/improvement/    — gating auto-amélioration
    └── kernel/events/         — observabilité

    ↓ contrats formels (kernel/contracts/)

    AgentLayer (agents/)       — spécialistes sous contrat
    CapabilityLayer (tools/, connectors/, skills/)
    ExecutionLayer (executor/)
    MemoryLayer (memory/ via MemoryFacade)
    InterfaceLayer (api/ — adapter uniquement)
```

---

## PARTIE 5 — ACTIONS CONCRÈTES (priorité décroissante)

### Actions immédiates (cette semaine)

| # | Action | Fichier | Complexité |
|---|--------|---------|-----------|
| A1 | Supprimer `core/self_improvement_loop.py` après vérifier SelfImprovementLoop inutilisé | `core/self_improvement_loop.py` | Faible |
| A2 | Casser la circularité : kernel/adapters/policy_adapter.py ne doit plus importer PolicyEngine de core | `kernel/adapters/policy_adapter.py` | Moyen |
| A3 | Rendre `core/memory_facade.py` obligatoire dans `agents/crew.py` | `agents/crew.py` | Faible |
| A4 | Créer `kernel/state/mission_state.py` en extrayant MissionContext + transitions de MetaOrchestrator | `core/meta_orchestrator.py` | Moyen |

### Actions à planifier (prochaines 2 semaines)

| # | Action | Impact architectural |
|---|--------|---------------------|
| B1 | Créer `kernel/planning/` en migrant mission_planner + goal_manager + goal_decomposer | Le planning entre dans le kernel |
| B2 | Absorber JarvisOrchestrator dans MetaOrchestrator — supprimer la couche de délégation | Supprimer 1120 lignes de couplage opaque |
| B3 | Créer `kernel/runtime/kernel.py` — point d'entrée kernel unique `JarvisKernel` | L'API pointe sur le kernel, pas sur MetaOrchestrator |
| B4 | Rendre `kernel/policy/engine.py` non fail-open — la politique est authoritative | La sécurité n'est plus optionnelle |

### Tests à écrire en priorité

```
tests/kernel/test_state_machine.py    — transitions d'état déterministes
tests/kernel/test_policy_engine.py    — politique appliquée sur toutes les actions
tests/kernel/test_capability_arbitration.py — routing déterministe
tests/kernel/test_memory_isolation.py — isolation mémoire entre missions
tests/integration/test_kernel_to_agent.py — contrat kernel→agent
```

### Points d'observabilité à ajouter

```python
# Dans JarvisKernel.submit() :
log.info("kernel_mission_submitted", mission_id=..., goal=..., policy_decision=...)
log.info("kernel_plan_generated",    mission_id=..., steps=..., complexity=...)
log.info("kernel_agent_selected",    mission_id=..., agent=..., capability=...)
log.info("kernel_mission_evaluated", mission_id=..., score=..., lessons=...)
```

---

## PARTIE 6 — RÈGLES D'ARCHITECTURE (non-négociables)

Ces règles s'appliquent immédiatement et pour toujours :

```
RÈGLE K1 : kernel/ n'importe JAMAIS depuis core/, agents/, api/, tools/
RÈGLE K2 : Tout accès mémoire passe par MemoryFacade — jamais direct
RÈGLE K3 : Toute action passe par kernel/policy/engine.py — jamais fail-open
RÈGLE K4 : Aucun nouveau module dans core/ sans le placer dans une sous-couche identifiée
RÈGLE K5 : Tout agent respecte kernel/contracts/agent.py
RÈGLE K6 : L'auto-amélioration passe par kernel/improvement/gate.py
RÈGLE K7 : L'API est un adapter — elle n'orchestre pas, elle transmet
```

---

## RÉSUMÉ EXÉCUTIF

| Dimension | Aujourd'hui | Cible |
|-----------|-------------|-------|
| Kernel réel | MetaOrchestrator + JarvisOrchestrator dans core/ | kernel/runtime/kernel.py |
| Taille du noyau | 2483 lignes dispersées | ≤ 600 lignes, 7 sous-modules |
| Planning | 20+ modules dans core/ | kernel/planning/ |
| Politique | Fail-open, optionelle | Authoritative, synchrone |
| Mémoire | 9 systèmes | 1 façade via kernel.memory |
| Dépendances circulaires | kernel↔core (45 imports croisés) | 0 |
| Observabilité | Events émis optionnellement | Events émis par le kernel sur chaque transition |
| Auto-amélioration | 4 systèmes parallèles | 1 pipeline gatée par le kernel |
| API | Pointe sur MetaOrchestrator | Pointe sur JarvisKernel |
| Verdict | Framework multi-agents | **AI OS en cours de construction** |

La transformation est possible. Elle demande entre 3 et 6 semaines de travail discipliné.
La priorité absolue est la Phase 3 : mettre le planning dans le kernel.
Sans ça, le kernel reste un service parmi d'autres, pas un cerveau.

---

## PARTIE 7 — ÉTAT POST-CONVERGENCE (Passes 8–14)

### 7.1 Kernel Subsystem Map

| Sous-système | Fichier principal | Statut | Passe |
|---|---|---|---|
| kernel.classifier | kernel/classifier/mission_classifier.py | ✅ AUTHORITATIVE | baseline |
| kernel.planner | kernel/planning/planner.py | ✅ AUTHORITATIVE | Pass 9 |
| kernel.router | kernel/routing/router.py | ✅ AUTHORITATIVE | baseline |
| kernel.gate | kernel/improvement/gate.py | ✅ AUTHORITATIVE | baseline |
| kernel.evaluator | kernel/evaluation/scorer.py | ✅ AUTHORITATIVE | Pass 8 |
| kernel.learner | kernel/learning/learner.py | ✅ AUTHORITATIVE | Pass 10 |
| kernel.cognitive | kernel/runtime/kernel.py (run_cognitive_cycle) | ✅ AUTHORITATIVE | Pass 11 |
| kernel.state | kernel/state/mission_state.py | ✅ K1-COMPLIANT | Pass 12 |
| kernel.memory | kernel/memory/interfaces.py | ✅ AUTHORITATIVE | Pass 13 |
| kernel.execute | kernel/execution/contracts.py | ✅ AUTHORITATIVE | Pass 14 |

### 7.2 Pipeline Cognitif Complet (runtime réel)

```
API POST /missions/run
  ↓
api/_deps._get_kernel() → JarvisKernel
  ↓
kernel.execute(ExecutionRequest)
  ↓ policy check → event
  ↓
MetaOrchestrator.run_mission() [délégué via _orchestrator_fn]
  ↓ FIRST CALL: kernel.run_cognitive_cycle(goal)
  │   1. kernel.classify(goal)          → KernelClassification
  │   2. kernel.planning.build(goal)    → KernelPlan
  │   3. kernel.router.route(goal)      → RoutingDecision[]
  │   4. kernel.memory.retrieve_lessons → list[dict]
  ↓
  Fast-paths: classification/plan/route/lessons injectés dans enriched_goal
  ↓
  JarvisOrchestrator / OrchestratorV2 (exécution)
  ↓
  kernel.evaluate(result) → KernelScore
  ↓
  kernel.learn(score)     → KernelLesson → store_lesson()
  ↓
ExecutionResult.from_context(MissionContext)
  ↓
API response
```

### 7.3 Ce qui reste décoratif / à migrer

| Composant | Statut | Action requise |
|---|---|---|
| core/meta_orchestrator.py (1500+ lignes) | 🔶 Coordinateur (was brain) | Simplifier — supprimer phases inline devenues fallbacks morts |
| core/orchestrator.py (~1120 lignes) | 🔶 Exécuteur délégué | Garder mais aligner sur kernel/execution/contracts |
| core/ (366 fichiers) | 🔶 Implémentation | Migrer progressivement vers kernel/ ou couches dédiées |
| agents/ (40 fichiers) | 🔶 Workers non contractualisés | Ajouter kernel/contracts/agent.py (Pass 16) |
| business/ (existant) | 🔶 Non aligné blueprint | Restructurer vers blueprint (Pass 17+) |
| security/ | ❌ Inexistant | Créer (Pass 17) |
| memory/ (top-level) | 🔶 Parallel à kernel.memory | Unifier via MemoryFacade |
| interfaces/ | ❌ Inexistant | Créer avec api/ comme adapter (R8) |

### 7.4 K1 Rule Status — COMPLET

```
kernel/runtime/     ✅ K1 clean
kernel/state/       ✅ K1 clean (Pass 12 — MissionStatus kernel-canonical)
kernel/learning/    ✅ K1 clean
kernel/evaluation/  ✅ K1 clean
kernel/planning/    ✅ K1 clean
kernel/routing/     ✅ K1 clean
kernel/memory/      ✅ K1 clean (Pass 13 — 3 violations corrigées)
kernel/execution/   ✅ K1 clean (Pass 14 — nouveau package)
kernel/contracts/   ✅ K1 clean
kernel/policy/      ✅ K1 clean
```

### 7.5 Actions restantes (priorité décroissante)

| # | Action | Impact | Complexité |
|---|---|---|---|
| P16 | Créer kernel/contracts/agent.py — KernelAgentContract Protocol | R7: agents sous contrat kernel | Faible |
| P17 | Créer security/ skeleton — security/policies, security/risk, security/audit | R3, R10: sécurité native | Moyen |
| P17b | Aligner business/ vers blueprint — business/strategy, finance, ventures | Axe 2 opérationnel | Moyen |
| P18 | Simplifier MetaOrchestrator — supprimer phases inline mortes | Clarté code | Moyen |
| P19 | Unifier memory/ top-level → kernel.memory + MemoryFacade | R6: façade unifiée | Élevé |
| P20 | Créer interfaces/ avec api/ comme sous-dossier | R8: API adapter uniquement | Élevé |

---
*Dernière mise à jour : 2026-03-30 (post-Pass 15)*
*Baseline : 902 fichiers Python, ~268k lignes, kernel/ 20 fichiers ~1700 lignes*
*Post-convergence : kernel/ 49 fichiers ~7046 lignes, 10/10 sous-systèmes ✅*
