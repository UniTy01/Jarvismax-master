"""business.saas — SaaS Builder module."""
from business.saas.schema import SaasFeature, SaasPage, TechStack, SaasBlueprint, SaasReport, parse_saas_report

def get_agent(settings):
    from business.saas.agent import SaasBuilderAgent
    return SaasBuilderAgent(settings)

__all__ = [
    "get_agent",
    "SaasFeature",
    "SaasPage",
    "TechStack",
    "SaasBlueprint",
    "SaasReport",
    "parse_saas_report",
]
