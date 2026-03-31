#!/usr/bin/env python3
"""
night_worker.py — batch nocturne pour Knowledge Expansion
Exécution: python scripts/night_worker.py
Ne tourne que si USE_KNOWLEDGE_EXPANSION=true
"""
import os, json, pathlib, logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [night_worker] %(levelname)s %(message)s")
logger = logging.getLogger("night_worker")

USE_KE = os.getenv("USE_KNOWLEDGE_EXPANSION", "false").lower() == "true"
if not USE_KE:
    logger.info("USE_KNOWLEDGE_EXPANSION=false — night_worker idle, nothing to do")
    raise SystemExit(0)

entries_path = pathlib.Path("workspace/knowledge_expansion/entries.json")
if not entries_path.exists():
    logger.info("No entries file found — nothing to process")
    raise SystemExit(0)

try:
    entries = json.loads(entries_path.read_text())
    original_count = len(entries)
    logger.info(f"Loaded {original_count} entries")
except Exception as e:
    logger.warning(f"Could not load entries: {e}")
    raise SystemExit(1)

try:
    from core.knowledge_expansion.knowledge_ttl_policy import cleanup_expired
    entries = cleanup_expired(entries)
    logger.info(f"After TTL cleanup: {len(entries)} entries (removed {original_count - len(entries)})")
except Exception as e:
    logger.warning(f"TTL cleanup fail-open: {e}")

try:
    from core.knowledge_expansion.knowledge_dedup_engine import run_dedup
    before = len(entries)
    entries = run_dedup(entries)
    logger.info(f"After dedup: {len(entries)} entries (merged {before - len(entries)} duplicates)")
except Exception as e:
    logger.warning(f"Dedup fail-open: {e}")

try:
    from core.knowledge_expansion.memory_compressor import should_compress, run_compression
    from core.knowledge_expansion.knowledge_value_scorer import KnowledgeValueScorer
    if should_compress(entries):
        before = len(entries)
        scorer = KnowledgeValueScorer()
        entries = run_compression(entries, scorer)
        logger.info(f"After compression: {len(entries)} entries (removed {before - len(entries)} low-value)")
    else:
        logger.info("No compression needed")
except Exception as e:
    logger.warning(f"Compression fail-open: {e}")

try:
    tmp = entries_path.with_suffix(".tmp")
    tmp.write_text(json.dumps(entries, ensure_ascii=False, indent=2))
    tmp.replace(entries_path)
    logger.info(f"Saved {len(entries)} entries to {entries_path}")
except Exception as e:
    logger.warning(f"Could not save entries: {e}")
