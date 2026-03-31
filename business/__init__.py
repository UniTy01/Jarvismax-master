"""
JARVIS BUSINESS LAYER
Extension business sur le Core JarvisMax.

Modules :
    venture     — Venture Builder (analyse d'opportunités)
    offer       — Offer Designer (design d'offre commerciale)
    workflow    — Workflow Architect (architecture de workflows)
    saas        — SaaS Builder (blueprint MVP)
    trade_ops   — Trade Ops (agent IA métier, ex: chauffagiste)
    meta_builder— Meta Builder (clonage de systèmes multi-agents)

Point d'entrée recommandé :
    from business.layer import BusinessLayer, get_business_layer
"""

def get_business_layer(settings):
    from business.layer import BusinessLayer
    return BusinessLayer(settings)

__all__ = ["get_business_layer"]
