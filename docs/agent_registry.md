# JarvisMax — Registre des Agents

> Version : 2.0 | Date : 2026-03-19

---

## Format du Registre

Chaque agent est décrit par :
- **Rôle** : mission principale
- **Entrées** : ce que l'agent consomme
- **Sorties** : ce que l'agent produit
- **Outils** : capacités utilisées
- **Collaboration** : avec quels agents
- **Conditions d'échec** : quand l'agent échoue
- **Logs associés** : clés structlog

---

## Agents Core

### 1. AtlasDirector (`atlas-director`)

**Rôle** : Orchestration du plan pour les missions complexes (score > 0.60).
Décompose un objectif en tâches précises pour chaque agent.

**Entrées** :
- `session.user_input` : objectif de la mission
- `session.get_output("vault-memory")` : contexte mémorisé

**Sorties** :
- `session.mission_summary` : résumé de la mission en 1 phrase
- `session.agents_plan` : liste des tâches `[{agent, task, priority}]`
- `session.needs_actions` : bool

**Outils** : LLM (rôle `director`, timeout 60s)

**Collaboration** :
- Appelé avant tous les autres agents
- Active `vault-memory` avant son propre appel

**Conditions d'échec** :
- Réponse LLM non JSON parseable → fallback plan statique (TaskRouter)
- Plan vide retourné → exception levée → fallback automatique

**Logs** : `atlas_director_start`, `director_parse_failed`, `auto_atlas_director_used`

---

### 2. ScoutResearch (`scout-research`)

**Rôle** : Recherche, analyse et synthèse d'informations avec rigueur scientifique.

**Entrées** :
- `session.mission_summary` + tâche assignée
- Contexte agents (`_ctx()`), VectorMemory (`_vec_ctx()`), AgentMemory (`_mem_ctx()`)
- KnowledgeMemory (`_knowledge_ctx()`)

**Sorties** :
```
## Synthèse (2-3 phrases)
## Faits clés
## Tendances identifiées
## Acteurs principaux
## Risques / Opportunités
## Limites de cette analyse
```

**Outils** : LLM (rôle `research`), VectorMemory, AgentMemory, KnowledgeMemory

**Collaboration** : Fournit contexte à MapPlanner, ForgeBuilder, ShadowAdvisor

**Conditions d'échec** : Timeout LLM, réponse vide

**Logs** : `scout-research_start`, `scout-research_done`, `scout-research_timeout`

---

### 3. MapPlanner (`map-planner`)

**Rôle** : Transformation d'objectifs en plans SMART exécutables.

**Entrées** : Mission + contexte ScoutResearch

**Sorties** :
```
## Objectif (mesurable)
## MVP (Minimum Viable Product)
## Jalons (SMART, avec dates)
## Dépendances critiques
## Risques (tableau)
## Estimation effort
```

**Outils** : LLM (rôle `planner`) + SelfCriticMixin (round de révision si score < 6.0)

**Collaboration** : Reçoit de ScoutResearch, fournit à ForgeBuilder

**Conditions d'échec** : Score auto-critique < 6.0 après révision → output degraded

**Logs** : `map-planner_start`, `map-planner_done`, `self_critic_score`

---

### 4. ForgeBuilder (`forge-builder`)

**Rôle** : Génération de code Python/Shell/YAML/JSON production-ready.

**Entrées** : Tâche + contexte (Scout + Planner)

**Sorties** :
```
## Description (choix techniques)
## Code (blocs formatés)
## Utilisation
## Tests recommandés
```

**Outils** : LLM (rôle `builder`, timeout 180s) + SelfCriticMixin (seuil 6.5)

**Collaboration** : Reçoit de MapPlanner, fournit à PulseOps

**Conditions d'échec** : Code généré avec erreurs de sécurité → REFUSÉ par LensReviewer

**Logs** : `forge-builder_start`, `forge-builder_done`, `forge-builder_timeout`

---

### 5. LensReviewer (`lens-reviewer`)

**Rôle** : Contrôle qualité et validation des travaux des autres agents.

**Entrées** : Toutes les sorties agents (`_ctx()`)

**Sorties** :
```
## Score global : X/10
## Points forts
## Problèmes et incohérences
## Risques de sécurité
## Améliorations concrètes
## Verdict : APPROUVÉ / APPROUVÉ_AVEC_RÉSERVES / REFUSÉ
```

**Règles** : Score < 6/10 → REFUSÉ obligatoire. Problème sécurité → REFUSÉ automatique.

**Collaboration** : Toujours en dernier (priorité 3+)

**Conditions d'échec** : Timeout, réponse hors format

**Logs** : `lens-reviewer_start`, `lens-reviewer_done`

---

### 6. VaultMemory (`vault-memory`)

**Rôle** : Rappel de contexte mémorisé pertinent pour la mission.

**Entrées** : `session.user_input`

**Sorties** : Résumé du contexte mémorisé pertinent

**Outils** : MemoryStore (recherche par similarité), LLM pour synthèse

**Collaboration** : Toujours en premier (priorité 1)

**Conditions d'échec** : MemoryStore indisponible → message "Mémoire temporairement indisponible"

**Logs** : `vault_recall_failed`, `vault-memory_done`

---

### 7. ShadowAdvisor (`shadow-advisor`)

**Rôle** : Validation critique structurée de toute décision, plan ou code.

**Entrées** : Mission + toutes les sorties agents

**Sorties** : JSON structuré `{decision, confidence, blocking_issues, risks, improvements, final_score}`

**Processus obligatoire** : 6 questions critiques dans l'ordre
1. Qu'est-ce qui peut casser ?
2. Qu'est-ce qui est supposé sans preuve ?
3. Qu'est-ce qui manque pour valider ?
4. Quelle est la contradiction principale ?
5. Quelle est la pire conséquence si on se trompe ?
6. Quelle amélioration réduit le plus le risque ?

**Sorties possibles** : GO (risques acceptables) | IMPROVE (corrections nécessaires) | NO-GO (risques critiques)

**Logs** : `shadow_advisor_v2_done`, `shadow_advisor_structure_violations`

---

### 8. PulseOps (`pulse-ops`)

**Rôle** : Préparation des actions concrètes à exécuter.

**Entrées** : Toutes les sorties agents

**Sorties** : JSON `{actions: [{action_type, target, content, ...}], summary}`

**Types d'actions** : `create_file | write_file | replace_in_file | run_command | backup_file`

**Collaboration** : Nécessite ForgeBuilder pour les actions de code. Déclenche ActionExecutor.

**Conditions d'échec** : JSON non parseable → `session._raw_actions = []`

**Logs** : `pulse_ops_parse_failed`

---

### 9. NightWorker (`night-worker`)

**Rôle** : Travail long multi-cycles sur des missions complexes.

**Entrées** : Mission + cycle courant + productions précédentes

**Sorties** : Production substantielle (code, analyses, rapports)

**Outils** : LLM (rôle `builder`, timeout 300s)

**Collaboration** : Délègue à `NightWorkerEngine` pour les cycles

**Logs** : Géré par `NightWorkerEngine`

---

## Nouveaux Agents (v2)

### 10. DebugAgent (`debug-agent`)

**Rôle** : Analyse des erreurs agents et proposition de corrections.

**Entrées** :
- `ErrorReport` : type d'erreur, message, stack trace, contexte
- Historique de session

**Sorties** :
- `AgentResult` avec `fix_proposal` (patch de code ou config à modifier)
- `confidence` (0.0–1.0)
- `root_cause` (classification : timeout | LLM | configuration | logique)

**Déclenchement** : Appelé automatiquement par orchestrateur si un agent échoue 2+ fois

**Conditions d'échec** : LLM ne trouve pas de root cause → rapport "inconclusive"

**Logs** : `debug_agent_start`, `debug_agent_root_cause`, `debug_agent_proposal`

---

### 11. RecoveryAgent (`recovery-agent`)

**Rôle** : Rollback et reprise contrôlée après erreur.

**Entrées** :
- Historique d'exécution (`DecisionReplay`)
- Liste des backups disponibles (`BACKUP_DIR`)
- Proposition de DebugAgent (optionnel)

**Sorties** :
- `AgentResult` avec actions de rollback executées
- `recovery_status` : `restored | partial | failed`
- Nouveau state de mission : `recovered | aborted`

**Outils** : `ActionExecutor` (restore_backup), MemoryStore (rollback d'état)

**Déclenchement** : Appelé par orchestrateur après DebugAgent si fix non auto-applicable

**Logs** : `recovery_agent_start`, `recovery_rollback_applied`, `recovery_failed`

---

### 12. MonitoringAgent (`monitoring-agent`)

**Rôle** : Agrégation de tous les signaux de santé du système.

**Entrées** :
- `SystemState` : statut des modules
- `LLMPerformanceMonitor` : drift latence/erreur
- `MetricsCollector` : métriques runs
- `TaskQueue` : files et état des tâches

**Sorties** :
- `HealthReport` JSON (status global + par composant)
- Alertes si seuils dépassés

**Déclenchement** : Appelé par `/api/v2/health` et `/api/v2/diagnostics`

**Logs** : `monitoring_agent_check`, `monitoring_alert_triggered`

---

## Tableau de Routing

| Mode | Agents (par priorité) |
|------|----------------------|
| CHAT | (direct LLM, pas d'agent) |
| RESEARCH | vault-memory → scout-research + shadow-advisor → lens-reviewer |
| PLAN | vault-memory → scout-research + map-planner + shadow-advisor → lens-reviewer |
| CODE | vault-memory → scout-research + forge-builder → lens-reviewer → pulse-ops |
| AUTO | vault-memory → scout-research + shadow-advisor + map-planner → forge-builder → lens-reviewer → pulse-ops |
| NIGHT | vault-memory → atlas-director (puis NightWorkerEngine cycles) |
| IMPROVE | vault-memory (puis SelfImproveEngine) |

---

## Protocoles de Collaboration

### Règles générales
1. Priorité ≤ N peut s'exécuter en parallèle avec d'autres agents de priorité N
2. Un agent ne peut démarrer que si tous les agents de priorité inférieure ont terminé (succès ou skip)
3. `vault-memory` est toujours en priorité 1 et s'exécute avant tous les autres
4. `lens-reviewer` est toujours en dernière priorité

### Gestion des dépendances (nouveau en v2)
Si l'agent A dépend de B et que B échoue :
- `dependency_mode: skip` → A passe avec contexte incomplet (warning)
- `dependency_mode: block` → A est annulé, erreur remontée
- `dependency_mode: retry` → orchestrateur retry B avant de lancer A
