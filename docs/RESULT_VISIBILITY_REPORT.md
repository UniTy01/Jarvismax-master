# Result Visibility Report

## Status: FULL RESULTS NOW VISIBLE ✅

### Before
```
final_output: "3/3 actions exécutées avec succès."
```

### After
```markdown
# Résultats de mission (3/3 actions)

## scout-research
[RESEARCH — 2026-03-27 14:19:15]
Mission : Analyser : Define an acquisition strategy...
✅ Recherche terminée — 14 éléments analysés.

---

## shadow-advisor
Score qualité : 8.0/10
Verdict : APPROUVÉ

---

## lens-reviewer
Score qualité : 8.0/10
✅ Review complète.
```

### Implementation
- `core/action_executor.py`: Modified `_maybe_complete_mission()` to aggregate
  real agent results from action objects instead of generic summary
- Agent names extracted from `action.target` field (format: `agent:scout-research`)
- Each agent's result truncated to 1500 chars max
- Structured markdown output with agent sections separated by `---`

### API response
- `GET /api/v2/missions/{id}` → `data.final_output` contains full markdown
- Flutter can render this directly in mission detail view

### Limitation
- Agent outputs are infrastructure checks (API status, vault, workspace scan)
  rather than actual business analysis — this is an agent implementation issue,
  not a pipeline issue. The pipeline correctly aggregates whatever agents produce.
