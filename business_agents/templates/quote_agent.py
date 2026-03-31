"""
Quote / Estimate Agent Template
=================================
For: plumber, electrician, HVAC, general service business.

Capabilities: intake requests, ask missing questions, generate quote draft,
summarize customer need, suggest next action, prepare email reply.
"""
from business_agents.template_schema import (
    BusinessAgentTemplate, PromptContract, FieldSchema, EvaluationRule, FallbackBehavior,
)

QUOTE_AGENT_TEMPLATE = BusinessAgentTemplate(
    agent_name="quote_agent",
    business_type="service_business",
    purpose="Generate professional quotes and estimates from customer requests",
    version="1.0.0",
    category="quote",

    allowed_capabilities=[
        "intake_request",
        "ask_clarifying_questions",
        "generate_quote_draft",
        "summarize_customer_need",
        "suggest_next_action",
        "prepare_email_reply",
    ],

    preferred_models=[
        "anthropic/claude-sonnet-4.6",
        "openai/gpt-4o-mini",
    ],

    required_tools=[
        "structured_intake",
        "markdown_generator",
        "email_draft",
        "file_write",
    ],

    memory_scopes=[
        "client_context_memory",
        "business_profile_memory",
        "reusable_response_memory",
    ],

    risk_profile="medium",

    system_prompt=PromptContract(
        role="system",
        version="1.0.0",
        variables=["business_name", "business_type", "service_area", "currency"],
        content="""You are a professional quoting assistant for {{business_name}}, a {{business_type}} company.

Your job is to help create accurate, professional quotes for customers.

RULES:
1. Always ask for missing information before generating a quote
2. Be professional but friendly
3. Use {{currency}} for all prices
4. Include labor, materials, and any applicable taxes
5. Add a validity period (default 30 days)
6. Include terms and conditions summary
7. Suggest next steps for the customer

REQUIRED INFORMATION for a quote:
- Customer name and contact
- Service/work description
- Location/address
- Urgency (standard/urgent/emergency)
- Any special requirements or constraints

If any required information is missing, ask for it before generating the quote.

OUTPUT FORMAT: Structured JSON with the following sections:
- customer_summary: brief description of what the customer needs
- clarifying_questions: list of questions if info is missing (empty if complete)
- quote: the actual quote with line items, subtotal, tax, total
- next_actions: suggested next steps
- email_draft: optional professional email to send to customer""",
    ),

    user_prompt_template="Customer request for {{business_name}}:\n\n{{customer_message}}",

    input_schema=[
        FieldSchema(name="customer_message", type="string", required=True,
                    description="The customer's request or inquiry"),
        FieldSchema(name="customer_name", type="string", required=False,
                    description="Customer name if known"),
        FieldSchema(name="customer_email", type="string", required=False,
                    description="Customer email if known"),
        FieldSchema(name="urgency", type="string", required=False,
                    description="standard, urgent, or emergency", default="standard"),
        FieldSchema(name="business_context", type="object", required=False,
                    description="Business profile and pricing context"),
    ],

    output_schema=[
        FieldSchema(name="customer_summary", type="string", required=True,
                    description="Brief summary of customer need"),
        FieldSchema(name="clarifying_questions", type="list", required=True,
                    description="Questions to ask if information is missing"),
        FieldSchema(name="quote", type="object", required=False,
                    description="Quote with line_items, subtotal, tax, total"),
        FieldSchema(name="next_actions", type="list", required=True,
                    description="Suggested next steps"),
        FieldSchema(name="email_draft", type="string", required=False,
                    description="Professional email draft for the customer"),
    ],

    evaluation_rules=[
        EvaluationRule(name="has_summary", description="Output includes customer summary",
                       check_type="presence", target_field="customer_summary"),
        EvaluationRule(name="has_questions_or_quote",
                       description="Output includes either clarifying questions or a quote",
                       check_type="presence", target_field="clarifying_questions"),
        EvaluationRule(name="has_next_actions", description="Output includes next actions",
                       check_type="presence", target_field="next_actions"),
        EvaluationRule(name="summary_length", description="Summary is meaningful (>20 chars)",
                       check_type="length", target_field="customer_summary", threshold=20),
        EvaluationRule(name="professional_tone",
                       description="No informal language, slang, or emoji in quote",
                       check_type="keyword", target_field="email_draft"),
    ],

    fallback=FallbackBehavior(
        strategy="partial",
        max_retries=2,
        default_response="I need more information to generate an accurate quote. "
                         "Please provide: the service needed, location, and any urgency level.",
        escalation_target="human",
    ),
)
