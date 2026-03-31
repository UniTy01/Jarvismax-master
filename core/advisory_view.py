"""
JARVIS MAX — Advisory View v1
Visualisation lisible du rapport Shadow Advisor.

Transforme un AdvisoryReport brut en affichage clair et exploitable.

Formats disponibles :
  - text  : sortie terminal ASCII lisible
  - dict  : structure JSON exportable
  - short : ligne de résumé compacte
"""
from __future__ import annotations

from typing import Any


# ── Icônes et couleurs ────────────────────────────────────────────────────────

_DECISION_ICON = {
    "GO":      "✅",
    "IMPROVE": "⚠️ ",
    "NO-GO":   "❌",
    "NO_GO":   "❌",
    "UNKNOWN": "❓",
}

_SEVERITY_ICON = {
    "high":   "🔴",
    "medium": "🟡",
    "low":    "🟢",
}

_SCORE_BAR_WIDTH = 20

def _score_bar(score: float) -> str:
    """Barre de progression ASCII pour un score /10."""
    filled = int((score / 10.0) * _SCORE_BAR_WIDTH)
    bar    = "█" * filled + "░" * (_SCORE_BAR_WIDTH - filled)
    color  = "🟢" if score >= 7.5 else "🟡" if score >= 4.0 else "🔴"
    return f"{color} [{bar}] {score:.1f}/10"


# ── Advisory View ─────────────────────────────────────────────────────────────

class AdvisoryView:
    """
    Visualise un rapport shadow advisor de façon lisible.

    Usage :
        view = AdvisoryView(report_dict)
        print(view.text())
        summary = view.short()
        data    = view.to_dict()
    """

    def __init__(self, report: dict|Any):
        """Accepte un dict ou un AdvisoryReport."""
        if isinstance(report, dict):
            self._r = report
        else:
            # AdvisoryReport object
            try:
                self._r = report.to_dict()
            except AttributeError:
                self._r = {}

        self._decision = self._extract_decision()
        self._score    = float(self._r.get("final_score", self._r.get("score", 0.0)))
        self._confidence = float(self._r.get("confidence", 0.5))

    # ── Formats ───────────────────────────────────────────────────────────────

    def text(self) -> str:
        """Sortie texte complète et lisible."""
        lines: list[str] = []

        # En-tête
        icon = _DECISION_ICON.get(self._decision, "❓")
        lines.append("=" * 55)
        lines.append(f"  SHADOW ADVISOR — {icon} {self._decision}")
        lines.append("=" * 55)
        lines.append(f"  Score      : {_score_bar(self._score)}")
        lines.append(f"  Confiance  : {self._confidence:.0%}")

        # Justification
        just = str(self._r.get("justification", "")).strip()
        if just:
            lines.append("")
            lines.append("  Analyse :")
            for line in self._wrap(just, 52):
                lines.append(f"    {line}")

        # Blocages critiques
        issues = self._r.get("blocking_issues", [])
        if issues:
            lines.append("")
            lines.append(f"  Blocages ({len(issues)}) :")
            for iss in issues[:5]:
                sev  = str(iss.get("severity", "low")).lower()
                icon = _SEVERITY_ICON.get(sev, "⚪")
                desc = str(iss.get("description", ""))[:80]
                lines.append(f"    {icon} [{sev.upper()}] {desc}")
                ev = str(iss.get("evidence", "")).strip()
                if ev:
                    lines.append(f"         preuve : {ev[:60]}")

        # Risques
        risks = self._r.get("risks", [])
        if risks:
            lines.append("")
            lines.append(f"  Risques ({len(risks)}) :")
            for r in risks[:4]:
                sev  = str(r.get("severity", "medium")).lower()
                icon = _SEVERITY_ICON.get(sev, "⚪")
                desc = str(r.get("description", ""))[:80]
                prob = r.get("probability", "?")
                imp  = r.get("impact", "?")
                lines.append(f"    {icon} {desc}")
                lines.append(f"         P={prob} / I={imp}")

        # Améliorations
        improvements = self._r.get("improvements", [])
        if improvements:
            lines.append("")
            lines.append(f"  Améliorations ({len(improvements)}) :")
            for imp in improvements[:4]:
                lines.append(f"    → {str(imp)[:80]}")

        # Tests requis
        tests = self._r.get("tests_required", [])
        if tests:
            lines.append("")
            lines.append(f"  Tests requis ({len(tests)}) :")
            for t in tests[:3]:
                lines.append(f"    ◦ {str(t)[:80]}")

        # Points faibles
        weak = self._r.get("weak_points", [])
        if weak:
            lines.append("")
            lines.append(f"  Points faibles :")
            for w in weak[:3]:
                lines.append(f"    · {str(w)[:80]}")

        lines.append("=" * 55)
        return "\n".join(lines)

    def short(self) -> str:
        """Résumé compact sur une ligne."""
        icon    = _DECISION_ICON.get(self._decision, "?")
        issues  = len(self._r.get("blocking_issues", []))
        risks   = len(self._r.get("risks", []))
        return (
            f"{icon} {self._decision} "
            f"| score={self._score:.1f}/10 "
            f"| blocages={issues} risques={risks} "
            f"| conf={self._confidence:.0%}"
        )

    def to_dict(self) -> dict:
        """Structure JSON exportable et propre."""
        return {
            "decision":       self._decision,
            "score":          round(self._score, 2),
            "confidence":     round(self._confidence, 3),
            "decision_icon":  _DECISION_ICON.get(self._decision, "?"),
            "score_bar":      _score_bar(self._score),
            "justification":  str(self._r.get("justification", ""))[:300],
            "blocking_issues": self._format_issues(),
            "risks":           self._format_risks(),
            "improvements":    [str(i)[:200] for i in self._r.get("improvements", [])],
            "tests_required":  [str(t)[:200] for t in self._r.get("tests_required", [])],
            "weak_points":     [str(w)[:200] for w in self._r.get("weak_points", [])],
            "is_go":       self._decision == "GO",
            "is_blocked":  self._decision in {"NO-GO", "NO_GO"},
            "needs_work":  self._decision == "IMPROVE",
        }

    def is_go(self)      -> bool: return self._decision == "GO"
    def is_no_go(self)   -> bool: return self._decision in {"NO-GO", "NO_GO"}
    def is_improve(self) -> bool: return self._decision == "IMPROVE"

    def critical_count(self) -> int:
        return sum(
            1 for i in self._r.get("blocking_issues", [])
            if str(i.get("severity", "")).lower() == "high"
        )

    # ── Internals ─────────────────────────────────────────────────────────────

    def _extract_decision(self) -> str:
        d = str(self._r.get("decision", "UNKNOWN")).upper().strip()
        if d in {"NO-GO", "NOGO", "NO_GO"}:
            return "NO-GO"
        if d in {"GO"}:
            return "GO"
        if d in {"IMPROVE"}:
            return "IMPROVE"
        return "UNKNOWN"

    def _format_issues(self) -> list[dict]:
        result = []
        for iss in self._r.get("blocking_issues", []):
            sev = str(iss.get("severity", "medium")).lower()
            result.append({
                "type":        str(iss.get("type", "logique")),
                "description": str(iss.get("description", ""))[:200],
                "severity":    sev,
                "severity_icon": _SEVERITY_ICON.get(sev, "⚪"),
                "evidence":    str(iss.get("evidence", ""))[:150],
            })
        return result

    def _format_risks(self) -> list[dict]:
        result = []
        for r in self._r.get("risks", []):
            sev = str(r.get("severity", "medium")).lower()
            result.append({
                "type":        str(r.get("type", "général")),
                "description": str(r.get("description", ""))[:200],
                "severity":    sev,
                "severity_icon": _SEVERITY_ICON.get(sev, "⚪"),
                "probability": str(r.get("probability", "medium")),
                "impact":      str(r.get("impact", "medium")),
            })
        return result

    @staticmethod
    def _wrap(text: str, width: int) -> list[str]:
        """Découpe un texte long en lignes de longueur max."""
        words  = text.split()
        lines  = []
        current = ""
        for word in words:
            if len(current) + len(word) + 1 > width:
                if current:
                    lines.append(current)
                current = word
            else:
                current = (current + " " + word).strip()
        if current:
            lines.append(current)
        return lines or [""]


# ── Raccourcis ────────────────────────────────────────────────────────────────

def format_advisory(report: dict|Any) -> str:
    """Raccourci : formate un rapport en texte lisible."""
    return AdvisoryView(report).text()


def advisory_short(report: dict|Any) -> str:
    """Raccourci : résumé court d'un rapport."""
    return AdvisoryView(report).short()
