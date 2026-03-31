"""
Content / Product Agent Template
===================================
For: ecommerce, CBD business, local business, SaaS.

Capabilities: product pages, FAQ, SEO content, technical summaries,
social post drafts.
"""
from business_agents.template_schema import (
    BusinessAgentTemplate, PromptContract, FieldSchema, EvaluationRule, FallbackBehavior,
)

CONTENT_AGENT_TEMPLATE = BusinessAgentTemplate(
    agent_name="content_agent",
    business_type="ecommerce",
    purpose="Generate product pages, FAQ, SEO content, and social media drafts",
    version="1.0.0",
    category="content",

    allowed_capabilities=[
        "generate_product_page",
        "generate_faq",
        "generate_seo_content",
        "generate_technical_summary",
        "generate_social_post",
        "generate_email_campaign",
    ],

    preferred_models=[
        "anthropic/claude-sonnet-4.6",
        "openai/gpt-4o-mini",
    ],

    required_tools=[
        "markdown_generator",
        "html_generator",
        "file_write",
        "web_research",
    ],

    memory_scopes=[
        "business_profile_memory",
        "reusable_response_memory",
        "agent_local_memory",
    ],

    risk_profile="low",

    system_prompt=PromptContract(
        role="system",
        version="1.0.0",
        variables=["business_name", "business_type", "brand_voice", "target_audience"],
        content="""You are a content generation specialist for {{business_name}} ({{business_type}}).

Your job is to create high-quality, conversion-focused content.

BRAND VOICE: {{brand_voice}}
TARGET AUDIENCE: {{target_audience}}

CONTENT TYPES you can generate:
1. PRODUCT PAGE: title, description, features, benefits, specs, CTA
2. FAQ: question-answer pairs, organized by category
3. SEO CONTENT: keyword-optimized articles with meta description
4. TECHNICAL SUMMARY: clear explanation of product/service capabilities
5. SOCIAL POST: platform-specific (Instagram, LinkedIn, Twitter/X, Facebook)

RULES:
- Match the brand voice consistently
- Never make medical/health claims unless explicitly provided
- Include SEO keywords naturally (no keyword stuffing)
- Social posts must respect platform character limits
- All content must be original (no copying)
- Use benefit-focused language over feature-focused
- Include clear calls to action

OUTPUT FORMAT: Structured JSON with:
- content_type: which type was generated
- title: content title/headline
- body: the main content (markdown format)
- meta: {description, keywords, word_count}
- variants: optional alternative versions
- social_posts: platform-specific versions if requested""",
    ),

    user_prompt_template="Generate {{content_type}} content for {{business_name}}:\n\n{{content_brief}}",

    input_schema=[
        FieldSchema(name="content_type", type="string", required=True,
                    description="product_page, faq, seo_article, technical_summary, social_post"),
        FieldSchema(name="content_brief", type="string", required=True,
                    description="What the content should be about"),
        FieldSchema(name="product_name", type="string", required=False),
        FieldSchema(name="product_details", type="object", required=False,
                    description="Product specs, features, pricing"),
        FieldSchema(name="target_keywords", type="list", required=False,
                    description="SEO keywords to target"),
        FieldSchema(name="platform", type="string", required=False,
                    description="Social platform: instagram, linkedin, twitter, facebook"),
        FieldSchema(name="tone", type="string", required=False,
                    description="Override brand voice for this piece", default=""),
    ],

    output_schema=[
        FieldSchema(name="content_type", type="string", required=True),
        FieldSchema(name="title", type="string", required=True,
                    description="Content title or headline"),
        FieldSchema(name="body", type="string", required=True,
                    description="Main content body in markdown"),
        FieldSchema(name="meta", type="object", required=True,
                    description="{description, keywords, word_count}"),
        FieldSchema(name="variants", type="list", required=False,
                    description="Alternative versions"),
        FieldSchema(name="social_posts", type="object", required=False,
                    description="Platform-specific social post versions"),
    ],

    evaluation_rules=[
        EvaluationRule(name="has_title", description="Output includes a title",
                       check_type="presence", target_field="title"),
        EvaluationRule(name="has_body", description="Output includes body content",
                       check_type="presence", target_field="body"),
        EvaluationRule(name="body_length", description="Body is substantial (>100 chars)",
                       check_type="length", target_field="body", threshold=100),
        EvaluationRule(name="has_meta", description="Output includes metadata",
                       check_type="presence", target_field="meta"),
        EvaluationRule(name="has_content_type", description="Output declares content type",
                       check_type="presence", target_field="content_type"),
    ],

    fallback=FallbackBehavior(
        strategy="partial",
        max_retries=2,
        default_response="I need more details to generate quality content. "
                         "Please provide: the content type (product page, FAQ, SEO article, "
                         "social post), and a brief description of what to write about.",
        escalation_target="human",
    ),
)
