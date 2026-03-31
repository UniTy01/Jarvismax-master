"""
JARVIS MAX — Mission Repair
Répare les missions APPROVED dont toutes les actions sont déjà terminées (EXECUTED/FAILED/REJECTED).
Appelé au démarrage de l'API pour corriger l'historique legacy.
"""
from __future__ import annotations
import structlog

log = structlog.get_logger()

_TERMINAL = {"EXECUTED", "FAILED", "REJECTED"}


def repair_approved_missions(limit: int = 500) -> dict:
    """
    Parcourt toutes les missions APPROVED.
    Si toutes leurs actions sont en état terminal → marque la mission DONE.
    Si aucune action n'existe ou si des actions sont encore en cours → laisse APPROVED.

    Returns:
        dict avec 'repaired', 'skipped', 'no_actions', 'errors'
    """
    try:
        from core.mission_system import get_mission_system
        from core.action_queue import get_action_queue
    except Exception as e:
        log.warning("mission_repair_import_failed", error=str(e))
        return {"repaired": 0, "skipped": 0, "no_actions": 0, "errors": 1}

    ms = get_mission_system()
    q  = get_action_queue()

    repaired   = 0
    skipped    = 0
    no_actions = 0
    errors     = 0

    try:
        missions = ms.list_missions(limit=limit)
    except Exception as e:
        log.error("mission_repair_list_failed", error=str(e))
        return {"repaired": 0, "skipped": 0, "no_actions": 0, "errors": 1}

    for mission in missions:
        if mission.status != "APPROVED":
            continue

        try:
            acts = q.for_mission(mission.mission_id)

            if not acts:
                # Mission sans actions — on ne peut pas la marquer DONE automatiquement
                no_actions += 1
                continue

            if all(a.status in _TERMINAL for a in acts):
                executed = sum(1 for a in acts if a.status == "EXECUTED")
                failed   = sum(1 for a in acts if a.status == "FAILED")
                ms.complete(
                    mission.mission_id,
                    result_text=(
                        f"[REPAIR] {executed}/{len(acts)} actions exécutées"
                        + (f", {failed} échouées" if failed else "")
                        + "."
                    ),
                )
                log.info(
                    "mission_repaired",
                    mission_id=mission.mission_id,
                    executed=executed,
                    total=len(acts),
                )
                repaired += 1
            else:
                # Des actions sont encore PENDING ou APPROVED → laisser en place
                skipped += 1

        except Exception as e:
            log.warning("mission_repair_error", mission_id=mission.mission_id, error=str(e))
            errors += 1

    log.info(
        "mission_repair_complete",
        repaired=repaired,
        skipped=skipped,
        no_actions=no_actions,
        errors=errors,
    )
    return {
        "repaired":   repaired,
        "skipped":    skipped,
        "no_actions": no_actions,
        "errors":     errors,
    }
