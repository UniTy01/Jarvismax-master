"""
JARVIS MAX — RecoveryAgent
Gère le rollback et la reprise contrôlée après erreur.

Déclenché par l'orchestrateur après DebugAgent si :
- is_auto_fixable=False → propose rollback ou escalation
- Backup disponible → restore automatique si nécessaire
- Mission partiellement exécutée → reprise depuis le dernier succès
"""
from __future__ import annotations

import json
import shutil
import time
from pathlib import Path

import structlog

from agents.crew import BaseAgent
from core.state import JarvisSession

log = structlog.get_logger()

_BACKUP_DIR = Path("workspace/.backups")


class RecoveryAgent(BaseAgent):
    name     = "recovery-agent"
    role     = "advisor"
    timeout_s= 60

    _SYSTEM = """Tu es RecoveryAgent, expert en reprise après erreur pour JarvisMax.

MISSION : Analyser la situation après une erreur et proposer ou appliquer une stratégie de recovery.

Tu connais ces stratégies :
1. ROLLBACK : restaurer un fichier depuis son backup (.bak)
2. SKIP : sauter l'agent défaillant et continuer avec les autres
3. PARTIAL_RETRY : réexécuter uniquement les tâches qui ont échoué
4. ESCALATE : signaler à l'utilisateur pour intervention manuelle
5. ABORT : annuler proprement la mission sans laisser d'état corrompu

FORMAT DE RÉPONSE (JSON strict) :
{
  "strategy": "SKIP",
  "reason": "L'agent scout-research n'est pas critique — les autres peuvent avancer",
  "actions": [
    {"type": "skip_agent", "agent": "scout-research"},
    {"type": "resume_mission", "from_agent": "map-planner"}
  ],
  "risk": "low",
  "impact": "Analyse moins complète mais mission continue"
}

STRATÉGIE PAR DÉFAUT si incertain : SKIP (moins destructif).
ROLLBACK uniquement si un fichier a été modifié et qu'un backup existe.
ABORT uniquement si la mission est corrompue de façon irréparable.
"""

    def system_prompt(self) -> str:
        return self._SYSTEM

    def user_message(self, session: JarvisSession) -> str:
        debug_result  = session.metadata.get("debug_result", {})
        failed_agent  = session.metadata.get("debug_target_error", {}).get("agent", "inconnu")
        auto_fixable  = session.metadata.get("debug_auto_fixable", False)
        backups       = self._list_recent_backups(5)

        completed_agents = [
            name for name, out in session.outputs.items() if out.success
        ]
        failed_agents = [
            name for name, out in session.outputs.items() if not out.success
        ]

        return (
            f"Mission : {session.mission_summary or session.user_input}\n"
            f"Agent en échec : {failed_agent}\n"
            f"Agents réussis : {', '.join(completed_agents) or 'aucun'}\n"
            f"Agents échoués : {', '.join(failed_agents) or 'aucun'}\n"
            f"Auto-fixable par DebugAgent : {auto_fixable}\n"
            f"\nAnalyse DebugAgent :\n{json.dumps(debug_result, ensure_ascii=False, indent=2)[:800]}\n"
            + (f"\nBackups disponibles :\n{chr(10).join(backups)}" if backups else "\nPas de backup récent.")
        )

    async def run(self, session: JarvisSession) -> str:
        t0 = time.monotonic()
        log.info("recovery_agent_start", sid=session.session_id)

        try:
            from core.llm_factory import LLMFactory
            from langchain_core.messages import SystemMessage, HumanMessage
            factory  = LLMFactory(self.s)
            messages = [
                SystemMessage(content=self.system_prompt()),
                HumanMessage(content=self.user_message(session)),
            ]
            resp = await factory.safe_invoke(messages, role=self.role, timeout=float(self.timeout_s))
            raw  = (resp.content if resp else "").strip()

            try:
                if raw.startswith("```"):
                    raw = raw.split("```")[1].lstrip("json").strip()
                data = json.loads(raw)
            except Exception:
                data = {
                    "strategy": "ESCALATE",
                    "reason":   "Analyse non concluante",
                    "actions":  [],
                    "risk":     "unknown",
                    "impact":   "Intervention manuelle requise",
                }

            # Appliquer les actions auto si elles sont de type "rollback_file"
            applied = []
            for action in data.get("actions", []):
                if action.get("type") == "rollback_file":
                    result = self._apply_rollback(action)
                    applied.append(result)

            ms = int((time.monotonic() - t0) * 1000)

            strategy = data.get("strategy", "ESCALATE")
            summary  = (
                f"[RecoveryAgent] strategy={strategy} "
                f"risk={data.get('risk', '?')} "
                f"rollbacks_applied={len(applied)}"
            )

            # Stocker pour l'orchestrateur
            session.metadata["recovery_result"]   = data
            session.metadata["recovery_strategy"] = strategy
            session.metadata["recovery_applied"]  = applied

            session.set_output(self.name, summary, success=True, ms=ms)

            log.info(
                "recovery_agent_done",
                strategy=strategy,
                rollbacks=len(applied),
                ms=ms,
                sid=session.session_id,
            )
            return summary

        except Exception as e:
            ms = int((time.monotonic() - t0) * 1000)
            log.error("recovery_agent_error", err=str(e)[:100], sid=session.session_id)
            session.set_output(self.name, "", success=False, error=str(e))
            return ""

    def _list_recent_backups(self, n: int = 5) -> list[str]:
        """Liste les N backups les plus récents."""
        try:
            if not _BACKUP_DIR.exists():
                return []
            baks = sorted(
                _BACKUP_DIR.glob("*.bak"),
                key=lambda p: p.stat().st_mtime,
                reverse=True,
            )[:n]
            return [p.name for p in baks]
        except Exception:
            return []

    # Répertoires autorisés pour les rollbacks — tout autre chemin est rejeté
    _ALLOWED_ROLLBACK_ROOTS = (
        Path("workspace"),
        Path("self_improve"),
        Path("core"),
        Path("agents"),
        Path("executor"),
        Path("learning"),
        Path("memory"),
    )

    def _apply_rollback(self, action: dict) -> dict:
        """
        Applique un rollback depuis backup.

        Sécurité :
        - Le backup_file NE PEUT PAS contenir de séparateurs de chemin (path traversal).
        - Le target DOIT être dans un sous-répertoire autorisé du projet.
        - Les chemins absolus hors projet sont refusés.
        """
        backup_name = action.get("backup_file", "")
        target      = action.get("target", "")

        if not backup_name or not target:
            return {"ok": False, "error": "backup_file ou target manquant"}

        # Sécurité 1 : backup_name ne doit pas contenir de chemin (ni / ni ..)
        if "/" in backup_name or "\\" in backup_name or ".." in backup_name:
            log.warning("recovery_rollback_blocked_path_traversal",
                        backup=backup_name[:80])
            return {"ok": False, "error": "backup_file contient un chemin interdit"}

        # Sécurité 2 : target doit être dans un répertoire autorisé
        dst = Path(target)
        try:
            # Résoudre sans accès disque pour détecter les .. avant vérification
            dst_resolved = dst.resolve()
            project_root = Path(".").resolve()
            # Vérifier que la destination est dans le projet
            dst_resolved.relative_to(project_root)  # lève ValueError si hors projet
        except ValueError:
            log.warning("recovery_rollback_blocked_outside_project",
                        target=target[:120])
            return {"ok": False, "error": f"target hors du projet : {target}"}

        # Vérifier que le préfixe est dans les répertoires autorisés
        allowed = any(
            str(dst).startswith(str(r)) or str(dst_resolved).startswith(
                str(Path(".").resolve() / r)
            )
            for r in self._ALLOWED_ROLLBACK_ROOTS
        )
        if not allowed:
            log.warning("recovery_rollback_blocked_disallowed_root",
                        target=target[:120])
            return {"ok": False, "error": f"target dans un répertoire non autorisé : {target}"}

        src = _BACKUP_DIR / backup_name
        if not src.exists():
            return {"ok": False, "error": f"Backup introuvable : {backup_name}"}

        try:
            shutil.copy2(str(src), str(dst))
            log.info("recovery_rollback_applied", backup=backup_name, target=target)
            return {"ok": True, "backup": backup_name, "target": target}
        except Exception as e:
            return {"ok": False, "error": str(e)[:100]}
