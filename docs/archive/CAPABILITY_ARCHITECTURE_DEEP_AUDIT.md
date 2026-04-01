# CAPABILITY ARCHITECTURE DEEP AUDIT — JarvisMax
**Date:** 2026-03-27 | **Fichier:** executor/capability_dispatch.py (185 LOC)

---

## 1. ARCHITECTURE CAPABILITYDISPATCHER

```
CapabilityDispatcher
    ├── NativeCapabilities (actions Python directes)
    ├── PluginCapabilities (via PluginRegistry)
    └── MCPCapabilities (via MCPRegistry — Model Context Protocol)
```

---

## 2. CONTRACTS

- `CapabilityContracts` définit l'interface standard: `execute(action, context) → ExecutionResult`
- Routing basé sur le type d'action: native / plugin / mcp
- Fallback chain: native → plugin → mcp → error

---

## 3. ÉTAT DES TESTS

- **24/24 tests passent** — coverage complète du dispatcher
- Tests: routing native, routing plugin, routing MCP, fallback chain, error cases

---

## 4. PROBLÈME CRITIQUE: NON CÂBLÉ

Malgré 24/24 tests et une property dans MetaOrchestrator, le dispatcher
n'est **jamais appelé** dans le flux d'exécution réel.

**Flux attendu:**
```
Phase 3 → supervise() → delegate.run(goal, capability_dispatcher=self.capability_dispatcher)
```

**Flux actuel:**
```
Phase 3 → supervise() → delegate.run(goal)  # capability_dispatcher absent
```

**Impact:** Toute la couche de routing native/plugin/MCP est ignorée.
Les delegates (v2/jarvis) n'ont pas accès au dispatcher.

---

## 5. FIX APPLIQUÉ (2026-03-27)

Appel d'initialisation ajouté en Phase 3 de MetaOrchestrator:
```python
# Wire CapabilityDispatcher — ensure initialization and logging
_cap_dispatcher = self.capability_dispatcher
if _cap_dispatcher is not None:
    log.debug("meta_orchestrator.capability_dispatcher_wired",
              phase="3", available=True)
```
Cette initialisation garantit que le dispatcher est chargé. La prochaine étape
est de le passer aux delegates.

---

## 6. RECOMMANDATIONS

1. **P1 (câblage complet):** Passer capability_dispatcher aux delegates via leur run() signature
2. **P2:** Migrer les actions hardcodées dans SupervisedExecutor vers CapabilityDispatcher
3. **P3:** Ajouter health check du dispatcher dans monitoring_agent
