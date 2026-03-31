"""
Customer Support Agent Template
=================================
For: small business, ecommerce, service company.

Capabilities: classify messages, answer FAQ, escalate edge cases,
summarize conversations, track unresolved issues.
"""
from business_agents.template_schema import (
    BusinessAgentTemplate, PromptContract, FieldSchema, EvaluationRule, FallbackBehavior,
)

SUPPORT_AGENT_TEMPLATE = BusinessAgentTemplate(
    agent_name="support_agent",
    business_type="general_business",
    purpose="Handle customer support inquiries with classification, FAQ, and escalation",
    version="1.0.0",
    category="support",

    allowed_capabilities=[
        "classify_message",
        "answer_faq",
        "escalate_edge_case",
        "summarize_conversation",
        "track_unresolved",
        "suggest_resolution",
    ],

    preferred_models=[
        "openai/gpt-4o-mini",
        "anthropic/claude-sonnet-4.6",
    ],

    required_tools=[
        "structured_intake",
        "markdown_generator",
        "file_read",
        "file_write",
        "crm_store",
    ],

    memory_scopes=[
        "client_context_memory",
        "reusable_response_memory",
        "agent_local_memory",
    ],

    risk_profile="low",

    system_prompt=PromptContract(
        role="system",
        version="1.0.0",
        variables=["business_name", "business_type", "support_hours", "escalation_email"],
        content="""You are a customer support agent for {{business_name}} ({{business_type}}).

Your job is to help customers quickly and professionally.

WORKFLOW:
1. CLASSIFY the incoming message into a category:
   - billing, shipping, product_info, technical, complaint, feedback, returns, other
2. CHECK if this matches a known FAQ answer
3. If you can answer → provide a clear, helpful response
4. If you cannot answer or it's complex → ESCALATE with a summary
5. Always track whether the issue is RESOLVED or UNRESOLVED

RULES:
- Be empathetic and professional
- Never make promises about refunds/compensation without escalation
- Never share internal system details with customers
- If the customer is angry, acknowledge their frustration first
- Keep responses concise but complete
- Support hours: {{support_hours}}
- Escalation contact: {{escalation_email}}

OUTPUT FORMAT: Structured JSON with:
- classification: message category
- confidence: 0-1 how confident in classification
- response: the response to send to the customer
- resolved: true/false
- escalation: null or {reason, priority, summary}
- conversation_summary: brief summary of the interaction""",
    ),

    user_prompt_template="Customer message for {{business_name}}:\n\n{{customer_message}}\n\nConversation history:\n{{conversation_history}}",

    input_schema=[
        FieldSchema(name="customer_message", type="string", required=True,
                    description="The customer's support message"),
        FieldSchema(name="customer_name", type="string", required=False),
        FieldSchema(name="customer_id", type="string", required=False),
        FieldSchema(name="conversation_history", type="string", required=False,
                    description="Previous messages in this conversation", default=""),
        FieldSchema(name="order_id", type="string", required=False),
    ],

    output_schema=[
        FieldSchema(name="classification", type="string", required=True,
                    description="Message category"),
        FieldSchema(name="confidence", type="number", required=True,
                    description="Classification confidence 0-1"),
        FieldSchema(name="response", type="string", required=True,
                    description="Response to send to customer"),
        FieldSchema(name="resolved", type="boolean", required=True,
                    description="Whether the issue is resolved"),
        FieldSchema(name="escalation", type="object", required=False,
                    description="Escalation details if needed"),
        FieldSchema(name="conversation_summary", type="string", required=True,
                    description="Brief summary of the interaction"),
    ],

    evaluation_rules=[
        EvaluationRule(name="has_classification",
                       description="Output includes message classification",
                       check_type="presence", target_field="classification"),
        EvaluationRule(name="has_response",
                       description="Output includes a customer response",
                       check_type="presence", target_field="response"),
        EvaluationRule(name="has_resolution_status",
                       description="Output includes resolved status",
                       check_type="presence", target_field="resolved"),
        EvaluationRule(name="response_length",
                       description="Response is meaningful (>30 chars)",
                       check_type="length", target_field="response", threshold=30),
        EvaluationRule(name="has_summary",
                       description="Includes conversation summary",
                       check_type="presence", target_field="conversation_summary"),
        EvaluationRule(name="valid_classification",
                       description="Classification is from known categories",
                       check_type="keyword", target_field="classification"),
    ],

    fallback=FallbackBehavior(
        strategy="escalate",
        max_retries=1,
        default_response="Thank you for reaching out. I'm connecting you with a team member "
                         "who can help with your specific question. You'll hear back within "
                         "{{support_hours}}.",
        escalation_target="human",
    ),
)
