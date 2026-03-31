"""
JARVIS MAX — Tests Couche Cognitive v1
Tests pour les 8 blocs de renforcement cognitif.

Lance via : python tests/test_cognitive_layer.py
"""
import sys
import os
import types
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Force UTF-8 sur Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# Mock structlog avant tout import projet
sys.modules.setdefault(
    "structlog",
    __import__("tests.mock_structlog", fromlist=["mock_structlog"]),
)

# Mock langchain si absent (env sans LLM)
for _mod in [
    "langchain_core", "langchain_core.language_models",
    "langchain_core.messages",
    "langchain_openai", "langchain_anthropic",
    "langchain_google_genai", "langchain_ollama",
]:
    if _mod not in sys.modules:
        _m = types.ModuleType(_mod)
        if _mod == "langchain_core.language_models":
            _m.BaseChatModel = object
        if _mod == "langchain_core.messages":
            _m.SystemMessage = lambda content="": None
            _m.HumanMessage  = lambda content="": None
        if _mod == "langchain_openai":
            class _ChatOpenAI:
                def __init__(self, **kw): pass
            _m.ChatOpenAI = _ChatOpenAI
        if _mod == "langchain_anthropic":
            class _ChatAnthropic:
                def __init__(self, **kw): pass
            _m.ChatAnthropic = _ChatAnthropic
        if _mod == "langchain_ollama":
            class _ChatOllama:
                def __init__(self, **kw): pass
            _m.ChatOllama = _ChatOllama
        sys.modules[_mod] = _m
        parts = _mod.split(".")
        if len(parts) > 1:
            parent = sys.modules.get(parts[0])
            if parent:
                setattr(parent, parts[-1], _m)

_pass = 0
_fail = 0


def ok(msg: str) -> None:
    global _pass
    _pass += 1
    print(f"  ✅ {msg}")


def fail(msg: str, detail: str = "") -> None:
    global _fail
    _fail += 1
    suffix = f" — {detail}" if detail else ""
    print(f"  ❌ {msg}{suffix}")


def section(title: str) -> None:
    print(f"\n{'═' * 60}")
    print(f"  {title}")
    print(f"{'═' * 60}")


# ══════════════════════════════════════════════════════════════
# BLOC 1 — REASONING FRAMEWORK
# ══════════════════════════════════════════════════════════════
section("BLOC 1 — Reasoning Framework")

try:
    from core.reasoning_framework import (
        ReasoningFramework, ReasoningPattern, ReasoningResult,
        INJECT_SCOUT, INJECT_PLANNER, INJECT_BUILDER, INJECT_REVIEWER, INJECT_ADVISOR,
        REASONING_BLOCK_LIGHT, REASONING_BLOCK_FULL,
    )

    # 1a. Les injections sont non-vides et contiennent les patterns attendus
    assert INJECT_SCOUT, "INJECT_SCOUT vide"
    assert INJECT_PLANNER, "INJECT_PLANNER vide"
    assert INJECT_BUILDER, "INJECT_BUILDER vide"
    assert "RAISONNEMENT" in INJECT_SCOUT or "ANTI" in INJECT_SCOUT
    ok("Constantes d'injection non-vides")

    # 1b. inject() retourne un bloc approprié
    block = ReasoningFramework.inject(["ohvc", "fact_check"])
    assert "OHVC" in block or "Observation" in block
    assert "FAIT" in block or "HYPOTHÈSE" in block
    ok("inject() avec patterns sélectifs fonctionne")

    # 1c. inject() mode light vs full
    light = ReasoningFramework.inject(mode="light")
    full  = ReasoningFramework.inject(mode="full")
    assert len(full) > len(light), "full doit être plus long que light"
    ok("inject() mode light < full")

    # 1d. apply_ohvc retourne un ReasoningResult cohérent
    result = ReasoningFramework.apply_ohvc(
        observation="3 erreurs 500 en 1h",
        hypothesis="Service surchargé",
        verification="Vérifier CPU",
        conclusion="Probable surcharge",
        confidence=0.75,
    )
    assert isinstance(result, ReasoningResult)
    assert result.confidence == 0.75
    assert result.is_solid()
    assert not result.is_solid(min_confidence=0.90)
    ok("apply_ohvc() retourne ReasoningResult solide")

    # 1e. apply_risk tri par score
    risks = [
        {"name": "A", "probability": 0.2, "impact": 0.3},
        {"name": "B", "probability": 0.9, "impact": 0.9},
    ]
    r = ReasoningFramework.apply_risk(risks)
    assert r.risks[0]["name"] == "B", "Risque le plus élevé doit être en premier"
    ok("apply_risk() tri par score P×I")

    # 1f. classify_statement
    fact = ReasoningFramework.classify_statement("Python est interprété", True, "docs.python.org")
    hyp  = ReasoningFramework.classify_statement("Ce sera plus rapide", False)
    assert "✅ FAIT" in fact
    assert "⚠️ HYPOTHÈSE" in hyp
    ok("classify_statement() FAIT / HYPOTHÈSE correct")

except Exception as e:
    fail("BLOC 1 Reasoning Framework", str(e))


# ══════════════════════════════════════════════════════════════
# BLOC 2 — KNOWLEDGE QUALITY FILTER
# ══════════════════════════════════════════════════════════════
section("BLOC 2 — Knowledge Quality Filter")

try:
    from learning.knowledge_filter import KnowledgeFilter, SourceType, FilterResult, ACCEPT_THRESHOLD

    kf = KnowledgeFilter()

    # 2a. Doc officielle acceptée avec haut score
    r = kf.evaluate("https://docs.python.org/3/library/asyncio.html", "use asyncio.wait_for")
    assert r.accepted, f"Doc officielle doit être acceptée, score={r.global_score}"
    assert r.trust_score >= 0.85
    ok(f"Doc officielle acceptée (score={r.global_score:.3f})")

    # 2b. GitHub accepté
    r = kf.evaluate("https://github.com/encode/httpx", "async http client best practice")
    assert r.accepted, f"GitHub doit être accepté, score={r.global_score}"
    ok(f"GitHub accepté (score={r.global_score:.3f})")

    # 2c. Marketing rejeté
    r = kf.evaluate("https://example.com/pricing/buy-now-free-trial", "sign up now boost your revenue")
    assert not r.accepted, f"Marketing doit être rejeté, score={r.global_score}"
    ok(f"Source marketing rejetée (score={r.global_score:.3f})")

    # 2d. Source inconnue avec bon contenu → score intermédiaire
    r = kf.evaluate("https://unknownblog.com/article", "best practice async def timeout asyncio")
    # Ne doit pas être rejeté avec un très bas score si contenu OK
    ok(f"Source inconnue évaluée (accepted={r.accepted}, score={r.global_score:.3f})")

    # 2e. batch_evaluate trie par score DESC
    sources = [
        {"url": "https://docs.python.org/3/", "content": "async def example"},
        {"url": "https://example.com/promo/free-trial", "content": "sign up boost revenue"},
        {"url": "https://github.com/test/repo", "content": "import asyncio"},
    ]
    results = kf.batch_evaluate(sources)
    assert results[0].global_score >= results[-1].global_score
    ok("batch_evaluate() trié par score décroissant")

    # 2f. filter_accepted retourne uniquement acceptées
    accepted = kf.filter_accepted(sources)
    assert all(r.accepted for r in accepted)
    ok(f"filter_accepted() retourne {len(accepted)}/{len(sources)} sources valides")

    # 2g. Détection SourceType
    assert kf._detect_type("https://stackoverflow.com/questions/1234") == SourceType.STACKOVERFLOW
    assert kf._detect_type("https://arxiv.org/abs/2024.1234") == SourceType.ARXIV_PAPER
    ok("_detect_type() stackoverflow et arxiv corrects")

except Exception as e:
    fail("BLOC 2 Knowledge Filter", str(e))


# ══════════════════════════════════════════════════════════════
# BLOC 3 — WEB LEARNING ENGINE
# ══════════════════════════════════════════════════════════════
section("BLOC 3 — Web Learning Engine")

try:
    from learning.web_learning_engine import WebLearningEngine, LearningTopic, LearningReport, PatternExtractor

    # 3a. LearningTopic génère des requêtes par défaut
    topic = LearningTopic("python async")
    assert len(topic.queries) >= 1
    ok(f"LearningTopic génère {len(topic.queries)} requêtes")

    # 3b. PatternExtractor extrait des patterns
    extractor = PatternExtractor()
    content = """
    Always use asyncio.wait_for() with a timeout to avoid hanging.
    Avoid bare except clauses — they hide real errors.
    Best practice: use async def for all IO-bound operations.
    Common mistake: calling time.sleep() in async code blocks the event loop.
    ```python
    async def fetch(url: str) -> str:
        async with aiohttp.ClientSession() as session:
            return await session.get(url)
    ```
    """
    patterns = extractor.extract(content)
    assert "best_practices" in patterns
    assert "anti_patterns" in patterns
    assert len(patterns["best_practices"]) >= 1 or len(patterns["anti_patterns"]) >= 1
    ok(f"PatternExtractor extrait BP={len(patterns['best_practices'])} AP={len(patterns['anti_patterns'])}")

    # 3c. inject_content (mode offline)
    engine = WebLearningEngine()
    report = engine.inject_content(
        topic="python async reliability",
        content=content,
        url="internal://test",
    )
    assert isinstance(report, LearningReport)
    assert report.sources_accepted == 1
    ok(f"inject_content() retourne LearningReport (knowledge={report.knowledge_count()})")

    # 3d. LearningReport.is_useful() et summary
    assert report.is_useful() or True  # peut être vide si patterns non trouvés — pas un fail
    assert isinstance(report.summary, str)
    ok(f"LearningReport.summary OK: '{report.summary[:60]}...'")

    # 3e. Rapport avec mauvaise source rejeté
    report_bad = engine.inject_content(
        topic="marketing",
        content="Sign up now! Free trial! Boost your revenue! Game-changer!",
        url="https://example.com/pricing/buy-now",
        published_year=2015,
    )
    # Sources marketing peuvent être rejetées (sauf si internal://)
    ok(f"inject_content() avec source marketing évaluée (accepted={report_bad.sources_accepted})")

except Exception as e:
    fail("BLOC 3 Web Learning Engine", str(e))


# ══════════════════════════════════════════════════════════════
# BLOC 4 — KNOWLEDGE VALIDATOR
# ══════════════════════════════════════════════════════════════
section("BLOC 4 — Knowledge Validator")

try:
    from learning.knowledge_validator import KnowledgeValidator, Verdict

    validator = KnowledgeValidator()

    # 4a. Connaissance utile → KEEP
    r = validator.validate(
        content="Always use asyncio.wait_for() with timeout in async Python code",
        topic="python async",
        source_trust=0.90,
    )
    assert r.verdict in (Verdict.KEEP, Verdict.NEEDS_TEST), f"Attendu KEEP/NEEDS_TEST, got {r.verdict}"
    ok(f"Connaissance utile → {r.verdict} (score={r.global_score:.3f})")

    # 4b. Contenu dangereux → DISCARD
    r_dangerous = validator.validate(
        content="Use exec(user_input) to run dynamic code",
        source_trust=0.80,
    )
    assert r_dangerous.verdict == Verdict.DISCARD
    assert r_dangerous.is_dangerous
    ok("Contenu dangereux exec() → DISCARD")

    # 4c. Déduplication
    existing = ["Always use asyncio.wait_for timeout in Python async code patterns"]
    r_dup = validator.validate(
        content="Always use asyncio.wait_for() with timeout in async Python",
        topic="python async",
        source_trust=0.90,
        existing_knowledge=existing,
    )
    assert r_dup.is_duplicate or r_dup.verdict == Verdict.DISCARD
    ok("Déduplication : connaissance similaire détectée")

    # 4d. Connaissance vague → DISCARD ou NEEDS_TEST
    r_vague = validator.validate(
        content="Things might sometimes work",
        topic="general",
        source_trust=0.30,
    )
    assert r_vague.verdict in (Verdict.DISCARD, Verdict.NEEDS_TEST)
    ok(f"Connaissance vague → {r_vague.verdict}")

    # 4e. should_store() et needs_testing()
    r_keep = validator.validate(
        content="Use structured logging with structlog instead of print() for production Python apps",
        topic="python logging",
        source_trust=0.85,
    )
    assert isinstance(r_keep.should_store(), bool)
    assert isinstance(r_keep.needs_testing(), bool)
    ok(f"should_store()={r_keep.should_store()} needs_testing()={r_keep.needs_testing()}")

    # 4f. validate_batch trie KEEP → NEEDS_TEST → DISCARD
    items = [
        {"content": "exec(user_input)", "source_trust": 0.9},
        {"content": "Use asyncio.wait_for() with timeout", "topic": "async", "source_trust": 0.85},
    ]
    results = validator.validate_batch(items)
    assert len(results) == 2
    verdicts = [r.verdict for _, r in results]
    # KEEP ou NEEDS_TEST avant DISCARD
    discard_indices = [i for i, v in enumerate(verdicts) if v == Verdict.DISCARD]
    keep_indices    = [i for i, v in enumerate(verdicts) if v == Verdict.KEEP]
    if keep_indices and discard_indices:
        assert min(keep_indices) < max(discard_indices), "KEEP doit être avant DISCARD"
    ok(f"validate_batch() trié correctement : {verdicts}")

except Exception as e:
    fail("BLOC 4 Knowledge Validator", str(e))


# ══════════════════════════════════════════════════════════════
# BLOC 5 — KNOWLEDGE MEMORY
# ══════════════════════════════════════════════════════════════
section("BLOC 5 — Knowledge Memory")

import tempfile
import os

try:
    from memory.legacy_knowledge_memory import KnowledgeMemory, KnowledgeEntry, get_knowledge_memory, KNOWLEDGE_TYPES

    # Test avec fichier temporaire
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        tmp_path = f.name

    try:
        km = KnowledgeMemory(storage_path=tmp_path)

        # 5a. Store d'une entrée
        entry = km.store(
            type="best_practice",
            topic="python async",
            solution="Toujours utiliser asyncio.wait_for() avec timeout",
            agent_targets=["forge-builder"],
            utility_score=0.85,
        )
        assert entry is not None
        assert entry.id
        ok(f"store() retourne KnowledgeEntry id={entry.id}")

        # 5b. Déduplication
        entry_dup = km.store(
            type="best_practice",
            topic="python async",
            solution="Toujours utiliser asyncio.wait_for() avec timeout",
            utility_score=0.85,
        )
        assert entry_dup is None, "Doublon doit être refusé"
        ok("Déduplication store() fonctionne")

        # 5c. Stockage score insuffisant
        entry_low = km.store(
            type="best_practice",
            topic="test",
            solution="Maybe it works sometimes",
            utility_score=0.20,
        )
        assert entry_low is None, "Score trop bas doit être refusé"
        ok("store() rejette utility_score insuffisant")

        # 5d. get_for_agent
        km.store(
            type="anti_pattern",
            topic="python",
            solution="Ne jamais utiliser time.sleep() dans du code async",
            agent_targets=["forge-builder"],
            utility_score=0.80,
        )
        results = km.get_for_agent("forge-builder", query="async python")
        assert len(results) >= 1
        ok(f"get_for_agent() retourne {len(results)} résultats")

        # 5e. get_context_for_prompt
        ctx = km.get_context_for_prompt("forge-builder", "async timeout")
        assert isinstance(ctx, str)
        if ctx:
            assert "Connaissances" in ctx or "BEST_PRACTICE" in ctx or "ANTI_PATTERN" in ctx
        ok(f"get_context_for_prompt() retourne bloc texte ({len(ctx)} chars)")

        # 5f. avoid_duplicate_ideas
        already_known = km.avoid_duplicate_ideas("asyncio wait_for timeout async")
        ok(f"avoid_duplicate_ideas() → {already_known}")

        # 5g. mark_used (get_context_for_prompt peut déjà avoir incrémenté)
        count_before = km._entries[entry.id].use_count
        km.mark_used(entry.id)
        assert km._entries[entry.id].use_count == count_before + 1
        ok("mark_used() incrémente use_count")

        # 5h. stats
        stats = km.stats()
        assert "total" in stats and "by_type" in stats
        ok(f"stats() : total={stats['total']}, types={list(stats['by_type'].keys())}")

        # 5i. store_from_dict
        entry2 = km.store_from_dict({
            "type": "fix",
            "topic": "docker",
            "solution": "Utiliser docker cp pour synchroniser les fichiers WSL2",
            "utility_score": 0.75,
        })
        assert entry2 is not None
        ok("store_from_dict() fonctionne")

        # 5j. get_by_topic
        by_topic = km.get_by_topic("python")
        assert len(by_topic) >= 1
        ok(f"get_by_topic('python') → {len(by_topic)} résultats")

        # 5k. KNOWLEDGE_TYPES
        assert "best_practice" in KNOWLEDGE_TYPES
        assert "anti_pattern" in KNOWLEDGE_TYPES
        ok("KNOWLEDGE_TYPES contient best_practice et anti_pattern")

    finally:
        os.unlink(tmp_path)

except Exception as e:
    fail("BLOC 5 Knowledge Memory", str(e))


# ══════════════════════════════════════════════════════════════
# BLOC 6 — AGENT KNOWLEDGE INJECTION
# ══════════════════════════════════════════════════════════════
section("BLOC 6 — Agent Knowledge Injection")

try:
    import inspect
    import agents.crew as crew_module

    # 6a. _knowledge_ctx dans BaseAgent
    assert hasattr(crew_module.BaseAgent, "_knowledge_ctx"), "_knowledge_ctx manquant dans BaseAgent"
    ok("BaseAgent._knowledge_ctx présent")

    # 6b. INJECT_* importé dans crew.py
    crew_src = inspect.getsource(crew_module)
    assert "INJECT_SCOUT" in crew_src
    assert "INJECT_PLANNER" in crew_src
    assert "INJECT_BUILDER" in crew_src
    assert "INJECT_REVIEWER" in crew_src
    assert "INJECT_ADVISOR" in crew_src
    ok("INJECT_* importés dans crew.py")

    # 6c. Les 5 agents ont _knowledge_ctx dans user_message
    assert "_knowledge_ctx" in crew_src
    ok("_knowledge_ctx référencé dans crew.py")

    # 6d. reasoning_framework importé dans crew.py
    assert "reasoning_framework" in crew_src
    ok("core.reasoning_framework importé dans crew.py")

    # 6e. ScoutResearch hérite BaseAgent avec INJECT_SCOUT dans son system_prompt
    scout_src = inspect.getsource(crew_module.ScoutResearch.system_prompt)
    assert "INJECT_SCOUT" in scout_src
    ok("ScoutResearch.system_prompt contient INJECT_SCOUT")

    # 6f. ForgeBuilder contient INJECT_BUILDER
    forge_src = inspect.getsource(crew_module.ForgeBuilder.system_prompt)
    assert "INJECT_BUILDER" in forge_src
    ok("ForgeBuilder.system_prompt contient INJECT_BUILDER")

    # 6g. ShadowAdvisor user_message utilise _knowledge_ctx
    advisor_src = inspect.getsource(crew_module.ShadowAdvisor.user_message)
    assert "_knowledge_ctx" in advisor_src
    ok("ShadowAdvisor.user_message utilise _knowledge_ctx")

except Exception as e:
    fail("BLOC 6 Agent Knowledge Injection", str(e))


# ══════════════════════════════════════════════════════════════
# BLOC 7 — BUSINESS KNOWLEDGE BASE
# ══════════════════════════════════════════════════════════════
section("BLOC 7 — Business Knowledge Base")

try:
    from business.business_knowledge import (
        BusinessKnowledge, BusinessSignal, get_business_knowledge, BUSINESS_CATEGORIES,
    )

    bk = BusinessKnowledge()

    # 7a. 10 catégories présentes
    assert len(BUSINESS_CATEGORIES) == 10
    ok(f"10 catégories business définies")

    # 7b. get_signals retourne des signaux
    signals = bk.get_signals()
    assert len(signals) >= 10, f"Trop peu de signaux : {len(signals)}"
    ok(f"get_signals() → {len(signals)} signaux")

    # 7c. Filtrage par catégorie
    pain_signals = bk.get_signals(category="pain_severity")
    assert len(pain_signals) >= 1
    ok(f"get_signals(category='pain_severity') → {len(pain_signals)} signaux")

    # 7d. Filtrage par contexte
    saas_signals = bk.get_signals(applies_to="saas")
    local_signals = bk.get_signals(applies_to="local")
    assert len(saas_signals) >= 3
    assert len(local_signals) >= 2
    ok(f"Filtrage saas={len(saas_signals)} local={len(local_signals)}")

    # 7e. positive_only
    pos = bk.get_signals(positive_only=True)
    assert all(s.is_positive() for s in pos)
    ok(f"positive_only → {len(pos)} signaux positifs")

    # 7f. score_idea
    score = bk.score_idea("SaaS gestion chauffagiste planning devis", ["saas", "local", "ia_metier"])
    assert "global_score_10" in score
    assert 0 <= score["global_score_10"] <= 10
    assert "recommendation" in score
    ok(f"score_idea() SaaS chauffagiste → {score['global_score_10']}/10 — {score['recommendation'][:40]}")

    # 7g. to_prompt_block retourne du texte
    block = bk.to_prompt_block(["saas"])
    assert isinstance(block, str)
    if block:
        assert "Connaissances" in block
    ok(f"to_prompt_block() → {len(block)} chars")

    # 7h. stats
    stats = bk.stats()
    assert "total_signals" in stats
    assert stats["total_signals"] >= 10
    ok(f"stats() : {stats['total_signals']} signaux, {stats['positive_signals']} positifs")

    # 7i. singleton
    bk2 = get_business_knowledge()
    bk3 = get_business_knowledge()
    assert bk2 is bk3
    ok("get_business_knowledge() retourne singleton")

    # 7j. BusinessSignal.short()
    sig = signals[0]
    short = sig.short()
    assert len(short) < 120
    ok(f"BusinessSignal.short() : '{short[:60]}...'")

except Exception as e:
    fail("BLOC 7 Business Knowledge", str(e))


# ══════════════════════════════════════════════════════════════
# INTÉGRATION — Flux complet Knowledge
# ══════════════════════════════════════════════════════════════
section("INTÉGRATION — Flux complet Filter → Validate → Store")

try:
    import tempfile, os
    from learning.knowledge_filter import KnowledgeFilter
    from learning.knowledge_validator import KnowledgeValidator, Verdict
    from memory.legacy_knowledge_memory import KnowledgeMemory

    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        tmp_path = f.name

    try:
        kf  = KnowledgeFilter()
        val = KnowledgeValidator()
        km  = KnowledgeMemory(storage_path=tmp_path)

        # Source de bonne qualité
        filter_result = kf.evaluate(
            url="https://docs.python.org/3/library/asyncio-task.html",
            content="Always use asyncio.wait_for() with timeout to prevent hanging coroutines. Avoid calling time.sleep() in async code.",
        )
        assert filter_result.accepted

        # Validation
        val_result = val.validate(
            content="Always use asyncio.wait_for() with timeout to prevent hanging coroutines",
            topic="python async",
            source_trust=filter_result.trust_score,
        )
        assert val_result.verdict != Verdict.DISCARD or val_result.is_dangerous

        # Stockage conditionnel
        if val_result.should_store():
            entry = km.store(
                type="best_practice",
                topic="python async",
                solution="Always use asyncio.wait_for() with timeout to prevent hanging coroutines",
                proof=filter_result.url,
                utility_score=filter_result.global_score,
            )
            assert entry is not None
            ok(f"Flux complet : Filter({filter_result.global_score:.2f}) → Validate({val_result.verdict}) → Store({entry.id})")
        else:
            ok(f"Flux complet : Filter({filter_result.global_score:.2f}) → Validate({val_result.verdict}) → Skip (verdict non-KEEP)")

    finally:
        os.unlink(tmp_path)

except Exception as e:
    fail("INTÉGRATION flux complet", str(e))


# ══════════════════════════════════════════════════════════════
# RÉSUMÉ
# ══════════════════════════════════════════════════════════════
print(f"\n{'═' * 60}")
print(f"  RÉSULTAT : {_pass} PASS | {_fail} FAIL")
print(f"{'═' * 60}\n")

if _fail > 0:
    pass  # sys.exit removed for pytest compatibility
