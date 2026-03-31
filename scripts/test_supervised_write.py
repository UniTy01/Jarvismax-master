"""
JARVIS MAX — Test de non-régression : supervision des missions write.

Vérifie que :
  1. Une mission "créer un fichier test.txt dans workspace" est classée
     action_type='write' et risk>='MEDIUM' par classify_action().
  2. En mode SUPERVISED, la mission ne passe PAS automatiquement en DONE.
  3. La mission est mise en PENDING_VALIDATION (pas APPROVED, pas DONE).
  4. workspace/test.txt n'existe PAS (aucune écriture sans approbation).

Résultat attendu : PASS
Résultat de régression : FAIL si mission → DONE sans approbation,
                          ou si workspace/test.txt existe.

Usage :
    cd /app   (ou racine du repo)
    python scripts/test_supervised_write.py
"""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

# ── Setup path ───────────────────────────────────────────────────────────────
_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

# ── Couleurs terminal ─────────────────────────────────────────────────────────

def _green(s: str) -> str: return f"\033[92m{s}\033[0m"
def _red(s:   str) -> str: return f"\033[91m{s}\033[0m"
def _bold(s:  str) -> str: return f"\033[1m{s}\033[0m"


PASS = _green("PASS")
FAIL = _red("FAIL")

failures: list[str] = []


def check(name: str, condition: bool, detail: str = "") -> None:
    if condition:
        print(f"  {PASS}  {name}")
    else:
        msg = f"{name}" + (f" — {detail}" if detail else "")
        print(f"  {FAIL}  {msg}")
        failures.append(msg)


# ══════════════════════════════════════════════════════════════════════════════
# Test 1 — classify_action()
# ══════════════════════════════════════════════════════════════════════════════

def test_classify_action() -> None:
    print(_bold("\n[1] classify_action() — classification du goal"))
    from core.mission_system import classify_action, _RISK_ORDER

    goal = "créer un fichier test.txt dans workspace"
    action_type, risk = classify_action(goal)

    check("action_type == 'write'",      action_type == "write",
          f"got '{action_type}'")
    check("risk >= 'MEDIUM'",
          _RISK_ORDER.index(risk) >= _RISK_ORDER.index("MEDIUM"),
          f"got '{risk}'")

    # Cas négatif : pure analyse ne devrait pas être write
    at2, r2 = classify_action("analyser les logs du système")
    check("analyze goal -> action_type != 'write'",  at2 != "write",
          f"got '{at2}' for analyze goal")

    # Variantes françaises
    for g in [
        "write a file in workspace",
        "create test.txt",
        "modifier le fichier config",
        "supprimer le fichier tmp",
    ]:
        at, _ = classify_action(g)
        check(f"'{g[:40]}' -> write", at == "write", f"got '{at}'")


# ══════════════════════════════════════════════════════════════════════════════
# Test 2 — MissionSystem.submit() en mode SUPERVISED
# ══════════════════════════════════════════════════════════════════════════════

def test_supervised_mission() -> None:
    print(_bold("\n[2] MissionSystem.submit() en mode SUPERVISED"))

    # Stockage temporaire (pas de pollution workspace réel)
    import tempfile, json
    tmp_dir  = Path(tempfile.mkdtemp())
    tmp_json = tmp_dir / "missions.json"

    from core.mission_system import MissionSystem, MissionStatus
    from core.mode_system    import ModeSystem

    # Mode SUPERVISED obligatoire
    mode_sys = ModeSystem(storage=tmp_dir / "system_mode.json")
    mode_sys.set_mode("SUPERVISED", changed_by="test")

    ms = MissionSystem(
        storage=tmp_json,
        mode_system=mode_sys,
    )

    goal   = "créer un fichier test.txt dans workspace"
    result = ms.submit(goal)

    print(f"   mission_id  : {result.mission_id}")
    print(f"   status      : {result.status}")
    print(f"   plan_risk   : {result.plan_risk}")
    print(f"   plan_steps  : {json.dumps([{k:v for k,v in s.items() if k in ['agent','action_type','risk']} for s in result.plan_steps], indent=4)}")

    check("status == PENDING_VALIDATION",
          result.status == MissionStatus.PENDING_VALIDATION,
          f"got '{result.status}'")

    check("status != DONE",
          result.status != MissionStatus.DONE,
          f"got '{result.status}'")

    check("status != APPROVED",
          result.status != MissionStatus.APPROVED,
          f"mission was auto-approved — SUPERVISED guard failed")

    check("requires_validation == True",
          result.requires_validation is True,
          f"got {result.requires_validation}")

    # Vérifier que plan_risk >= MEDIUM
    from core.mission_system import _RISK_ORDER
    check("plan_risk >= MEDIUM",
          _RISK_ORDER.index(result.plan_risk) >= _RISK_ORDER.index("MEDIUM"),
          f"got '{result.plan_risk}'")

    # Vérifier que l'étape forge-builder a action_type=write
    write_steps = [
        s for s in result.plan_steps
        if s.get("agent") in {"forge-builder", "map-planner"}
           and s.get("action_type") == "write"
    ]
    check("forge-builder/map-planner step has action_type='write'",
          len(write_steps) > 0,
          "no write step found in plan")

    return result.mission_id, ms


# ══════════════════════════════════════════════════════════════════════════════
# Test 3 — complete() garde-fou PENDING_VALIDATION
# ══════════════════════════════════════════════════════════════════════════════

def test_complete_guard(mission_id: str, ms) -> None:
    print(_bold("\n[3] complete() garde-fou PENDING_VALIDATION"))

    from core.mission_system import MissionStatus

    # Tenter de compléter une mission PENDING — doit être bloqué
    ms.complete(mission_id)
    r = ms.get(mission_id)

    check("complete() n'a pas mis DONE une mission PENDING_VALIDATION",
          r.status != MissionStatus.DONE,
          f"status after complete() = '{r.status}'")

    check("status reste PENDING_VALIDATION après complete() bloqué",
          r.status == MissionStatus.PENDING_VALIDATION,
          f"got '{r.status}'")


# ══════════════════════════════════════════════════════════════════════════════
# Test 4 — workspace/test.txt ne doit PAS exister
# ══════════════════════════════════════════════════════════════════════════════

def test_no_file_created() -> None:
    print(_bold("\n[4] Vérification workspace/test.txt absent"))

    # Cherche dans workspace/ de la racine du repo
    candidates = [
        _ROOT / "workspace" / "test.txt",
        Path("workspace") / "test.txt",
        Path("/app/workspace/test.txt"),
    ]
    for p in candidates:
        if p.exists():
            check(f"workspace/test.txt absent ({p})", False,
                  f"FICHIER TROUVÉ : {p} — écriture sans approbation !")
            return

    check("workspace/test.txt absent (aucune écriture sans approbation)", True)


# ══════════════════════════════════════════════════════════════════════════════
# Main
# ══════════════════════════════════════════════════════════════════════════════

def main() -> int:
    print(_bold("=" * 60))
    print(_bold("JARVIS MAX — Test supervision mission write (SUPERVISED)"))
    print(_bold("=" * 60))

    test_classify_action()
    mission_id, ms = test_supervised_mission()
    test_complete_guard(mission_id, ms)
    test_no_file_created()

    print()
    if failures:
        print(_red(f"RÉSULTAT : {len(failures)} FAIL(S)"))
        for f in failures:
            print(f"  • {f}")
        return 1
    else:
        print(_green("RESULTAT : TOUS LES TESTS PASSENT [OK]"))
        return 0


if __name__ == "__main__":
    sys.exit(main())
