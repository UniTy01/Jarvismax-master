"""
JARVIS MAX — Coding Loop Engine

Devin-like coding workflow:
  1. Repo scan → understand codebase structure
  2. Relevant file detection → find files to modify
  3. Bounded modification plan → scoped, safe edits
  4. Code edit → apply changes
  5. Test run → validate
  6. Error interpretation → understand failures
  7. Patch → fix issues
  8. Retest → confirm fix

This module provides the structured loop logic.
Actual LLM calls are delegated to the orchestrator.
"""
from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import structlog

log = structlog.get_logger()


# ── Coding Task Model ─────────────────────────────────────────

@dataclass
class CodingTask:
    """A bounded coding task with clear scope."""
    task_id: str
    description: str
    task_type: str = "bugfix"       # bugfix, refactor, feature, test, document
    target_files: list[str] = field(default_factory=list)
    test_command: str = ""
    max_iterations: int = 5
    created_at: float = field(default_factory=time.time)

    # Execution state
    iteration: int = 0
    status: str = "pending"          # pending, scanning, planning, editing, testing, done, failed
    plan: list[str] = field(default_factory=list)
    edits_applied: list[dict] = field(default_factory=list)
    test_results: list[dict] = field(default_factory=list)
    errors_encountered: list[str] = field(default_factory=list)


@dataclass
class RepoContext:
    """Understanding of the repository structure."""
    root: Path = field(default_factory=lambda: Path("."))
    total_files: int = 0
    python_files: list[str] = field(default_factory=list)
    test_files: list[str] = field(default_factory=list)
    config_files: list[str] = field(default_factory=list)
    recent_changes: list[str] = field(default_factory=list)
    structure_map: dict = field(default_factory=dict)

    def scan(self, root: Path | None = None) -> None:
        """Scan repository structure."""
        if root:
            self.root = root
        try:
            all_files = [
                f for f in self.root.rglob("*")
                if f.is_file()
                and "__pycache__" not in str(f)
                and ".git" not in str(f)
                and "node_modules" not in str(f)
                and ".venv" not in str(f)
            ]
            self.total_files = len(all_files)

            self.python_files = sorted([
                str(f.relative_to(self.root))
                for f in all_files if f.suffix == ".py"
            ])
            self.test_files = sorted([
                f for f in self.python_files
                if "/test" in f or f.startswith("test_") or "/tests/" in f
            ])
            self.config_files = sorted([
                str(f.relative_to(self.root))
                for f in all_files
                if f.name in ("pyproject.toml", "setup.py", "setup.cfg",
                              "requirements.txt", "Dockerfile", "docker-compose.yml",
                              ".env.example", "Makefile")
            ])

            # Build structure map (top-level dirs with file counts)
            dirs: dict[str, int] = {}
            for f in all_files:
                try:
                    rel = f.relative_to(self.root)
                    parts = rel.parts
                    if len(parts) > 1:
                        top_dir = parts[0]
                        dirs[top_dir] = dirs.get(top_dir, 0) + 1
                except ValueError:
                    pass
            self.structure_map = dict(sorted(dirs.items(), key=lambda x: x[1], reverse=True)[:20])

            # Recent changes (by mtime)
            sorted_by_mtime = sorted(all_files, key=lambda f: f.stat().st_mtime, reverse=True)
            self.recent_changes = [
                str(f.relative_to(self.root))
                for f in sorted_by_mtime[:10]
            ]

        except Exception as e:
            log.warning("repo_scan_failed", err=str(e)[:100])


# ── File Relevance Detection ──────────────────────────────────

def find_relevant_files(description: str, repo: RepoContext,
                        max_files: int = 10) -> list[str]:
    """
    Find files most relevant to a coding task description.

    Uses:
    - Keyword matching against file paths
    - Import graph analysis (lightweight)
    - Recent modification recency
    """
    desc_words = set(re.findall(r'\w+', description.lower()))
    scored: list[tuple[str, float]] = []

    for f in repo.python_files:
        score = 0.0
        f_lower = f.lower()
        f_words = set(re.findall(r'\w+', f_lower))

        # Path keyword overlap
        overlap = len(desc_words & f_words)
        score += overlap * 0.3

        # Bonus for test files when task mentions testing
        if any(w in desc_words for w in ("test", "tests", "testing", "validate")):
            if "test" in f_lower:
                score += 0.5

        # Bonus for recent changes
        if f in repo.recent_changes[:5]:
            score += 0.2

        # Penalty for very deep paths
        depth = f.count("/")
        if depth > 4:
            score -= 0.1

        if score > 0:
            scored.append((f, score))

    scored.sort(key=lambda x: x[1], reverse=True)
    return [f for f, _ in scored[:max_files]]


# ── Edit Validation ───────────────────────────────────────────

def validate_edit(file_path: str, old_content: str, new_content: str) -> dict:
    """
    Validate a code edit before applying it.

    Returns dict with: valid, warnings, errors
    """
    result = {"valid": True, "warnings": [], "errors": []}

    if not new_content.strip():
        result["valid"] = False
        result["errors"].append("New content is empty")
        return result

    # Check for syntax errors (Python only)
    if file_path.endswith(".py"):
        try:
            compile(new_content, file_path, "exec")
        except SyntaxError as e:
            result["valid"] = False
            result["errors"].append(f"Syntax error: {e}")
            return result

    # Warn on large changes
    old_lines = old_content.count("\n")
    new_lines = new_content.count("\n")
    if old_lines > 0:
        change_ratio = abs(new_lines - old_lines) / old_lines
        if change_ratio > 0.5:
            result["warnings"].append(
                f"Large change: {old_lines} → {new_lines} lines ({change_ratio:.0%} change)")

    # Warn on removing imports
    old_imports = set(re.findall(r'^(?:from|import)\s+\S+', old_content, re.MULTILINE))
    new_imports = set(re.findall(r'^(?:from|import)\s+\S+', new_content, re.MULTILINE))
    removed_imports = old_imports - new_imports
    if removed_imports:
        result["warnings"].append(f"Removed imports: {removed_imports}")

    # Warn on removing functions/classes
    old_defs = set(re.findall(r'^(?:def|class)\s+(\w+)', old_content, re.MULTILINE))
    new_defs = set(re.findall(r'^(?:def|class)\s+(\w+)', new_content, re.MULTILINE))
    removed_defs = old_defs - new_defs
    if removed_defs:
        result["warnings"].append(f"Removed definitions: {removed_defs}")

    return result


# ── Test Result Parsing ───────────────────────────────────────

@dataclass
class TestResult:
    """Parsed test execution result."""
    passed: int = 0
    failed: int = 0
    errors: int = 0
    skipped: int = 0
    total: int = 0
    output: str = ""
    failure_details: list[str] = field(default_factory=list)
    success: bool = False
    duration_s: float = 0.0

    @property
    def pass_rate(self) -> float:
        return self.passed / self.total if self.total > 0 else 0.0


def parse_test_output(output: str) -> TestResult:
    """
    Parse pytest/unittest output into structured result.

    Handles common pytest output formats.
    """
    result = TestResult(output=output[:5000])

    # pytest summary line: "X passed, Y failed, Z errors in N.NNs"
    summary_match = re.search(
        r'(\d+)\s+passed(?:.*?(\d+)\s+failed)?(?:.*?(\d+)\s+error)?(?:.*?(\d+)\s+skipped)?'
        r'(?:.*?in\s+([\d.]+)s)?',
        output
    )
    if summary_match:
        result.passed = int(summary_match.group(1) or 0)
        result.failed = int(summary_match.group(2) or 0)
        result.errors = int(summary_match.group(3) or 0)
        result.skipped = int(summary_match.group(4) or 0)
        if summary_match.group(5):
            result.duration_s = float(summary_match.group(5))
    else:
        # Try "FAILED" line count
        failed_lines = re.findall(r'^FAILED\s+(.+)', output, re.MULTILINE)
        result.failed = len(failed_lines)
        # Try "PASSED" indicator
        if "passed" in output.lower():
            passed_match = re.search(r'(\d+)\s+passed', output)
            if passed_match:
                result.passed = int(passed_match.group(1))

    result.total = result.passed + result.failed + result.errors
    result.success = result.failed == 0 and result.errors == 0 and result.total > 0

    # Extract failure details
    failure_blocks = re.findall(
        r'(?:FAILED|ERROR)\s+(.+?)(?:\n|$)',
        output
    )
    result.failure_details = failure_blocks[:10]

    return result


# ── Coding Loop State Machine ─────────────────────────────────

class CodingLoop:
    """
    Structured coding loop that drives analysis → plan → execute → test → correct.

    Usage:
        loop = CodingLoop(task)
        while not loop.is_done():
            action = loop.next_action()
            result = execute_action(action)  # External
            loop.feed_result(result)
    """

    def __init__(self, task: CodingTask):
        self.task = task
        self.repo = RepoContext()
        self._phase = "scan"         # scan, plan, edit, test, interpret, patch, retest, done, failed
        self._iteration = 0
        self._last_test: TestResult | None = None
        self._edit_queue: list[dict] = []
        self._completed_edits: list[dict] = []
        self.started_at = time.time()

    def is_done(self) -> bool:
        return self._phase in ("done", "failed")

    def next_action(self) -> dict:
        """
        Returns the next action the orchestrator should perform.

        Action types:
        - scan_repo: Scan repository structure
        - find_files: Find relevant files for the task
        - generate_plan: Ask LLM to plan the changes
        - read_file: Read a specific file
        - edit_file: Apply an edit to a file
        - run_tests: Execute test suite
        - interpret_errors: Ask LLM to interpret test failures
        - generate_fix: Ask LLM to generate a fix for failures
        """
        if self._phase == "scan":
            return {
                "type": "scan_repo",
                "description": "Scan repository structure",
                "params": {"root": str(self.repo.root)},
            }

        if self._phase == "plan":
            return {
                "type": "generate_plan",
                "description": f"Generate modification plan for: {self.task.description}",
                "params": {
                    "task": self.task.description,
                    "task_type": self.task.task_type,
                    "target_files": self.task.target_files,
                    "repo_structure": self.repo.structure_map,
                    "relevant_files": find_relevant_files(
                        self.task.description, self.repo),
                },
            }

        if self._phase == "edit":
            if self._edit_queue:
                edit = self._edit_queue[0]
                return {
                    "type": "edit_file",
                    "description": f"Edit {edit['file']}",
                    "params": edit,
                }
            # No more edits, move to testing
            self._phase = "test"
            return self.next_action()

        if self._phase == "test":
            return {
                "type": "run_tests",
                "description": "Run test suite to validate changes",
                "params": {
                    "command": self.task.test_command or "python -m pytest tests/ --tb=short -q",
                    "timeout": 120,
                },
            }

        if self._phase == "interpret":
            return {
                "type": "interpret_errors",
                "description": "Interpret test failures",
                "params": {
                    "test_output": self._last_test.output[:3000] if self._last_test else "",
                    "failures": self._last_test.failure_details if self._last_test else [],
                    "edits_applied": self._completed_edits,
                },
            }

        if self._phase == "patch":
            return {
                "type": "generate_fix",
                "description": "Generate fix for test failures",
                "params": {
                    "failures": self._last_test.failure_details if self._last_test else [],
                    "error_interpretation": self.task.errors_encountered[-1] if self.task.errors_encountered else "",
                    "files_modified": [e["file"] for e in self._completed_edits],
                },
            }

        if self._phase == "retest":
            self._phase = "test"
            return self.next_action()

        return {"type": "noop", "description": "Nothing to do"}

    def feed_result(self, result: dict) -> None:
        """Process the result of an action and advance the state machine."""
        action_type = result.get("type", "")
        success = result.get("success", False)

        if action_type == "scan_repo":
            if success:
                # Populate repo context from result
                self.repo.total_files = result.get("total_files", 0)
                self.repo.python_files = result.get("python_files", [])
                self.repo.test_files = result.get("test_files", [])
                self.repo.structure_map = result.get("structure_map", {})
                self.repo.recent_changes = result.get("recent_changes", [])
            self._phase = "plan"

        elif action_type == "generate_plan":
            if success:
                plan = result.get("plan", [])
                self.task.plan = plan
                self._edit_queue = result.get("edits", [])
                self._phase = "edit"
            else:
                self._phase = "failed"
                self.task.status = "failed"

        elif action_type == "edit_file":
            if self._edit_queue:
                edit = self._edit_queue.pop(0)
                if success:
                    self._completed_edits.append({
                        "file": edit.get("file", ""),
                        "change": result.get("change_summary", ""),
                    })
                    self.task.edits_applied.append(edit)
                else:
                    self.task.errors_encountered.append(
                        result.get("error", "Edit failed"))

            if not self._edit_queue:
                self._phase = "test"

        elif action_type == "run_tests":
            test_output = result.get("output", "")
            self._last_test = parse_test_output(test_output)
            self.task.test_results.append({
                "iteration": self._iteration,
                "passed": self._last_test.passed,
                "failed": self._last_test.failed,
                "success": self._last_test.success,
            })

            if self._last_test.success:
                self._phase = "done"
                self.task.status = "done"
                log.info("coding_loop_succeeded",
                         task_id=self.task.task_id,
                         iterations=self._iteration,
                         edits=len(self._completed_edits))
            else:
                self._iteration += 1
                if self._iteration >= self.task.max_iterations:
                    self._phase = "failed"
                    self.task.status = "failed"
                    log.warning("coding_loop_max_iterations",
                                task_id=self.task.task_id,
                                iterations=self._iteration)
                else:
                    self._phase = "interpret"

        elif action_type == "interpret_errors":
            self.task.errors_encountered.append(result.get("interpretation", ""))
            self._phase = "patch"

        elif action_type == "generate_fix":
            if success:
                self._edit_queue = result.get("edits", [])
                self._phase = "edit"
            else:
                self._phase = "failed"
                self.task.status = "failed"

    def get_state(self) -> dict:
        """Get current loop state for monitoring."""
        return {
            "task_id": self.task.task_id,
            "phase": self._phase,
            "iteration": self._iteration,
            "max_iterations": self.task.max_iterations,
            "edits_applied": len(self._completed_edits),
            "errors": len(self.task.errors_encountered),
            "last_test_passed": self._last_test.passed if self._last_test else 0,
            "last_test_failed": self._last_test.failed if self._last_test else 0,
            "elapsed_s": round(time.time() - self.started_at, 1),
        }
