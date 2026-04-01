# Result Display — UPDATED ✅

## Change (commit 50d8c0c)
Modified `core/action_executor.py` `_maybe_complete_mission()` to aggregate real
agent results instead of generic summary.

## Before
```
final_output: "3/3 actions exécutées avec succès."
```

## After
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

## How it works
1. When all actions complete, executor iterates over action results
2. Agent name extracted from `action.target` (format: `agent:scout-research`)
3. Each agent's result included up to 1500 chars
4. Output structured as markdown with `## agent-name` sections
5. Sections separated by `---` for clean rendering

## API response
`GET /api/v2/missions/{id}` → `data.final_output` contains full markdown.

Flutter renders this in the mission detail view — user sees actual business
output, not just a count.

## Presentation only
No executor logic modified. Only the output assembly in `_maybe_complete_mission()`.
