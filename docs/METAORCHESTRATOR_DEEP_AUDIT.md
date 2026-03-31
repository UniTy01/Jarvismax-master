# METAORCHESTRATOR DEEP AUDIT — JarvisMax
**Date:** 2026-03-27 | **Fichier:** core/meta_orchestrator.py (498 LOC)

---

## 1. ARCHITECTURE 5 PHASES

### Phase 1 — Classification (lignes ~180-220)
- **Appel:** `self.classifier.classify(goal, context)`
- **Nature:** Déterministe — aucun LLM requis
- **Output:** risk_level, needs_approval, use_budget, mode
- **Force:** Séparation claire intent vs execution

### Phase 2 — Assemblage de contexte (lignes ~220-230)
- **Appel:** `self.memory_facade.assemble_context()` + `skill_service`
- **Nature:** Enrichissement de goal avec skills + memories
- **Output:** `enriched_goal` — string augmenté de prior experience
- **Force:** Contextualisation cohérente avant exécution

### Phase 3 — Exécution supervisée (lignes ~234-260)
- **Appel:** `supervise(delegate.run, ...)` via ExecutionSupervisor
- **Delegate:** `self.v2` (OrchestratorV2) ou `self.jarvis` selon budget
- **Point faible:** CapabilityDispatcher est une property lazy mais jamais appelée ici

### Phase 4 — Enregistrement outcome (lignes ~265-285)
- **Appel:** `self.skill_service.record_outcome(goal, outcome, ...)`
- **Nature:** Apprentissage des succès/échecs de skills

### Phase 5 — Mémorisation (lignes ~285-300)
- **Appel:** `self.memory_facade.store_outcome(mid, goal, outcome, ...)`
- **Nature:** Stockage structuré en mémoire vectorielle

---

## 2. LAZY IMPORTS — PATTERN UTILISÉ

MetaOrchestrator utilise systématiquement des lazy imports dans les properties:
```python
@property
def v2(self):
    if not hasattr(self, "_v2"):
        from core.orchestrator_v2 import OrchestratorV2
        self._v2 = OrchestratorV2(self.s)
    return self._v2
```
**Avantage:** Startup rapide, imports circulaires évités.
**Risque:** Erreurs de import tardives — difficiles à détecter en tests.

---

## 3. CAPABILITY_DISPATCHER — ORPHELIN CÂBLÉ

```python
@property
def capability_dispatcher(self):  # lignes 125-135
    if not hasattr(self, "_capability_dispatcher"):
        from executor.capability_dispatch import get_capability_dispatcher
        self._capability_dispatcher = get_capability_dispatcher()
    return self._capability_dispatcher
```
La property est définie et correcte, MAIS aucun appel dans Phase 3.
Fix recommandé: ajouter `_ = self.capability_dispatcher` en Phase 3 pour initialisation.

---

## 4. DELEGATES LEGACY

- `self.v2` → OrchestratorV2 (budget-aware)
- `self.jarvis` → JarvisOrchestrator (legacy)
- Les delegates ne reçoivent pas le CapabilityDispatcher dans leur contexte

---

## 5. POINTS FORTS
- Pipeline 5 phases clair et cohérent
- MissionContext + MissionStatus state machine propre
- Structlog avec trace complète par phase
- Lazy imports évitant les problèmes de circularité

## 6. POINTS FAIBLES
- CapabilityDispatcher non câblé (24/24 tests passent mais feature silencieuse)
- Delegates legacy non migrés vers ExecutionEngine
- Phase 3b learning loop (lignes ~299) incomplète selon comments

## 7. RECOMMANDATIONS
1. Appeler `self.capability_dispatcher` en Phase 3 pour initialisation/logging
2. Migrer les delegates vers une interface unifiée avec CapabilityDispatcher
3. Documenter explicitement pourquoi ExecutionEngine est bypassé
