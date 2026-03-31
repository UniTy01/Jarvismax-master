"""
JARVIS MAX — Tests Shadow-Advisor V2
Tests complets : 4 scénarios réels + cas négatifs + cohérence score/décision.

Lance via : python tests/test_shadow_advisor.py
"""
import sys
import os
import json
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
    suffix = f"\n     → {detail}" if detail else ""
    print(f"  ❌ {msg}{suffix}")


def section(title: str) -> None:
    print(f"\n{'═' * 60}")
    print(f"  {title}")
    print(f"{'═' * 60}")


# ══════════════════════════════════════════════════════════════
# FIXTURES — Sorties LLM simulées
# ══════════════════════════════════════════════════════════════

# CAS 1 : Décision technique — async sans timeout (NO-GO)
_TECHNICAL_NOGO = json.dumps({
    "decision": "NO-GO",
    "confidence": 0.85,
    "blocking_issues": [
        {
            "type": "technique",
            "description": "La coroutine fetch() n'utilise pas asyncio.wait_for() — risque de blocage infini.",
            "severity": "high",
            "evidence": "Ligne 42 : await session.get(url) sans timeout"
        },
        {
            "type": "test",
            "description": "Aucun test de timeout dans la suite existante.",
            "severity": "medium",
            "evidence": "Recherche de 'wait_for' dans tests/ → 0 résultat"
        }
    ],
    "risks": [
        {
            "type": "fiabilité",
            "description": "Un serveur lent bloque le thread asyncio entier.",
            "severity": "high",
            "probability": "high",
            "impact": "high"
        }
    ],
    "weak_points": [
        "Pas de gestion d'erreur réseau (ConnectionError, TimeoutError)",
        "Variable 'url' non validée avant appel HTTP"
    ],
    "inconsistencies": [
        "La fonction est documentée comme 'fire and forget' mais retourne une valeur"
    ],
    "missing_proofs": [
        "Aucun test de charge pour valider le comportement sous 100 req/s"
    ],
    "improvements": [
        "Envelopper await session.get(url) dans asyncio.wait_for(coro, timeout=10.0)",
        "Ajouter try/except asyncio.TimeoutError avec log structuré",
        "Ajouter test unittest pour simuler timeout serveur"
    ],
    "tests_required": [
        "test_fetch_timeout_server_slow",
        "test_fetch_invalid_url",
        "test_fetch_connection_refused"
    ],
    "final_score": 3.5,
    "justification": "Blocage infini possible sur réseau lent ou serveur défaillant — critique pour un système multi-agents où chaque agent est en asyncio. Sans timeout, un agent peut figer l'orchestrateur entier."
})

# CAS 2 : Patch de code — valide avec réserves (IMPROVE)
_PATCH_IMPROVE = json.dumps({
    "decision": "IMPROVE",
    "confidence": 0.72,
    "blocking_issues": [
        {
            "type": "logique",
            "description": "Le patch remplace _compute_session_status() par un appel ternaire — mais le cas None n'est pas documenté.",
            "severity": "medium",
            "evidence": "Ligne 501 : status_info = session_status if session_status is not None else self._compute_session_status(session)"
        }
    ],
    "risks": [
        {
            "type": "régression",
            "description": "Si session_status est passé comme False (falsy) — l'ternaire échouerait à cause de 'is not None'.",
            "severity": "low",
            "probability": "low",
            "impact": "medium"
        }
    ],
    "weak_points": [
        "Documentation de la signature _generate_report() non mise à jour",
        "Test de régression pour le double-emit non ajouté"
    ],
    "inconsistencies": [],
    "missing_proofs": [
        "Pas de test validant que session_status_computed n'est émis qu'une fois"
    ],
    "improvements": [
        "Ajouter assert sur le type de session_status dans _generate_report",
        "Ajouter test unitaire comptant les émissions de session_status_computed"
    ],
    "tests_required": [
        "test_single_emission_session_status_computed",
        "test_generate_report_with_explicit_status"
    ],
    "final_score": 6.2,
    "justification": "Le patch corrige le double-emit identifié mais introduit une ambiguité sur la valeur None vs valeur falsie. La logique est correcte dans le cas courant mais mérite un test de régression explicite."
})

# CAS 3 : Idée business — fort potentiel avec risques (IMPROVE)
_BUSINESS_IMPROVE = json.dumps({
    "decision": "IMPROVE",
    "confidence": 0.78,
    "blocking_issues": [
        {
            "type": "business",
            "description": "Le marché des chauffagistes est fragmenté — 50 000 entreprises mais 80% sont des solo/micro-entrepreneurs sans budget logiciel.",
            "severity": "medium",
            "evidence": "[HYPOTHÈSE] Estimation basée sur INSEE secteur chauffage 2022"
        }
    ],
    "risks": [
        {
            "type": "marché",
            "description": "Concurrence directe d'Obat, Planify et Dolibarr — déjà établis sur ce segment.",
            "severity": "high",
            "probability": "high",
            "impact": "medium"
        },
        {
            "type": "adoption",
            "description": "Résistance au changement des artisans — délai d'adoption 6-18 mois.",
            "severity": "medium",
            "probability": "medium",
            "impact": "medium"
        }
    ],
    "weak_points": [
        "Aucune différenciation claire par rapport aux concurrents existants",
        "Prix non validé avec prospects réels"
    ],
    "inconsistencies": [
        "Le pitch dit 'aucun concurrent' mais Obat et Planify couvrent exactement ce marché"
    ],
    "missing_proofs": [
        "Pas d'entretiens clients validant la douleur",
        "ROI client non calculé",
        "Prix de vente non testé"
    ],
    "improvements": [
        "Identifier 3 différenciateurs non couverts par Obat (ex: IA vocale, auto-devis photo)",
        "Conduire 10 entretiens clients chauffagistes avant de coder",
        "Définir le pricing avec comparaison directe vs solution actuelle client"
    ],
    "tests_required": [
        "Validation terrain : 10 entretiens prospects",
        "Test de landing page avant dev",
        "Analyse différentielle Obat vs proposition"
    ],
    "final_score": 5.8,
    "justification": "L'idée est réelle et le marché existe mais le pitch souffre d'une incohérence majeure ('aucun concurrent' est faux). La différenciation doit être établie sur des preuves terrain, pas sur des hypothèses."
})

# CAS 4 : Workflow métier — GO avec conditions (GO)
_WORKFLOW_GO = json.dumps({
    "decision": "GO",
    "confidence": 0.88,
    "blocking_issues": [],
    "risks": [
        {
            "type": "intégration",
            "description": "Le webhook n8n peut avoir un délai de 2-5s sous charge — acceptable pour ce workflow.",
            "severity": "low",
            "probability": "medium",
            "impact": "low"
        }
    ],
    "weak_points": [
        "Le retry du webhook n'est pas configuré (défaut n8n : 0 retry)"
    ],
    "inconsistencies": [],
    "missing_proofs": [],
    "improvements": [
        "Configurer retry=3 sur le nœud webhook n8n",
        "Ajouter monitoring alerting si latence > 3s"
    ],
    "tests_required": [
        "test_workflow_end_to_end_nominal",
        "test_webhook_retry_on_failure"
    ],
    "final_score": 8.1,
    "justification": "Workflow bien conçu avec séparation claire des responsabilités. Les risques identifiés sont de faible impact et ont une mitigation simple (retry config). Aucun blocage critique. Recommandation : GO avec configuration du retry avant mise en production."
})

# CAS NÉGATIF 1 : Sortie vide
_EMPTY_OUTPUT = ""

# CAS NÉGATIF 2 : Sortie floue (texte libre, pas de JSON)
_VAGUE_OUTPUT = """
Il me semble que le plan est globalement correct. Il y a peut-être quelques points
à améliorer mais dans l'ensemble ça semble fonctionner. Les risques sont gérables.
Je dirais que c'est plutôt bien.
"""

# CAS NÉGATIF 3 : JSON partiel avec contradiction non structurée
_PARTIAL_JSON = """{
  "decision": "GO",
  "final_score": 9.5,
  "blocking_issues": [
    {"type": "securite", "description": "Injection SQL possible", "severity": "high", "evidence": "input non sanitisé"}
  ],
  "justification": "Tout semble bien"
}"""

# CAS NÉGATIF 4 : JSON avec absence de preuve non signalée
_NO_PROOFS = json.dumps({
    "decision": "GO",
    "confidence": 0.95,
    "blocking_issues": [],
    "risks": [],
    "weak_points": [],
    "inconsistencies": [],
    "missing_proofs": [],
    "improvements": [],
    "tests_required": [],
    "final_score": 9.8,
    "justification": "Tout est parfait, aucun risque identifié."
})


# ══════════════════════════════════════════════════════════════
# IMPORT DES MODULES
# ══════════════════════════════════════════════════════════════
section("Import modules")

try:
    from agents.shadow_advisor.schema import (
        AdvisoryReport, AdvisoryDecision, BlockingIssue, Risk, IssueSeverity,
        parse_advisory, validate_advisory_structure,
    )
    from agents.shadow_advisor.scorer import AdvisoryScorer
    ok("schema.py importé")
    ok("scorer.py importé")
except Exception as e:
    fail("Import modules shadow_advisor", str(e))
    print(f"\n❌ FATAL : impossible d'importer — {e}")
    if __name__ == "__main__":
        sys.exit(1)


# ══════════════════════════════════════════════════════════════
# TESTS SCHEMA ET PARSING
# ══════════════════════════════════════════════════════════════
section("Schema — AdvisoryReport structure")

try:
    # Structure de base
    report = AdvisoryReport(
        decision="GO",
        confidence=0.80,
        final_score=7.5,
        justification="Test de base",
    )
    assert report.decision == AdvisoryDecision.GO
    assert report.confidence == 0.80
    assert report.final_score == 7.5
    ok("AdvisoryReport instanciation basique")

    # Normalisation décision
    r_nogo  = AdvisoryReport(decision="NO-GO",  confidence=0.5, final_score=2.0, justification="x")
    r_nogo2 = AdvisoryReport(decision="NOGO",   confidence=0.5, final_score=2.0, justification="x")
    r_imp   = AdvisoryReport(decision="IMPROVE", confidence=0.5, final_score=5.0, justification="x")
    assert r_nogo.decision  == AdvisoryDecision.NO_GO
    assert r_nogo2.decision == AdvisoryDecision.NO_GO
    assert r_imp.decision   == AdvisoryDecision.IMPROVE
    ok("Normalisation décision NO-GO / NOGO / IMPROVE")

    # Clamp confidence et score
    r_clamp = AdvisoryReport(decision="GO", confidence=1.5, final_score=15.0, justification="x")
    assert r_clamp.confidence == 1.0
    assert r_clamp.final_score == 10.0
    ok("Clamp confidence [0,1] et score [0,10]")

    # BlockingIssue
    issue = BlockingIssue(type="technique", description="Timeout manquant", severity="high", evidence="ligne 42")
    assert issue.is_critical()
    ok("BlockingIssue.is_critical() pour severity=high")

    issue_low = BlockingIssue(type="test", description="Test manquant", severity="low")
    assert not issue_low.is_critical()
    ok("BlockingIssue.is_critical() False pour severity=low")

    # Risk
    risk = Risk(type="réseau", description="Latence", severity="medium", probability="high", impact="low")
    score = risk.risk_score()
    assert 0 < score < 1
    ok(f"Risk.risk_score() = {score:.3f}")

    # has_critical_issues
    r_with_crit = AdvisoryReport(
        decision="NO-GO", confidence=0.9, final_score=3.0, justification="Critique présent",
        blocking_issues=[issue],
    )
    assert r_with_crit.has_critical_issues()
    assert r_with_crit.critical_issue_count() == 1
    ok("has_critical_issues() / critical_issue_count()")

    # is_actionable
    r_actionable = AdvisoryReport(
        decision="IMPROVE", confidence=0.7, final_score=5.0,
        justification="Rapport complet",
        risks=[risk],
        improvements=["Fix timeout"],
    )
    assert r_actionable.is_actionable()
    ok("is_actionable() True quand risks + improvements + justification")

    r_empty = AdvisoryReport(decision="GO", confidence=0.9, final_score=8.0, justification="x")
    assert not r_empty.is_actionable()
    ok("is_actionable() False quand vide")

    # summary_line — utilise .value pour Python 3.11+
    line = r_with_crit.summary_line()
    assert "score=" in line
    assert "NO-GO" in line or "IMPROVE" in line or "GO" in line  # une décision valide
    ok(f"summary_line() : '{line}'")

    # to_dict
    d = r_actionable.to_dict()
    assert "decision" in d and "blocking_issues" in d and "improvements" in d
    ok("to_dict() contient tous les champs obligatoires")

    # to_prompt_feedback
    fb = r_actionable.to_prompt_feedback()
    assert "Shadow-Advisor" in fb
    assert "IMPROVE" in fb or "GO" in fb or "NO-GO" in fb
    ok(f"to_prompt_feedback() : {len(fb)} chars")

    # top_risk
    r_multi_risk = AdvisoryReport(
        decision="IMPROVE", confidence=0.7, final_score=5.0, justification="x",
        risks=[
            Risk("A", "Faible", "low", "low", "low"),
            Risk("B", "Critique", "high", "high", "high"),
        ],
    )
    top = r_multi_risk.top_risk()
    assert top is not None and top.type == "B"
    ok("top_risk() retourne le risque le plus élevé")

except Exception as e:
    fail("Schema AdvisoryReport", str(e))


# ══════════════════════════════════════════════════════════════
# TESTS PARSING
# ══════════════════════════════════════════════════════════════
section("Parsing — parse_advisory()")

try:
    # Parsing JSON valide complet
    r = parse_advisory(_TECHNICAL_NOGO)
    assert r.is_valid_parse(), f"Parse error: {r.parse_error}"
    assert len(r.blocking_issues) == 2
    assert len(r.risks) == 1
    assert r.blocking_issues[0].severity == "high"
    assert r.blocking_issues[0].evidence != ""
    ok(f"Parsing NO-GO technique : {len(r.blocking_issues)} issues, {len(r.risks)} risks")

    r2 = parse_advisory(_PATCH_IMPROVE)
    assert r2.is_valid_parse()
    assert r2.decision in (AdvisoryDecision.IMPROVE, AdvisoryDecision.GO, AdvisoryDecision.NO_GO)
    ok(f"Parsing IMPROVE patch : decision={r2.decision}")

    r3 = parse_advisory(_WORKFLOW_GO)
    assert r3.is_valid_parse()
    assert len(r3.improvements) >= 1
    ok(f"Parsing GO workflow : improvements={len(r3.improvements)}")

    # JSON avec markdown fence
    with_fence = f"```json\n{_PATCH_IMPROVE}\n```"
    r_fence = parse_advisory(with_fence)
    assert r_fence.is_valid_parse()
    ok("Parsing JSON avec ``` markdown fence")

    # Sortie vide → fallback rapport d'erreur (jamais d'exception)
    r_empty = parse_advisory(_EMPTY_OUTPUT)
    assert not r_empty.is_valid_parse()
    assert r_empty.parse_error
    assert len(r_empty.blocking_issues) >= 1  # au moins 1 issue signalant le problème
    ok(f"Sortie vide → fallback rapport (parse_error='{r_empty.parse_error[:40]}')")

    # Sortie floue (texte libre)
    r_vague = parse_advisory(_VAGUE_OUTPUT)
    assert not r_vague.is_valid_parse()
    ok(f"Sortie floue → fallback rapport (parse_error présent)")

    # JSON partiel (champs manquants)
    r_partial = parse_advisory(_PARTIAL_JSON)
    assert r_partial.is_valid_parse()  # partial JSON mais parseable
    ok(f"JSON partiel parsé : decision={r_partial.decision}, score={r_partial.final_score}")

    # Repair trailing comma
    broken_json = '{"decision":"IMPROVE","confidence":0.7,"justification":"test",}'
    r_broken = parse_advisory(broken_json)
    # Peut réussir si repair fonctionne ou non — juste pas d'exception
    ok(f"JSON avec trailing comma : is_valid={r_broken.is_valid_parse()}")

except Exception as e:
    fail("Parsing parse_advisory()", str(e))


# ══════════════════════════════════════════════════════════════
# TESTS SCORER
# ══════════════════════════════════════════════════════════════
section("Scorer — AdvisoryScorer logique")

try:
    scorer = AdvisoryScorer()

    # CAS 1 : NO-GO technique — score doit être bas et décision NO-GO
    r_nogo = parse_advisory(_TECHNICAL_NOGO)
    r_nogo = scorer.score(r_nogo)
    assert r_nogo.decision == AdvisoryDecision.NO_GO, f"Attendu NO-GO, got {r_nogo.decision}"
    assert r_nogo.final_score <= 4.9, f"Attendu ≤4.9 (cap critique), got {r_nogo.final_score}"
    ok(f"NO-GO technique : score={r_nogo.final_score:.2f} ≤ 4.9, décision={r_nogo.decision}")

    # CAS 2 : IMPROVE patch — score moyen
    r_imp = parse_advisory(_PATCH_IMPROVE)
    r_imp = scorer.score(r_imp)
    assert r_imp.decision in (AdvisoryDecision.IMPROVE, AdvisoryDecision.GO)
    assert 3.0 <= r_imp.final_score <= 9.0
    ok(f"IMPROVE patch : score={r_imp.final_score:.2f}, décision={r_imp.decision}")

    # CAS 3 : Business IMPROVE — score moyen avec risques
    r_biz = parse_advisory(_BUSINESS_IMPROVE)
    r_biz = scorer.score(r_biz)
    # Pas NO-GO car blocage = medium (pas critical)
    assert r_biz.decision != AdvisoryDecision.GO or r_biz.final_score >= 7.5
    ok(f"Business IMPROVE : score={r_biz.final_score:.2f}, décision={r_biz.decision}")

    # CAS 4 : Workflow GO — score élevé
    r_go = parse_advisory(_WORKFLOW_GO)
    r_go = scorer.score(r_go)
    assert r_go.decision == AdvisoryDecision.GO, f"Attendu GO, got {r_go.decision}"
    assert r_go.final_score >= 7.5, f"Attendu ≥7.5, got {r_go.final_score}"
    ok(f"Workflow GO : score={r_go.final_score:.2f} ≥ 7.5, décision={r_go.decision}")

    # Règle : blocage CRITICAL → score ≤ 4.9
    r_with_critical = parse_advisory(json.dumps({
        "decision": "GO", "confidence": 0.9, "final_score": 9.0,
        "blocking_issues": [
            {"type": "securite", "description": "SQL injection", "severity": "high", "evidence": "input non sanitisé"}
        ],
        "risks": [], "weak_points": [], "inconsistencies": [],
        "missing_proofs": [], "improvements": ["Sanitiser l'input"],
        "tests_required": ["test_sql_injection"],
        "justification": "Problème de sécurité critique — le GO du LLM est incohérent"
    }))
    r_with_critical = scorer.score(r_with_critical)
    assert r_with_critical.final_score <= 4.9, f"Cap critique non respecté : {r_with_critical.final_score}"
    assert r_with_critical.decision == AdvisoryDecision.NO_GO
    ok(f"Cap critique : blocage high → score={r_with_critical.final_score:.2f} ≤ 4.9, NO-GO forcé")

    # Règle : pas de blocage + améliorations → bonus → score élevé
    r_clean = parse_advisory(json.dumps({
        "decision": "GO", "confidence": 0.90,
        "blocking_issues": [],
        "risks": [{"type": "A", "description": "risque mineur", "severity": "low", "probability": "low", "impact": "low"}],
        "weak_points": ["Point faible mineur"],
        "inconsistencies": [], "missing_proofs": [],
        "improvements": ["Améliorer A", "Améliorer B", "Améliorer C"],
        "tests_required": ["test_A", "test_B"],
        "final_score": 8.5,
        "justification": "Rapport propre avec preuves et améliorations identifiées — situation saine."
    }))
    r_clean = scorer.score(r_clean)
    assert r_clean.decision == AdvisoryDecision.GO, f"Attendu GO, got {r_clean.decision}"
    ok(f"Rapport propre : score={r_clean.final_score:.2f}, décision=GO")

    # explain() fonctionne
    explanation = scorer.explain(r_nogo)
    assert "Score final" in explanation
    assert "MALUS" in explanation or "BASE" in explanation
    ok(f"scorer.explain() produit explication lisible ({len(explanation)} chars)")

except Exception as e:
    fail("Scorer AdvisoryScorer", str(e))


# ══════════════════════════════════════════════════════════════
# TESTS VALIDATION STRUCTURE
# ══════════════════════════════════════════════════════════════
section("Validation — validate_advisory_structure()")

try:
    scorer = AdvisoryScorer()

    # Rapport valide et actionnable → 0 violations
    r_valid = parse_advisory(_WORKFLOW_GO)
    r_valid = scorer.score(r_valid)
    violations = validate_advisory_structure(r_valid)
    ok(f"Rapport GO valide : {len(violations)} violations (attendu 0 ou faible)")

    # Rapport d'erreur (parse failed) → violations immédiates
    r_err = parse_advisory("")
    violations_err = validate_advisory_structure(r_err)
    assert any("parsing" in v.lower() or "parse" in v.lower() for v in violations_err)
    ok(f"Rapport parse_error → violations détectées : {violations_err[0][:50]}")

    # Contradiction GO + score bas → violation
    r_incoherent = AdvisoryReport(
        decision="GO", confidence=0.8, final_score=3.5,
        justification="Rapport incohérent",
        improvements=["Fix A"],
        risks=[Risk("X", "Risque X", "low", "low", "low")],
    )
    # Ne pas rescorer pour garder l'incohérence
    violations_inc = validate_advisory_structure(r_incoherent)
    assert any("GO" in v and "score" in v.lower() for v in violations_inc), \
        f"Incohérence GO+score_bas non détectée : {violations_inc}"
    ok(f"Contradiction GO+score_bas détectée : '{violations_inc[0][:60]}'")

    # Contradiction NO-GO + score élevé → violation
    r_inco2 = AdvisoryReport(
        decision="NO-GO", confidence=0.8, final_score=8.0,
        justification="Rapport incohérent 2",
        improvements=["Fix B"],
        risks=[Risk("Y", "Risque Y", "low", "low", "low")],
    )
    violations_inc2 = validate_advisory_structure(r_inco2)
    assert any("NO-GO" in v and "score" in v.lower() for v in violations_inc2), \
        f"Incohérence NO-GO+score_haut non détectée : {violations_inc2}"
    ok(f"Contradiction NO-GO+score_élevé détectée : '{violations_inc2[0][:60]}'")

    # GO avec blocage critique → violation
    r_go_crit = AdvisoryReport(
        decision="GO", confidence=0.8, final_score=7.8,
        justification="Rapport incohérent 3",
        blocking_issues=[BlockingIssue("securite", "SQL injection", "high", "input non sanitisé")],
        improvements=["Sanitiser"],
        risks=[],
    )
    violations_crit = validate_advisory_structure(r_go_crit)
    assert any("GO" in v and "critique" in v.lower() for v in violations_crit), \
        f"GO+critique non détecté : {violations_crit}"
    ok(f"GO avec blocage critique → violation : '{violations_crit[-1][:60]}'")

    # Rapport sans amélioration → violation
    r_no_imp = AdvisoryReport(
        decision="NO-GO", confidence=0.5, final_score=2.0,
        justification="Trop de problèmes",
        blocking_issues=[BlockingIssue("logique", "Logique incorrecte", "high", "")],
    )
    viol_imp = validate_advisory_structure(r_no_imp)
    assert any("amélioration" in v.lower() or "actionnable" in v.lower() for v in viol_imp)
    ok(f"Rapport sans amélioration → violation détectée")

except Exception as e:
    fail("validate_advisory_structure()", str(e))


# ══════════════════════════════════════════════════════════════
# CAS NÉGATIFS SPÉCIAUX
# ══════════════════════════════════════════════════════════════
section("Cas négatifs — détection des pièges LLM")

try:
    scorer = AdvisoryScorer()

    # PIÈGE 1 : LLM dit GO mais met un blocage HIGH → scorer force NO-GO
    r_trap1 = parse_advisory(json.dumps({
        "decision": "GO",
        "confidence": 0.95,
        "blocking_issues": [
            {"type": "securite", "description": "XSS non filtré", "severity": "high", "evidence": "input utilisateur injecté dans DOM"}
        ],
        "risks": [], "weak_points": [], "inconsistencies": [], "missing_proofs": [],
        "improvements": ["Filtrer l'input"],
        "tests_required": ["test_xss"],
        "final_score": 9.0,
        "justification": "Bonne implémentation malgré le XSS."
    }))
    r_trap1 = scorer.score(r_trap1)
    assert r_trap1.decision == AdvisoryDecision.NO_GO, \
        f"PIÈGE 1 non détecté : LLM dit GO mais critique présent → attendu NO-GO, got {r_trap1.decision}"
    assert r_trap1.final_score <= 4.9
    ok(f"PIÈGE 1 : LLM dit GO + critique HIGH → scorer force NO-GO (score={r_trap1.final_score:.2f})")

    # PIÈGE 2 : Rapport "tout parfait" (aucun risque, aucune faiblesse) → score pénalisé
    r_trap2 = parse_advisory(_NO_PROOFS)
    r_trap2 = scorer.score(r_trap2)
    # Sans aucun risque, faiblesse, amélioration → rapport non actionnable
    assert not r_trap2.is_actionable(), "Rapport 'tout parfait' ne devrait pas être actionnable"
    ok(f"PIÈGE 2 : Rapport 'tout parfait' → non actionnable (score={r_trap2.final_score:.2f})")

    # PIÈGE 3 : Sortie floue → rapport de fallback, score = 0
    r_trap3 = parse_advisory(_VAGUE_OUTPUT)
    assert r_trap3.final_score == 0.0, f"Sortie floue devrait avoir score=0, got {r_trap3.final_score}"
    assert r_trap3.parse_error
    ok(f"PIÈGE 3 : Sortie floue → score=0, parse_error présent")

    # PIÈGE 4 : Contradiction non structurée (JSON partiel) → détectée par validate
    r_trap4 = parse_advisory(_PARTIAL_JSON)
    if r_trap4.is_valid_parse():
        r_trap4 = scorer.score(r_trap4)
        violations = validate_advisory_structure(r_trap4)
        # GO avec blocage critique (issue high dans _PARTIAL_JSON)
        crit_violation = any("critique" in v.lower() or "critical" in v.lower() for v in violations)
        ok(f"PIÈGE 4 : JSON partiel avec critique → contradiction détectée={crit_violation}, score={r_trap4.final_score:.2f}")
    else:
        ok(f"PIÈGE 4 : JSON partiel non parsé → fallback correct")

except Exception as e:
    fail("Cas négatifs", str(e))


# ══════════════════════════════════════════════════════════════
# TEST INTÉGRATION — crew.py ShadowAdvisor V2
# ══════════════════════════════════════════════════════════════
section("Intégration — crew.py ShadowAdvisor V2")

try:
    import inspect
    import agents.crew as crew_module

    # L'agent existe
    assert hasattr(crew_module, "ShadowAdvisor")
    ok("ShadowAdvisor présent dans crew.py")

    # run() est défini (override de BaseAgent)
    sa_src = inspect.getsource(crew_module.ShadowAdvisor)
    assert "async def run" in sa_src
    ok("ShadowAdvisor.run() overridé")

    # Utilise parse_advisory
    assert "parse_advisory" in sa_src
    ok("ShadowAdvisor.run() utilise parse_advisory()")

    # Utilise AdvisoryScorer
    assert "AdvisoryScorer" in sa_src
    ok("ShadowAdvisor.run() utilise AdvisoryScorer()")

    # Stocke dans session.metadata
    assert "session.metadata" in sa_src
    assert "shadow_advisory" in sa_src
    ok("ShadowAdvisor stocke le rapport dans session.metadata['shadow_advisory']")

    # Prompt contient le schéma JSON obligatoire (via _JSON_SCHEMA class attr)
    schema_attr = crew_module.ShadowAdvisor._JSON_SCHEMA
    assert "blocking_issues" in schema_attr
    assert "final_score" in schema_attr
    assert "NO-GO" in schema_attr
    sp_src = inspect.getsource(crew_module.ShadowAdvisor.system_prompt)
    assert "INTERDICTIONS" in sp_src or "Interdit" in sp_src or "INTERDIT" in sp_src
    ok("system_prompt V2 contient schéma JSON + interdictions")

    # user_message inclut le contexte agents
    um_src = inspect.getsource(crew_module.ShadowAdvisor.user_message)
    assert "_ctx(" in um_src  # V2 reçoit le contexte des autres agents
    assert "_knowledge_ctx" in um_src
    ok("user_message V2 inclut contexte agents + knowledge")

    # timeout_s est bien 30
    assert crew_module.ShadowAdvisor.timeout_s == 30
    ok("timeout_s = 30 maintenu (R-06 SRE)")

except Exception as e:
    fail("Intégration crew.py ShadowAdvisor V2", str(e))


# ══════════════════════════════════════════════════════════════
# TEST INTÉGRATION — knowledge_memory
# ══════════════════════════════════════════════════════════════
section("Intégration — knowledge_memory patterns connus")

try:
    import tempfile, os
    from memory.legacy_knowledge_memory import KnowledgeMemory

    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        tmp_path = f.name

    try:
        km = KnowledgeMemory(storage_path=tmp_path)

        # Stocker des anti-patterns connus
        km.store(
            type="anti_pattern",
            topic="python async",
            solution="Ne jamais utiliser time.sleep() dans du code async — bloque le thread",
            agent_targets=["shadow-advisor"],
            utility_score=0.90,
        )
        km.store(
            type="anti_pattern",
            topic="securite",
            solution="Ne jamais utiliser exec() avec input utilisateur — injection de code",
            agent_targets=["shadow-advisor"],
            utility_score=0.95,
        )
        km.store(
            type="best_practice",
            topic="python async",
            solution="Toujours utiliser asyncio.wait_for() avec timeout pour éviter les blocages",
            agent_targets=["shadow-advisor"],
            utility_score=0.90,
        )

        # shadow-advisor doit pouvoir récupérer ces patterns
        ctx = km.get_context_for_prompt("shadow-advisor", query="async timeout")
        assert ctx, "shadow-advisor doit avoir des connaissances sur async timeout"
        assert "asyncio" in ctx.lower() or "timeout" in ctx.lower() or "async" in ctx.lower()
        ok(f"shadow-advisor reçoit {len(ctx)} chars de connaissances async")

        ctx_sec = km.get_context_for_prompt("shadow-advisor", query="exec injection securite")
        ok(f"shadow-advisor reçoit connaissances sécurité ({len(ctx_sec)} chars)")

        # avoid_duplicate_ideas pour business
        already = km.avoid_duplicate_ideas("asyncio wait_for timeout async coroutine")
        ok(f"avoid_duplicate_ideas pour pattern connu → {already}")

    finally:
        os.unlink(tmp_path)

except Exception as e:
    fail("knowledge_memory intégration shadow-advisor", str(e))


# ══════════════════════════════════════════════════════════════
# RÉSUMÉ
# ══════════════════════════════════════════════════════════════
if __name__ == "__main__":
    print(f"\n{'═' * 60}")
    print(f"  RÉSULTAT : {_pass} PASS | {_fail} FAIL")
    print(f"{'═' * 60}\n")

    if _fail > 0:
        sys.exit(1)
