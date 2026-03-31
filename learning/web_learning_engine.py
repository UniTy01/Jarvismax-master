"""
JARVIS MAX — Web Learning Engine v1
Moteur d'apprentissage web contrôlé.

Flux :
  1. Prend un sujet ciblé
  2. Génère des requêtes propres
  3. Filtre les sources avec KnowledgeQualityFilter
  4. Extrait best practices, erreurs fréquentes, patterns robustes, anti-patterns
  5. Produit un rapport structuré exploitable

Output :
{
  "topic": "python async reliability",
  "sources_evaluated": 5,
  "sources_accepted": 3,
  "best_practices": [...],
  "anti_patterns": [...],
  "common_failures": [...],
  "reusable_patterns": [...],
  "summary": "..."
}

Note : le moteur utilise le scraper existant (tools/browser/scraper.py)
       et ne fait JAMAIS de requêtes directes hors du flux contrôlé.
"""
from __future__ import annotations

import asyncio
import json
import re
import time
import structlog
from dataclasses import dataclass, field
from typing import Any

from learning.knowledge_filter import KnowledgeFilter, FilterResult

log = structlog.get_logger()


# ── Sujet d'apprentissage ─────────────────────────────────────────────────────

@dataclass
class LearningTopic:
    name: str
    queries: list[str] = field(default_factory=list)
    max_sources: int = 5
    min_score: float = 0.55

    def __post_init__(self):
        if not self.queries:
            # Requêtes par défaut à partir du nom
            self.queries = [
                f"{self.name} best practices",
                f"{self.name} common mistakes",
                f"{self.name} tutorial site:docs.python.org OR site:github.com",
            ]


# ── Rapport d'apprentissage ───────────────────────────────────────────────────

@dataclass
class LearningReport:
    topic: str
    sources_evaluated: int = 0
    sources_accepted: int = 0
    best_practices: list[str] = field(default_factory=list)
    anti_patterns: list[str] = field(default_factory=list)
    common_failures: list[str] = field(default_factory=list)
    reusable_patterns: list[str] = field(default_factory=list)
    accepted_sources: list[dict] = field(default_factory=list)
    rejected_sources: list[dict] = field(default_factory=list)
    duration_s: float = 0.0
    timestamp: float = field(default_factory=time.time)
    summary: str = ""

    def to_dict(self) -> dict:
        return {
            "topic": self.topic,
            "sources_evaluated": self.sources_evaluated,
            "sources_accepted": self.sources_accepted,
            "best_practices": self.best_practices,
            "anti_patterns": self.anti_patterns,
            "common_failures": self.common_failures,
            "reusable_patterns": self.reusable_patterns,
            "accepted_sources": self.accepted_sources,
            "rejected_sources": self.rejected_sources,
            "duration_s": round(self.duration_s, 2),
            "timestamp": self.timestamp,
            "summary": self.summary,
        }

    def is_useful(self) -> bool:
        """Rapport utile si au moins 1 BP ou 1 anti-pattern."""
        return bool(self.best_practices or self.anti_patterns or self.reusable_patterns)

    def knowledge_count(self) -> int:
        return (
            len(self.best_practices)
            + len(self.anti_patterns)
            + len(self.common_failures)
            + len(self.reusable_patterns)
        )


# ── Extracteur de patterns ────────────────────────────────────────────────────

class PatternExtractor:
    """
    Extrait des patterns exploitables depuis du contenu textuel.
    Utilise des heuristiques syntaxiques + regex — pas de LLM requis.
    """

    # Indicateurs de best practice
    _BP_SIGNALS = re.compile(
        r"(always|best practice|recommended|prefer|should|use .+ instead|"
        r"correct way|proper way|tip:|pro tip:|✅|👍)",
        re.IGNORECASE,
    )

    # Indicateurs d'anti-pattern
    _AP_SIGNALS = re.compile(
        r"(avoid|never|don't|do not|anti-pattern|bad practice|"
        r"common mistake|pitfall|wrong way|❌|👎|deprecated|"
        r"instead of .+ use|warning:|caution:)",
        re.IGNORECASE,
    )

    # Indicateurs d'erreur courante
    _FAIL_SIGNALS = re.compile(
        r"(common error|frequent mistake|gotcha|bug|issue|problem|"
        r"exception|traceback|error:|raises|AttributeError|TypeError|"
        r"fails when|breaks when|crash)",
        re.IGNORECASE,
    )

    # Indicateurs de pattern réutilisable (code)
    _PATTERN_SIGNALS = re.compile(
        r"(pattern|template|recipe|boilerplate|snippet|example:|"
        r"```python|def \w+\(|class \w+|async def|@\w+)",
        re.IGNORECASE,
    )

    def extract(self, content: str, max_per_category: int = 5) -> dict[str, list[str]]:
        """
        Extrait les patterns depuis le contenu.
        Retourne un dict avec best_practices, anti_patterns, common_failures, reusable_patterns.
        """
        lines = [l.strip() for l in content.splitlines() if len(l.strip()) > 20]

        best_practices: list[str] = []
        anti_patterns: list[str] = []
        common_failures: list[str] = []
        reusable_patterns: list[str] = []

        # Extraction ligne par ligne avec contexte
        for i, line in enumerate(lines):
            # Contexte : ligne précédente + actuelle + suivante
            ctx = " ".join(lines[max(0, i-1):min(len(lines), i+2)])

            if (
                len(best_practices) < max_per_category
                and self._BP_SIGNALS.search(ctx)
                and not self._AP_SIGNALS.search(line[:30])
            ):
                cleaned = self._clean(line)
                if cleaned and cleaned not in best_practices:
                    best_practices.append(cleaned)

            elif (
                len(anti_patterns) < max_per_category
                and self._AP_SIGNALS.search(ctx)
            ):
                cleaned = self._clean(line)
                if cleaned and cleaned not in anti_patterns:
                    anti_patterns.append(cleaned)

            elif (
                len(common_failures) < max_per_category
                and self._FAIL_SIGNALS.search(ctx)
            ):
                cleaned = self._clean(line)
                if cleaned and cleaned not in common_failures:
                    common_failures.append(cleaned)

            elif (
                len(reusable_patterns) < max_per_category
                and self._PATTERN_SIGNALS.search(ctx)
            ):
                cleaned = self._clean(line)
                if cleaned and cleaned not in reusable_patterns:
                    reusable_patterns.append(cleaned)

        return {
            "best_practices": best_practices,
            "anti_patterns": anti_patterns,
            "common_failures": common_failures,
            "reusable_patterns": reusable_patterns,
        }

    def _clean(self, line: str) -> str:
        """Nettoie une ligne pour la rendre stockable."""
        # Supprimer markdown excessif
        line = re.sub(r"^#+\s*", "", line)
        line = re.sub(r"\*\*(.+?)\*\*", r"\1", line)
        line = re.sub(r"`(.+?)`", r"\1", line)
        line = line.strip("- •→➤>").strip()
        return line[:200] if len(line) > 200 else line


# ── Moteur d'apprentissage web ────────────────────────────────────────────────

class WebLearningEngine:
    """
    Moteur d'apprentissage web contrôlé.

    Usage async :
        engine = WebLearningEngine()
        report = await engine.learn("python async reliability")
        if report.is_useful():
            # stocker dans KnowledgeMemory
    """

    def __init__(self):
        self._filter    = KnowledgeFilter()
        self._extractor = PatternExtractor()

    async def learn(
        self,
        topic: str | LearningTopic,
        max_sources: int = 5,
    ) -> LearningReport:
        """
        Apprentissage complet sur un sujet.
        Retourne un LearningReport prêt à être validé et stocké.
        """
        t0 = time.monotonic()

        if isinstance(topic, str):
            topic = LearningTopic(name=topic, max_sources=max_sources)

        log.info("web_learning_start", topic=topic.name, queries=len(topic.queries))

        report = LearningReport(topic=topic.name)

        # Collecte des sources
        raw_sources = await self._collect_sources(topic)
        report.sources_evaluated = len(raw_sources)

        # Filtrage qualité
        for src in raw_sources:
            result = self._filter.evaluate(
                url=src.get("url", ""),
                content=src.get("content", ""),
                published_year=src.get("published_year"),
            )
            if result.accepted:
                report.sources_accepted += 1
                report.accepted_sources.append(result.to_dict())
                # Extraction de patterns
                patterns = self._extractor.extract(src.get("content", ""))
                self._merge_patterns(report, patterns)
            else:
                report.rejected_sources.append({
                    "url": result.url,
                    "reason": result.rejection_reason,
                    "score": result.global_score,
                })
                log.debug(
                    "source_rejected",
                    url=result.url[:60],
                    reason=result.rejection_reason[:80],
                )

        # Déduplication
        report.best_practices    = list(dict.fromkeys(report.best_practices))[:10]
        report.anti_patterns     = list(dict.fromkeys(report.anti_patterns))[:10]
        report.common_failures   = list(dict.fromkeys(report.common_failures))[:10]
        report.reusable_patterns = list(dict.fromkeys(report.reusable_patterns))[:10]

        # Résumé
        report.summary = self._build_summary(report)
        report.duration_s = time.monotonic() - t0

        log.info(
            "web_learning_done",
            topic=topic.name,
            accepted=report.sources_accepted,
            rejected=report.sources_evaluated - report.sources_accepted,
            knowledge=report.knowledge_count(),
            duration_s=round(report.duration_s, 1),
        )
        return report

    async def _collect_sources(self, topic: LearningTopic) -> list[dict]:
        """
        Collecte des sources via le scraper existant ou simulation.
        En mode sans scraper : retourne une liste vide (pas d'erreur).
        """
        sources: list[dict] = []

        try:
            from tools.browser.scraper import WebScraper
            scraper = WebScraper()

            for query in topic.queries[:3]:  # max 3 requêtes
                try:
                    results = await asyncio.wait_for(
                        scraper.search(query, max_results=2),
                        timeout=15.0,
                    )
                    for r in results:
                        sources.append({
                            "url": r.get("url", ""),
                            "content": r.get("content", r.get("snippet", "")),
                            "published_year": r.get("year"),
                        })
                    if len(sources) >= topic.max_sources:
                        break
                except asyncio.TimeoutError:
                    log.warning("web_scrape_timeout", query=query[:50])
                except Exception as e:
                    log.warning("web_scrape_error", query=query[:50], err=str(e)[:80])

        except ImportError:
            log.debug("web_scraper_unavailable_learning_offline")

        return sources[:topic.max_sources]

    def _merge_patterns(self, report: LearningReport, patterns: dict) -> None:
        report.best_practices.extend(patterns.get("best_practices", []))
        report.anti_patterns.extend(patterns.get("anti_patterns", []))
        report.common_failures.extend(patterns.get("common_failures", []))
        report.reusable_patterns.extend(patterns.get("reusable_patterns", []))

    def _build_summary(self, report: LearningReport) -> str:
        parts = [
            f"Sujet : {report.topic}",
            f"Sources : {report.sources_accepted}/{report.sources_evaluated} acceptées",
            f"Connaissances : {report.knowledge_count()} extraites",
        ]
        if report.best_practices:
            parts.append(f"Meilleures pratiques : {report.best_practices[0][:80]}...")
        if report.anti_patterns:
            parts.append(f"Anti-pattern principal : {report.anti_patterns[0][:80]}...")
        return " | ".join(parts)

    def inject_content(
        self,
        topic: str,
        content: str,
        url: str = "internal://jarvismax",
        published_year: int | None = None,
    ) -> LearningReport:
        """
        Mode hors-ligne : injecter du contenu directement (sans scraping).
        Utile pour les tests et l'apprentissage depuis sources internes.
        """
        report = LearningReport(topic=topic)
        report.sources_evaluated = 1

        result = self._filter.evaluate(url=url, content=content, published_year=published_year)
        if result.accepted or url.startswith("internal://"):
            # Sources internes toujours acceptées
            report.sources_accepted = 1
            report.accepted_sources = [result.to_dict()]
            patterns = self._extractor.extract(content)
            self._merge_patterns(report, patterns)
            report.summary = self._build_summary(report)
        else:
            report.rejected_sources = [{"url": url, "reason": result.rejection_reason}]
            report.summary = f"Contenu rejeté : {result.rejection_reason}"

        return report
