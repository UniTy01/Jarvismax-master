# EXECUTOR DEEP AUDIT — JarvisMax
**Date:** 2026-03-27 | **Scope:** executor/ layer complet

---

## 1. TROIS ExecutionResult — PROBLÈME DE CONTRAT

### Version A — runner.py:107 (ActionResult)
```python
@dataclass
class ActionResult:  # canonical name for shell/file action results
    success: bool
    action_type: str
    target: str = ""
    output: str = ""
    error: str = ""
    backup_path: str = ""
    duration_ms: int = 0
```
Utilisée par: SupervisedExecutor (importée en alias ExecutionResult)

### Version B — contracts.py:40 (ExecutionResult — canonique riche)
```python
@dataclass
class ExecutionResult:
    execution_id: str  # uuid auto
    task_id: str = ""
    status: ExecutionStatus  # enum
    success: bool = False
    error_class: ErrorClass  # enum
    error_message: str = ""
    retryable: bool = False
    tool_used: str = ""
    confidence: float = 0.0
    raw_output: str = ""
    # ... 10+ autres champs
```
Utilisée par: CapabilityDispatcher, contracts système

### Version C — safe_executor.py:31 (SI-spécifique)
- applied_change, rollback_triggered, diff_summary
- Spécialisée pour self-improvement pipeline

---

## 2. SUPERVISED_EXECUTOR — IMPORT PROBLÉMATIQUE

**Ligne 35:**
```python
from executor.runner import ActionExecutor, ActionResult as ExecutionResult  # legacy compat
```
**Problème:** Utilise ActionResult (Version A) aliasée en ExecutionResult.
**Impact:** supervised_executor crée des résultats avec action_type, target, output
qui sont incompatibles avec contracts.ExecutionResult (qui a raw_output, tool_used...).

**Risque de migration:** ÉLEVÉ — tous les appelants de supervised_executor.execute()
s'attendent aux champs de ActionResult. Migration nécessite refactor complet.

**Dette documentée:** Garder l'alias legacy mais ajouter une migration progressive
vers contracts.ExecutionResult via un adaptateur.

---

## 3. EXECUTIONENGINE ORPHELIN (execution_engine.py — 542 LOC)

**Contenu:** Thread-pool complet avec retry logic, concurrency control, metrics
**Utilisateurs:** tool_runner.py, API performance endpoint
**Bypassé par:** MetaOrchestrator (appelle delegate.run() directement via ExecutionSupervisor)

**Analyse:**
- L'engine a une valeur pour les tâches batch/parallèles
- Le pipeline principal MetaOrch → Supervisor → Delegate l'ignore complètement
- Pas de déprécation explicite, pas de migration plan

**Recommandation:** Décider explicitement: intégrer ou déprécier.

---

## 4. CAPABILITYDISPATCHER — NON CÂBLÉ

**Fichier:** executor/capability_dispatch.py (185 LOC)
**Capacités:** routing native/plugin/MCP tools, 24/24 tests passent
**Problème:** MetaOrchestrator a la property mais ne l'appelle jamais

**Flux attendu:**
```
Phase 3 → supervise() → delegate.run() → [devrait passer par CapabilityDispatcher]
```
**Flux actuel:**
```
Phase 3 → supervise() → delegate.run() → [bypass CapabilityDispatcher]
```

---

## 5. RECOMMANDATIONS PRIORITAIRES

1. **P1:** Ajouter adaptateur ActionResult → ExecutionResult pour unification progressive
2. **P2:** Appeler capability_dispatcher en Phase 3 pour initialisation/logging
3. **P3:** Décider sort de ExecutionEngine — intégrer au pipeline ou déprécier officiellement
4. **P4:** Créer interface ExecutorContract unifiée que tous les executors implémentent
