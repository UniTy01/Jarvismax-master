"""
JARVIS MAX — Peer Review Engine (Phase 3)
==========================================
Évaluation inter-agents : Agent B révise l'output d'Agent A.

Règles :
    - La peer review ne bloque JAMAIS l'exécution si confidence >= PEER_REVIEW_THRESHOLD
    - Elle est fire-and-forget par défaut (async, non bloquant)
    - Elle est déclenchée uniquement si un reviewer est disponible
    - Le résultat est loggé et mémorisé, pas retourné à l'agent source

Usage :
    from agents.peer_review import PeerReviewEngine

    engine  = PeerReviewEngine(settings)
    result  = await engine.review(contract, reviewer_name="lens-reviewer")
    # result.approved  →  True / False
    # result.feedback  →  str
    # result.overall_score  →  float 0-10
"""
from __future__ import annotations

import asyncio
import json
import structlog
from typing import Any

from agents.contracts import (
    AgentContract, ReviewResult,
    PEER_REVIEW_THRESHOLD, PEER_REVIEW_PASS_SCORE,
)

log = structlog.get_logger(__name__)

# Reviewers par agent (qui peut revoir qui)
REVIEWER_FOR: dict[str, str] = {
    "scout-research":  "lens-reviewer",
    "forge-builder":   "lens-reviewer",
    "map-planner":     "shadow-advisor",
    "debug-agent":     "lens-reviewer",
    "workflow-agent":  "shadow-advisor",
}

_REVIEW_SYSTEM = """Tu es un agent de révision qualité pour un système IA multi-agents.
Tu dois évaluer la sortie d'un autre agent sur 4 dimensions, chacune notée de 0 à 10.

IMPORTANT: Réponds UNIQUEMENT en JSON valide avec ce format exact:
{
  "quality": <float 0-10>,
  "consistency": <float 0-10>,
  "risk": <float 0-10>,
  "completeness": <float 0-10>,
  "feedback": "<string court, max 200 chars>"
}

Dimensions:
- quality: la sortie est-elle de bonne qualité et utile ?
- consistency: est-elle cohérente avec la mission et le contexte ?
- risk: niveau de risque des actions proposées (0=sans risque, 10=très risqué)
- completeness: couvre-t-elle bien la tâche demandée ?
"""


class PeerReviewEngine:
    """
    Moteur de peer review inter-agents.
    Utilise un LLM pour scorer la sortie d'un agent.
    """

    def __init__(self, settings):
        self.s = settings

    async def should_review(self, contract: AgentContract) -> bool:
        """
        Détermine si une peer review est nécessaire.
        True seulement si:
            - confidence < PEER_REVIEW_THRESHOLD
            - un reviewer est disponible pour cet agent
        """
        if contract.confidence >= PEER_REVIEW_THRESHOLD:
            return False
        return contract.agent_id in REVIEWER_FOR

    async def review(
        self,
        contract:      AgentContract,
        reviewer_name: str = "",
        timeout_s:     float = 30.0,
    ) -> ReviewResult:
        """
        Lance une peer review de contract par reviewer_name.
        Si reviewer_name vide, utilise REVIEWER_FOR[contract.agent_id].

        Returns ReviewResult — never raises (safe for fire-and-forget).
        """
        reviewer = reviewer_name or REVIEWER_FOR.get(contract.agent_id, "shadow-advisor")

        try:
            result = await asyncio.wait_for(
                self._do_review(contract, reviewer),
                timeout=timeout_s,
            )
            log.info(
                "peer_review.done",
                reviewer    = reviewer,
                reviewed    = contract.agent_id,
                score       = result.overall_score,
                approved    = result.approved,
            )
            return result

        except asyncio.TimeoutError:
            log.warning("peer_review.timeout", reviewer=reviewer,
                        reviewed=contract.agent_id)
            return self._fallback_review(contract, reviewer, "timeout")

        except Exception as e:
            log.warning("peer_review.error", reviewer=reviewer,
                        reviewed=contract.agent_id, err=str(e)[:80])
            return self._fallback_review(contract, reviewer, str(e)[:80])

    async def _do_review(
        self,
        contract: AgentContract,
        reviewer: str,
    ) -> ReviewResult:
        """Core LLM-based review."""
        from langchain_core.messages import SystemMessage, HumanMessage
        from core.llm_factory import LLMFactory

        user_msg = (
            f"AGENT REVIEWÉ : {contract.agent_id}\n"
            f"TÂCHE : {contract.metadata.get('task', 'non spécifiée')[:200]}\n"
            f"SORTIE (tronquée à 800 chars) :\n{contract.output[:800]}\n\n"
            f"Évalue cette sortie en JSON."
        )
        factory = LLMFactory(self.s)
        resp    = await factory.safe_invoke(
            [SystemMessage(content=_REVIEW_SYSTEM),
             HumanMessage(content=user_msg)],
            role    = "fast",
            timeout = 25.0,
        )

        raw = resp.content if resp else "{}"
        # Extract JSON
        start = raw.find("{")
        end   = raw.rfind("}") + 1
        if start >= 0 and end > start:
            parsed = json.loads(raw[start:end])
        else:
            raise ValueError("No JSON in reviewer response")

        return ReviewResult.from_scores(
            reviewer_id  = reviewer,
            reviewed_id  = contract.agent_id,
            contract_id  = contract.id,
            quality      = float(parsed.get("quality",      7.0)),
            consistency  = float(parsed.get("consistency",  7.0)),
            risk         = float(parsed.get("risk",         2.0)),
            completeness = float(parsed.get("completeness", 7.0)),
            feedback     = str(parsed.get("feedback", ""))[:200],
            pass_score   = PEER_REVIEW_PASS_SCORE,
        )

    def _fallback_review(
        self,
        contract: AgentContract,
        reviewer: str,
        reason:   str,
    ) -> ReviewResult:
        """Fallback review when LLM is unavailable — approves by default."""
        return ReviewResult.from_scores(
            reviewer_id  = reviewer,
            reviewed_id  = contract.agent_id,
            contract_id  = contract.id,
            quality      = 7.0,
            consistency  = 7.0,
            risk         = 2.0,
            completeness = 7.0,
            feedback     = f"[fallback: {reason}] auto-approved",
            pass_score   = PEER_REVIEW_PASS_SCORE,
        )

    async def review_if_needed(
        self,
        contract: AgentContract,
    ) -> ReviewResult | None:
        """
        Convenience method: reviews only if contract.needs_review is True.
        Returns None if review was not needed.
        Designed for fire-and-forget use in parallel_executor.
        """
        if not contract.needs_review:
            return None
        if contract.agent_id not in REVIEWER_FOR:
            return None
        return await self.review(contract)
