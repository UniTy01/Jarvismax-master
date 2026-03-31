"""
JARVIS MAX v3 — Repo Map Generator
À la manière de SWE-agent / Aider, condense l'arborescence d'un dossier
pour donner du contexte à l'agent sans inonder la fenêtre de contexte.
(Plus tard, peut-être enrichi via tree-sitter pour extraire les signatures de fonctions).
"""
import os
from pathlib import Path

def get_repo_map(workspace_path: str | Path, max_depth: int = 4, ignore_dirs=None) -> str:
    """Génère un arbre textuel simple du projet."""
    if ignore_dirs is None:
        ignore_dirs = {'.git', '__pycache__', 'node_modules', 'venv', '.env', '.idea', 'dist', 'build'}

    base_path = Path(workspace_path).absolute()
    if not base_path.exists():
        return f"Erreur: le dossier {base_path} n'existe pas."

    lines = []
    
    def walk(current_path: Path, prefix: str = "", depth: int = 0):
        if depth > max_depth:
            return
            
        try:
            entries = sorted(list(current_path.iterdir()), key=lambda e: (e.is_file(), e.name.lower()))
        except PermissionError:
            return

        for i, entry in enumerate(entries):
            if entry.name in ignore_dirs or entry.name.startswith('.'):
                continue
                
            is_last = (i == len(entries) - 1)
            connector = "└── " if is_last else "├── "
            
            if entry.is_dir():
                lines.append(f"{prefix}{connector}{entry.name}/")
                new_prefix = prefix + ("    " if is_last else "│   ")
                walk(entry, new_prefix, depth + 1)
            else:
                # Filtrage optionnel de certains fichiers binaire ou lourds
                if entry.suffix not in ['.pyc', '.png', '.jpg', '.mp4', '.ttf', '.woff']:
                    lines.append(f"{prefix}{connector}{entry.name}")

    lines.append(f"📁 {base_path.name}/")
    walk(base_path)
    
    result = "\n".join(lines)
    # Protection limite token
    if len(result) > 10000:
        return result[:9500] + "\n... [TRONQUÉ] L'arborescence est trop grande."
    return result
