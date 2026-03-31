"""
Pipeline Guard — garantit qu'une mission renvoie toujours un output non vide.
Utilisé par api/main.py pour protéger final_output.
"""
import logging
from typing import List, Any, Optional

logger = logging.getLogger(__name__)

_FALLBACK_MSG = "Mission exécutée. Je rencontre un problème temporaire mais je continue de fonctionner."


def synthesize_from_agent_outputs(agent_outputs: List[Any]) -> str:
    """Construit un final_output depuis agent_outputs quand le principal est vide."""
    parts = []
    for ao in (agent_outputs or []):
        for field in ("result", "output", "content", "reasoning"):
            val = ao.get(field, "") if isinstance(ao, dict) else getattr(ao, field, "")
            if val and str(val).strip():
                name = ao.get("agent_name", "agent") if isinstance(ao, dict) else getattr(ao, "agent_name", "agent")
                parts.append(f"[{name}] {str(val).strip()}")
                break
    return "\n\n".join(parts) if parts else ""


def build_safe_final_output(
    raw_output: Optional[str],
    agent_outputs: List[Any],
    mission_id: str = "",
) -> str:
    """
    Garantit un final_output non vide selon priorité :
    1. raw_output explicite
    2. synthèse depuis agent_outputs
    3. fallback message système
    """
    # Priorité 1
    if raw_output and raw_output.strip():
        return raw_output.strip()

    logger.warning(
        "[PIPELINE GUARD] final_output vide détecté — mission=%s agent_count=%d",
        mission_id, len(agent_outputs or [])
    )

    # Priorité 2
    synthesized = synthesize_from_agent_outputs(agent_outputs)
    if synthesized:
        logger.info("[PIPELINE GUARD] fallback=synthesis agent_count=%d", len(agent_outputs))
        return synthesized

    # Priorité 3
    logger.warning(
        "[PIPELINE GUARD] fallback=system_message agent_count=%d mission=%s",
        len(agent_outputs or []), mission_id
    )
    return _FALLBACK_MSG


def build_safe_fallback_output(
    agent_outputs: List[Any],
    executor_status: str = "unknown",
    mission_id: str = "",
) -> dict:
    """Retourne un dict structuré pour cas d'échec total."""
    return {
        "status": "fallback",
        "final_output": build_safe_final_output(None, agent_outputs, mission_id),
        "debug": {
            "agent_count": len(agent_outputs or []),
            "executor_status": executor_status,
            "fallback_used": True,
        }
    }
