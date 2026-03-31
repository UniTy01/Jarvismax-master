"""business.offer — Offer Designer module."""
from business.offer.schema import PricingTier, OfferDesign, OfferReport, parse_offer_report

def get_agent(settings):
    from business.offer.agent import OfferDesignerAgent
    return OfferDesignerAgent(settings)

__all__ = [
    "get_agent",
    "PricingTier",
    "OfferDesign",
    "OfferReport",
    "parse_offer_report",
]
