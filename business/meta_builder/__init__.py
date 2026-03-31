"""business.meta_builder — Meta Builder module."""
from business.meta_builder.schema import AgentCloneSpec, MetaBuildPlan, parse_meta_build_plan

def get_agent(settings):
    from business.meta_builder.agent import MetaBuilderAgent
    return MetaBuilderAgent(settings)

__all__ = [
    "get_agent",
    "AgentCloneSpec",
    "MetaBuildPlan",
    "parse_meta_build_plan",
]
