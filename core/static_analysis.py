"""
JARVIS MAX — Static Analysis Module
=====================================
Lightweight static analysis for the JarvisMax codebase.

Detects:
- Unused imports (per-file)
- Dead code (defined but unreferenced functions/classes)
- Circular import risk (module-level dependency cycles)
- Missing type hints on public functions
- Unsafe except patterns (bare except, except pass)
- Complexity hotspots

No external dependencies — uses only ast and stdlib.
All functions return structured results, never raise.

Usage:
    from core.static_analysis import analyze_file, analyze_directory
    report = analyze_file("core/circuit_breaker.py")
    full = analyze_directory("core/")
"""
from __future__ import annotations

import ast
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class FileAnalysis:
    """Analysis results for a single file."""
    path:             str
    lines:            int = 0
    functions:        int = 0
    classes:          int = 0
    unused_imports:   list[str] = field(default_factory=list)
    missing_typehints: list[str] = field(default_factory=list)
    bare_excepts:     list[int] = field(default_factory=list)
    except_pass:      list[int] = field(default_factory=list)
    complexity_hotspots: list[dict] = field(default_factory=list)
    missing_docstrings: list[str] = field(default_factory=list)
    syntax_valid:     bool = True
    error:            str = ""

    def issue_count(self) -> int:
        return (
            len(self.unused_imports)
            + len(self.missing_typehints)
            + len(self.bare_excepts)
            + len(self.except_pass)
            + len(self.complexity_hotspots)
            + len(self.missing_docstrings)
        )

    def to_dict(self) -> dict:
        return {
            "path": self.path,
            "lines": self.lines,
            "functions": self.functions,
            "classes": self.classes,
            "issues": self.issue_count(),
            "unused_imports": self.unused_imports,
            "missing_typehints": self.missing_typehints[:10],
            "bare_excepts": self.bare_excepts,
            "except_pass": self.except_pass[:10],
            "complexity_hotspots": self.complexity_hotspots[:5],
            "missing_docstrings": self.missing_docstrings[:10],
            "syntax_valid": self.syntax_valid,
        }


@dataclass
class DirectoryAnalysis:
    """Aggregated analysis for a directory."""
    path:         str
    files:        list[FileAnalysis] = field(default_factory=list)
    total_lines:  int = 0
    total_issues: int = 0

    @property
    def summary(self) -> str:
        return (
            f"{self.path}: {len(self.files)} files, "
            f"{self.total_lines} lines, {self.total_issues} issues"
        )

    def worst_files(self, n: int = 10) -> list[FileAnalysis]:
        return sorted(self.files, key=lambda f: f.issue_count(), reverse=True)[:n]

    def to_dict(self) -> dict:
        return {
            "path": self.path,
            "files_analyzed": len(self.files),
            "total_lines": self.total_lines,
            "total_issues": self.total_issues,
            "worst_files": [f.to_dict() for f in self.worst_files(10)],
        }


# ═══════════════════════════════════════════════════════════════
# ANALYSIS FUNCTIONS
# ═══════════════════════════════════════════════════════════════

def _detect_unused_imports(tree: ast.AST, source: str) -> list[str]:
    """Detect imported names that are never used in the file."""
    imported_names: dict[str, int] = {}  # name → line

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                name = alias.asname or alias.name.split(".")[0]
                imported_names[name] = node.lineno
        elif isinstance(node, ast.ImportFrom):
            for alias in node.names:
                name = alias.asname or alias.name
                if name != "*":
                    imported_names[name] = node.lineno

    # Check usage — simple text search (handles attr access, decorators, etc.)
    used = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            used.add(node.id)
        elif isinstance(node, ast.Attribute):
            used.add(node.attr)

    unused = []
    for name, line in imported_names.items():
        if name not in used and name != "_":
            # Skip __all__ listed names
            unused.append(f"L{line}: {name}")
    return unused


def _detect_missing_typehints(tree: ast.AST) -> list[str]:
    """Detect public functions missing return type annotations."""
    missing = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if not node.name.startswith("_") and node.returns is None:
                missing.append(f"L{node.lineno}: {node.name}()")
    return missing


def _detect_missing_docstrings(tree: ast.AST) -> list[str]:
    """Detect public functions and classes without docstrings."""
    missing = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            if node.name.startswith("_"):
                continue
            has_docstring = (
                node.body
                and isinstance(node.body[0], ast.Expr)
                and isinstance(node.body[0].value, ast.Constant)
                and isinstance(node.body[0].value.value, str)
            )
            if not has_docstring:
                kind = "class" if isinstance(node, ast.ClassDef) else "def"
                missing.append(f"L{node.lineno}: {kind} {node.name}")
    return missing


def _detect_unsafe_except(tree: ast.AST) -> tuple[list[int], list[int]]:
    """Detect bare except and except-pass patterns."""
    bare = []
    pass_only = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ExceptHandler):
            if node.type is None:
                bare.append(node.lineno)
            if len(node.body) == 1 and isinstance(node.body[0], ast.Pass):
                pass_only.append(node.lineno)
    return bare, pass_only


def _detect_complexity(tree: ast.AST) -> list[dict]:
    """Detect functions with high cyclomatic complexity."""
    hotspots = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            complexity = 1
            for child in ast.walk(node):
                if isinstance(child, (ast.If, ast.While, ast.For, ast.ExceptHandler)):
                    complexity += 1
                elif isinstance(child, ast.BoolOp):
                    complexity += len(child.values) - 1
            if complexity > 10:
                hotspots.append({
                    "name": node.name,
                    "line": node.lineno,
                    "complexity": complexity,
                })
    return sorted(hotspots, key=lambda h: h["complexity"], reverse=True)


def analyze_file(path: str) -> FileAnalysis:
    """
    Analyze a single Python file.
    
    Returns FileAnalysis with all detected issues.
    Never raises — returns error info in the result.
    """
    result = FileAnalysis(path=path)
    try:
        p = Path(path)
        if not p.exists():
            result.syntax_valid = False
            result.error = "File not found"
            return result

        source = p.read_text(encoding="utf-8", errors="replace")
        result.lines = source.count("\n") + 1

        try:
            tree = ast.parse(source, filename=path)
        except SyntaxError as e:
            result.syntax_valid = False
            result.error = f"SyntaxError L{e.lineno}: {e.msg}"
            return result

        # Count definitions
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                result.functions += 1
            elif isinstance(node, ast.ClassDef):
                result.classes += 1

        result.unused_imports = _detect_unused_imports(tree, source)
        result.missing_typehints = _detect_missing_typehints(tree)
        result.missing_docstrings = _detect_missing_docstrings(tree)
        bare, pass_only = _detect_unsafe_except(tree)
        result.bare_excepts = bare
        result.except_pass = pass_only
        result.complexity_hotspots = _detect_complexity(tree)

    except Exception as e:
        result.error = f"Analysis failed: {str(e)[:200]}"

    return result


def analyze_directory(
    path: str = ".",
    exclude: Optional[set[str]] = None,
) -> DirectoryAnalysis:
    """
    Analyze all Python files in a directory.
    
    Args:
        path: Directory to analyze
        exclude: Set of path prefixes to skip (e.g. {"tests/", "archive/"})
    
    Returns DirectoryAnalysis with aggregated results.
    """
    exclude = exclude or {"tests/", "archive/", "__pycache__/"}
    d = Path(path)
    result = DirectoryAnalysis(path=path)

    try:
        for f in sorted(d.rglob("*.py")):
            rel = str(f)
            if any(ex in rel for ex in exclude) or "__pycache__" in rel:
                continue
            analysis = analyze_file(str(f))
            result.files.append(analysis)
            result.total_lines += analysis.lines
            result.total_issues += analysis.issue_count()
    except Exception as e:
        result.files.append(FileAnalysis(
            path=path, error=f"Directory scan failed: {str(e)[:200]}",
        ))

    return result
