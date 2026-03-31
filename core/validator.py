"""
JARVIS MAX v3 — Auto Validator
Système de vérification post-mission pour assurer la qualité du code produit.
"""
import structlog
from typing import Any

log = structlog.get_logger()

class MissionValidator:
    """Exécute des tests automatiques après que l'agent a dit 'avoir fini'."""
    
    def __init__(self, terminal: Any):
        self.terminal = terminal

    async def validate(self) -> tuple[bool, str]:
        """Tente de valider le projet (détection auto des tests)."""
        log.info("auto_validation_starting")
        
        # 1. Détecter le type de projet
        exit_code, files = await self.terminal.execute("ls -F")
        
        test_cmd = None
        if "package.json" in files:
            test_cmd = "npm test"
        elif "pytest.ini" in files or "tests/" in files or "test_" in files:
            test_cmd = "python -m pytest"
        
        if not test_cmd:
            return True, "Aucun test automatique détecté. Validation manuelle requise."

        log.info("executing_validation_command", cmd=test_cmd)
        exit_code, output = await self.terminal.execute(test_cmd)
        
        if exit_code == 0:
            return True, f"Validation réussie avec '{test_cmd}'.\n{output[:500]}"
        else:
            return False, f"Échec de la validation avec '{test_cmd}'.\nErreur :\n{output[:1000]}"
