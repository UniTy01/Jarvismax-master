"""business.workflow — Workflow Architect module."""
from business.workflow.schema import WorkflowStep, BusinessWorkflow, WorkflowReport, parse_workflow_report

def get_agent(settings):
    from business.workflow.agent import WorkflowArchitectAgent
    return WorkflowArchitectAgent(settings)

__all__ = [
    "get_agent",
    "WorkflowStep",
    "BusinessWorkflow",
    "WorkflowReport",
    "parse_workflow_report",
]
