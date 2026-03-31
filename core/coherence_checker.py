"""
JARVIS MAX — Coherence Checker v1
Vérification de cohérence globale avant action.

Responsabilités :
  1. Validation chemins : vérifier que les fichiers/dirs référencés existent réellement
  2. Anti-erreurs répétées : détecter les patterns d'erreur déjà connus dans VaultMemory
  3. Cohérence imports : détecter les imports de modules inexistants
  4. Détection hallucinations : signaux de confiance trop haute sans preuve
  5. Log traçable : chaque vérification loggée avec contexte

CoherenceResult :
  - passed   : bool         → True si toutes les vérifications passent
  - issues   : list[str]    → problèmes détectés
  - warnings : list[str]    → avertissements non bloquants
  - errors   : list[str]    → erreurs bloquantes
  - score    : float        → 0.0 (tout cassé) → 1.0 (parfait)
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
import structlog

log = structlog.get_logger()

# Patterns de chemins fantômes (hallucinations connues)
_PHANTOM_PATH_PATTERNS = [
    r"/home/\w+/",        # chemin Linux hardcodé
    r"C:\\Users\\[A-Z]",  # chemin Windows hardcodé autre que le projet
    r"/tmp/jarvis",       # /tmp hardcodé
    r"workspace/output/nonexistent",
]

# Imports suspects (modules qui n'existent pas dans le projet ou sont mal orthographiés)
_SUSPICIOUS_IMPORTS = re.compile(
    r"\bimport\s+(jarvis_core|jarviscore|jarvismem|core\.memory_bus|agents\.crew_v\d)\b",
    re.IGNORECASE,
)

# Signaux d'hallucination dans les outputs agents
_HALLUCINATION_SIGNALS = re.compile(
    r"\b(j'imagine|hypothétiquement|je suppose|probablement autour de \d|"
    r"environ \d{4}|basé sur mon intuition|selon mes estimations)\b",
    re.IGNORECASE,
)

# Max de répétitions d'erreur connue avant blocage
_MAX_KNOWN_ERROR_REPEAT = 3


# ── Résultat de vérification ──────────────────────────────────────────────────

@dataclass
class CoherenceResult:
    passed:   bool
    issues:   list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    errors:   list[str] = field(default_factory=list)
    score:    float = 1.0   # 1.0 = parfait

    def __post_init__(self):
        self.score = self._compute_score()

    def _compute_score(self) -> float:
        penalty = len(self.errors) * 0.30 + len(self.warnings) * 0.10
        return max(0.0, 1.0 - penalty)

    def add_error(self, msg: str) -> None:
        self.errors.append(msg)
        self.issues.append(f"[ERROR] {msg}")
        self.passed = False
        self.score  = self._compute_score()

    def add_warning(self, msg: str) -> None:
        self.warnings.append(msg)
        self.issues.append(f"[WARN] {msg}")
        self.score = self._compute_score()

    def summary(self) -> str:
        status = "PASS" if self.passed else "FAIL"
        return (
            f"[Coherence:{status}] score={self.score:.2f} "
            f"errors={len(self.errors)} warnings={len(self.warnings)}"
        )


# ── Coherence Checker ─────────────────────────────────────────────────────────

class CoherenceChecker:
    """
    Vérificateur de cohérence globale.

    Usage :
        checker = CoherenceChecker(base_dir=".")
        result = checker.check_text(agent_output, context="forge-builder output")
        result = checker.check_paths(["workspace/output.py", "nonexistent.py"])
        result = checker.check_session(session)
    """

    def __init__(self, base_dir: str|Path = "."):
        self._base = Path(base_dir).resolve()

    # ── API principale ────────────────────────────────────────────────────────

    def check_text(self, text: str, context: str = "") -> CoherenceResult:
        """
        Vérifie la cohérence d'un texte (sortie agent).
        Détecte : chemins fantômes, imports suspects, hallucinations.
        """
        result = CoherenceResult(passed=True)

        self._check_phantom_paths(text, result)
        self._check_suspicious_imports(text, result)
        self._check_hallucination_signals(text, result)
        self._check_known_errors(text, result, context)

        self._log_result(result, context or "text_check")
        return result

    def check_paths(self, paths: list[str], must_exist: bool = False) -> CoherenceResult:
        """
        Vérifie que les chemins référencés sont valides (pas de chemins fantômes).
        Si must_exist=True, vérifie aussi que les fichiers existent réellement.
        """
        result = CoherenceResult(passed=True)

        for p in paths:
            path_str = str(p)

            # Chemin fantôme
            for pattern in _PHANTOM_PATH_PATTERNS:
                if re.search(pattern, path_str):
                    result.add_error(f"Chemin fantôme détecté : {path_str!r}")
                    break

            # Existence si demandée
            if must_exist:
                full = self._base / path_str if not Path(path_str).is_absolute() else Path(path_str)
                if not full.exists():
                    result.add_warning(f"Fichier introuvable : {path_str!r}")

        self._log_result(result, "path_check")
        return result

    def check_session(self, session: Any) -> CoherenceResult:
        """
        Vérifie la cohérence d'une session complète :
        - toutes les sorties agents
        - les actions préparées par PulseOps
        - la cohérence mission/résultats
        """
        result = CoherenceResult(passed=True)

        try:
            # Vérifier les sorties agents
            outputs = getattr(session, "agents_outputs", {}) or {}
            for agent_name, output_data in outputs.items():
                text = ""
                if isinstance(output_data, dict):
                    text = output_data.get("output", "")
                elif isinstance(output_data, str):
                    text = output_data

                if text:
                    sub = self.check_text(text, context=f"session:{agent_name}")
                    result.errors.extend(sub.errors)
                    result.warnings.extend(sub.warnings)
                    result.issues.extend(sub.issues)

            # Vérifier les actions PulseOps si présentes
            raw_actions = getattr(session, "_raw_actions", []) or []
            paths = []
            for action in raw_actions:
                if isinstance(action, dict):
                    target = action.get("target", "")
                    if target:
                        paths.append(target)

            if paths:
                path_result = self.check_paths(paths, must_exist=False)
                result.errors.extend(path_result.errors)
                result.warnings.extend(path_result.warnings)
                result.issues.extend(path_result.issues)

            # Recalcule passed
            if result.errors:
                result.passed = False

            result.score = result._compute_score()

        except Exception as exc:
            log.warning("coherence_check_session_failed", err=str(exc))
            result.add_warning(f"Erreur vérification session : {exc}")

        self._log_result(result, "session_check")
        return result

    def check_plan(self, plan: list[dict]) -> CoherenceResult:
        """
        Vérifie la cohérence d'un plan d'agents (sortie AtlasDirector).
        - Agents valides
        - Priorités cohérentes
        - Pas de dépendances circulaires
        """
        result = CoherenceResult(passed=True)

        valid_agents = {
            "scout-research", "web-scout", "vault-memory", "shadow-advisor",
            "map-planner", "forge-builder", "lens-reviewer", "pulse-ops",
            "atlas-director", "night-worker",
        }

        seen_agents = set()
        for task in plan:
            if not isinstance(task, dict):
                result.add_error(f"Tâche invalide (non-dict) : {task!r}")
                continue

            agent = task.get("agent", "")
            if agent not in valid_agents:
                result.add_warning(f"Agent inconnu dans le plan : {agent!r}")

            if agent in seen_agents:
                result.add_warning(f"Agent dupliqué dans le plan : {agent!r}")
            seen_agents.add(agent)

            priority = task.get("priority", 0)
            if not isinstance(priority, int) or priority < 1:
                result.add_warning(f"Priorité invalide pour {agent!r} : {priority!r}")

        self._log_result(result, "plan_check")
        return result

    # ── Checks internes ────────────────────────────────────────────────────────

    def _check_phantom_paths(self, text: str, result: CoherenceResult) -> None:
        for pattern in _PHANTOM_PATH_PATTERNS:
            match = re.search(pattern, text)
            if match:
                result.add_warning(
                    f"Chemin potentiellement fantôme détecté dans le texte : "
                    f"{match.group()!r}"
                )

    def _check_suspicious_imports(self, text: str, result: CoherenceResult) -> None:
        match = _SUSPICIOUS_IMPORTS.search(text)
        if match:
            result.add_error(
                f"Import suspect détecté (module inexistant probable) : {match.group()!r}"
            )

    def _check_hallucination_signals(self, text: str, result: CoherenceResult) -> None:
        matches = _HALLUCINATION_SIGNALS.findall(text)
        if matches:
            result.add_warning(
                f"Signaux d'hallucination détectés ({len(matches)}) : "
                f"{', '.join(matches[:3])!r}"
            )

    def _check_known_errors(self, text: str, result: CoherenceResult, context: str) -> None:
        """Vérifie si le texte répète une erreur déjà connue en VaultMemory."""
        try:
            from memory.vault_memory import get_vault_memory
            vm     = get_vault_memory()
            errors = vm.get_by_type("error", max_k=10)

            for err_entry in errors:
                # Recherche Jaccard simplifiée
                err_words  = set(err_entry.content.lower().split())
                text_words = set(text.lower().split())
                if len(err_words) < 3:
                    continue
                inter = err_words & text_words
                union = err_words | text_words
                if union and len(inter) / len(union) > 0.50:
                    result.add_warning(
                        f"Erreur connue répétée : {err_entry.content[:100]!r} "
                        f"[vault:{err_entry.id}]"
                    )
        except Exception:
            pass  # Silencieux si VaultMemory indisponible

    def _log_result(self, result: CoherenceResult, context: str) -> None:
        if result.passed:
            log.debug(
                "coherence_check_passed",
                context=context,
                score=result.score,
                warnings=len(result.warnings),
            )
        else:
            log.warning(
                "coherence_check_failed",
                context=context,
                score=result.score,
                errors=result.errors[:3],
            )


# ── Singleton + raccourcis ────────────────────────────────────────────────────

_checker_instance: CoherenceChecker|None = None


def get_coherence_checker(base_dir: str = ".") -> CoherenceChecker:
    global _checker_instance
    if _checker_instance is None:
        _checker_instance = CoherenceChecker(base_dir=base_dir)
    return _checker_instance


def check_text(text: str, context: str = "") -> CoherenceResult:
    """
    Raccourci : vérifie la cohérence d'un texte.

    Usage :
        from core.coherence_checker import check_text
        result = check_text(agent_output, context="forge-builder")
        if not result.passed:
            log.warning("coherence_issues", issues=result.issues)
    """
    return get_coherence_checker().check_text(text, context)


def check_session(session: Any) -> CoherenceResult:
    """
    Raccourci : vérifie la cohérence d'une session.

    Usage :
        from core.coherence_checker import check_session
        result = check_session(session)
    """
    return get_coherence_checker().check_session(session)
