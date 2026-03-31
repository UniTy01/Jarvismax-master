# SIMPLICITY REVIEW — JarvisMax
**Date:** 2026-03-27 | **Scope:** Complexité accidentelle, duplications, refactor candidats

---

## 1. FICHIERS TROP LONGS

| Fichier | LOC | Seuil recommandé | Action |
|---|---|---|---|
| memory/memory_bus.py | 801 | 400 | Splitter en 3 modules |
| executor/execution_engine.py | 542 | 400 | Intégrer ou déprécier |
| core/meta_orchestrator.py | 498 | 400 | Acceptable (pipeline central) |
| executor/supervised_executor.py | ~400 | 400 | Limite atteinte |

---

## 2. DUPLICATIONS IDENTIFIÉES

### 3 ExecutionResult
- `executor/runner.py`: `ActionResult` (simple)
- `executor/contracts.py`: `ExecutionResult` (canonique)
- `core/self_improvement/safe_executor.py`: version SI
**Complexité accidentelle:** 3 représentations du même concept.

### Orchestrators multiples
- `core/meta_orchestrator.py` (principal)
- `core/orchestrator_v2.py` (delegate v2)
- `core/orchestration/execution_supervisor.py` (supervision)
- `executor/supervised_executor.py` (exécution supervisée)
**Overlap:** supervision à 2 niveaux sans délimitation claire.

---

## 3. IMPORTS CIRCULAIRES POTENTIELS

Chaînes d'import à risque:
- `meta_orchestrator` → lazy imports (mitigé)
- `capability_dispatch` ↔ `contracts` (vérifier)
- `memory_facade` → `memory_bus` → backends (chaîne profonde)

---

## 4. COMPLEXITÉ ACCIDENTELLE PAR COMPOSANT

| Composant | Complexité | Justifiée? |
|---|---|---|
| MemoryBus (801 LOC) | Haute | Non — candidat split |
| ExecutionEngine (542 LOC) | Haute | Partielle — bypassé |
| MetaOrchestrator (498 LOC) | Moyenne | Oui — pipeline central |
| SupervisedExecutor (~400 LOC) | Moyenne | Oui — gestion risque |

---

## 5. RECOMMANDATIONS PAR PRIORITÉ

### Priorité 1 (semaine 1)
- Décider sort de ExecutionEngine: intégrer proprement ou ajouter `# DEPRECATED` et ticket
- Câbler CapabilityDispatcher dans le flux Phase 3

### Priorité 2 (sprint 1)
- Splitter MemoryBus en memory_router + memory_serializer + memory_scorer
- Unifier ExecutionResult: ajouter adaptateur ActionResult → contracts.ExecutionResult

### Priorité 3 (sprint 2)
- Réduire supervised_executor.py via CapabilityDispatcher (actions → dispatcher)
- Ajouter type hints stricts sur toutes les interfaces publiques
