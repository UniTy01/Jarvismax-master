"""
JARVIS MAX — MissionExecutionResult (Phase 4)
==============================================
Résultat structuré de l'exécution complète d'une mission.
Reçu par MetaOrchestrator à la fin de chaque cycle d'exécution.

Distinct de executor.task_model.ExecutionResult (niveau tâche individuelle).
MissionExecutionResult = agrégation de tous les agents + état final mission.

Taxonomy des failures :
    TRANSIENT   — timeout, rate limit, réseau → retryable
    STRUCTURAL  — schema invalide, contrat manquant → non retryable
    LOGIC       — raisonnement erroné, délégation invalide → debug requis
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


# ─────────────────────────────────────────────────────────────────────────────
# Status
# ─────────────────────────────────────────────────────────────────────────────

class MissionExecStatus(str, Enum):
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED  = "failed"


# ─────────────────────────────────────────────────────────────────────────────
# Failure classification
# ─────────────────────────────────────────────────────────────────────────────

class FailureClass(str, Enum):
    """
    Taxonomie des échecs d'exécution.

    TRANSIENT  — problème temporaire, retry possible
    STRUCTURAL — problème de schéma/contrat, code change requis
    LOGIC      — problème de raisonnement agent, investigation requise
    """
    TRANSIENT  = "transient"
    STRUCTURAL = "structural"
    LOGIC      = "logic"
    UNKNOWN    = "unknown"


# Mots-clés pour classification automatique
_TRANSIENT_KEYWORDS = (
    "timeout", "rate limit", "503", "502", "429", "connection",
    "network", "temporary", "unavailable", "overloaded", "reset",
    "retry", "backoff",
)
_STRUCTURAL_KEYWORDS = (
    "missing field", "invalid schema", "validation", "missing key",
    "keyerror", "typeerror", "attributeerror", "none type",
    "invalid contract", "schema",
)
_LOGIC_KEYWORDS = (
    "hallucin", "wrong agent", "invalid delegation", "loop detected",
    "repeated output", "bad reasoning", "circular", "infinite",
)


def classify_failure(error: str | Exception) -> FailureClass:
    """
    Classifie automatiquement un échec selon son message.

    Priority: TRANSIENT > STRUCTURAL > LOGIC > UNKNOWN
    """
    msg = str(error).lower()
    if any(k in msg for k in _TRANSIENT_KEYWORDS):
        return FailureClass.TRANSIENT
    if any(k in msg for k in _STRUCTURAL_KEYWORDS):
        return FailureClass.STRUCTURAL
    if any(k in msg for k in _LOGIC_KEYWORDS):
        return FailureClass.LOGIC
    # Inspect exception type
    if isinstance(error, Exception):
        name = type(error).__name__.lower()
        if "timeout" in name or "connection" in name:
            return FailureClass.TRANSIENT
        if "value" in name or "type" in name or "key" in name or "attribute" in name:
            return FailureClass.STRUCTURAL
    return FailureClass.UNKNOWN


@dataclass
class FailureRecord:
    """Enregistrement d'un échec individuel dans une mission."""
    agent_id:       str
    error:          str
    failure_class:  FailureClass
    retryable:      bool
    retry_count:    int   = 0
    timestamp:      float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "agent_id":      self.agent_id,
            "error":         self.error[:200],
            "failure_class": self.failure_class.value,
            "retryable":     self.retryable,
            "retry_count":   self.retry_count,
            "timestamp":     self.timestamp,
        }


# ─────────────────────────────────────────────────────────────────────────────
# MissionExecutionResult
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class MissionExecutionResult:
    """
    Résultat d'exécution mission-level retourné à MetaOrchestrator.

    Agrège tous les résultats agents + état final + métriques.

    Règle de statut :
        SUCCESS  → agents_ok / agents_total >= 0.8
        PARTIAL  → 0.2 <= ratio < 0.8
        FAILED   → ratio < 0.2 OU erreur critique
    """
    mission_id:       str
    status:           MissionExecStatus  = MissionExecStatus.SUCCESS
    final_output:     str                = ""

    # Chain
    agent_chain:      list[str]          = field(default_factory=list)
    agents_ok:        int                = 0
    agents_total:     int                = 0

    # Errors / warnings
    errors:           list[FailureRecord] = field(default_factory=list)
    warnings:         list[str]           = field(default_factory=list)

    # Retry tracking
    retry_count:      int                = 0
    retry_details:    list[dict]         = field(default_factory=list)

    # Memory
    memory_updates:   list[str]          = field(default_factory=list)

    # Quality
    confidence_score: float              = 1.0

    # Loop guard
    loop_detected:    bool               = False
    loop_detail:      str                = ""

    # Timing
    duration_ms:      int                = 0
    started_at:       float              = field(default_factory=time.time)
    finished_at:      float              = 0.0

    # Auto
    id:               str                = field(default_factory=lambda: str(uuid.uuid4())[:10])

    # ── Computed ──────────────────────────────────────────────────────────────

    @property
    def success_rate(self) -> float:
        if self.agents_total == 0:
            return 1.0
        return round(self.agents_ok / self.agents_total, 3)

    @property
    def has_critical_failure(self) -> bool:
        return any(
            f.failure_class == FailureClass.STRUCTURAL
            for f in self.errors
        )

    def finish(self, final_output: str = "") -> "MissionExecutionResult":
        """Mark the result as finished and compute final status."""
        self.finished_at = time.time()
        self.duration_ms = max(1, int((self.finished_at - self.started_at) * 1000))
        if final_output:
            self.final_output = final_output

        rate = self.success_rate
        if self.loop_detected or self.has_critical_failure:
            self.status = MissionExecStatus.FAILED
        elif rate >= 0.8:
            self.status = MissionExecStatus.SUCCESS
        elif rate >= 0.2:
            self.status = MissionExecStatus.PARTIAL
        else:
            self.status = MissionExecStatus.FAILED

        return self

    def add_failure(
        self,
        agent_id:    str,
        error:       str | Exception,
        retry_count: int = 0,
    ) -> FailureRecord:
        """Add a classified failure record."""
        fc      = classify_failure(error)
        retryable = fc == FailureClass.TRANSIENT
        rec = FailureRecord(
            agent_id      = agent_id,
            error         = str(error)[:300],
            failure_class = fc,
            retryable     = retryable,
            retry_count   = retry_count,
        )
        self.errors.append(rec)
        return rec

    def add_warning(self, msg: str) -> None:
        self.warnings.append(msg[:200])

    def to_dict(self) -> dict:
        return {
            "id":             self.id,
            "mission_id":     self.mission_id,
            "status":         self.status.value,
            "final_output":   self.final_output[:500],
            "agent_chain":    self.agent_chain,
            "agents_ok":      self.agents_ok,
            "agents_total":   self.agents_total,
            "success_rate":   self.success_rate,
            "errors":         [e.to_dict() for e in self.errors],
            "warnings":       self.warnings,
            "retry_count":    self.retry_count,
            "memory_updates": self.memory_updates,
            "confidence_score": round(self.confidence_score, 3),
            "loop_detected":  self.loop_detected,
            "loop_detail":    self.loop_detail,
            "duration_ms":    self.duration_ms,
        }

    @classmethod
    def from_jarvis_session(
        cls,
        session: Any,
        mission_id: str = "",
    ) -> "MissionExecutionResult":
        """
        Crée un MissionExecutionResult depuis une JarvisSession existante.
        Pont de compatibilité avec le code legacy.
        """
        mid = mission_id or getattr(session, "session_id", "")
        outputs = getattr(session, "outputs", {})

        ok    = sum(1 for o in outputs.values() if getattr(o, "success", False))
        total = len(outputs)
        chain = list(outputs.keys())

        errors: list[FailureRecord] = []
        for name, out in outputs.items():
            if not getattr(out, "success", True):
                err_msg = getattr(out, "error", "unknown") or "unknown"
                fc  = classify_failure(err_msg)
                errors.append(FailureRecord(
                    agent_id      = name,
                    error         = err_msg[:200],
                    failure_class = fc,
                    retryable     = fc == FailureClass.TRANSIENT,
                ))

        result = cls(
            mission_id    = mid,
            final_output  = getattr(session, "final_report", "") or "",
            agent_chain   = chain,
            agents_ok     = ok,
            agents_total  = total,
            errors        = errors,
        )
        result.finish()
        return result
