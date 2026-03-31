# MEMORY DEEP AUDIT — JarvisMax
**Date:** 2026-03-27 | **Scope:** Stack mémoire complète

---

## 1. ARCHITECTURE MÉMOIRE

```
MetaOrchestrator (Phase 2 + Phase 5)
    └── MemoryFacade (core/memory_facade.py ~150 LOC)
            └── MemoryBus (memory/memory_bus.py 801 LOC)
                    ├── VectorBackend (ChromaDB/FAISS)
                    ├── EpisodicBackend (JSONL)
                    ├── SemanticBackend (embeddings)
                    └── AgentCapabilityScore (scoring)
```

---

## 2. MEMORYFACADE — INTERFACE PROPRE

**Rôle:** Abstraction entre MetaOrchestrator et MemoryBus.
**Méthodes clés:**
- `assemble_context(goal, session_id)` → string enrichi pour Phase 2
- `store_outcome(mission_id, goal, outcome, ...)` → Phase 5
- `get_relevant_memories(query)` → retrieval vectoriel

**Forces:**
- Interface simple (~150 LOC)
- Découplage total des backends

---

## 3. MEMORYBUS — 801 LOC (CANDIDAT REFACTOR)

**Problème:** 801 lignes est au-dessus du seuil de maintenabilité (~400 LOC).
**Contenu:** Routing multi-backend, serialization, embedding, scoring, cache.
**Recommandation:** Extraire en 3 modules:
- `memory_router.py` — routing logic
- `memory_serializer.py` — serialization/embedding  
- `memory_scorer.py` — AgentCapabilityScore

---

## 4. AGENTCAPABILITYSCORE

**Rôle:** Score les capabilities d'un agent basé sur son historique d'exécution.
**Intégration:** Via MemoryBus, accessible par MetaOrchestrator.
**État:** Fonctionnel mais pas exposé directement dans le pipeline Phase 2.

---

## 5. MULTI-BACKEND ROUTING

| Backend | Usage | État |
|---|---|---|
| VectorDB (Chroma/FAISS) | Semantic search | ✅ |
| Episodic (JSONL) | Historique séquentiel | ✅ |
| Semantic | Embeddings long-terme | ✅ |

---

## 6. FINDINGS

- **F1:** MemoryBus trop volumineux (801 LOC) — refactor recommandé
- **F2:** AgentCapabilityScore non exposé en Phase 2 pour enrichissement de contexte
- **F3:** Pas de TTL/expiration sur les mémoires episodiques
- **F4:** Pas de mécanisme de déduplication des outcomes similaires

---

## 7. RECOMMANDATIONS

1. Splitter MemoryBus en 3 modules de ~250 LOC chacun
2. Exposer AgentCapabilityScore dans l'enrichissement de contexte Phase 2
3. Ajouter TTL configurable sur les mémoires episodiques
