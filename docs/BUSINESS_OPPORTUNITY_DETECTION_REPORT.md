# Business Opportunity Detection

## Module: core/skills/business_reasoning.py

### Detection approach
- Keyword-based business intent detection (is_business_mission())
- Mission classifier BUSINESS task type (new)
- 6 opportunity types: automation, content, analysis, micro_saas, productized, document_generation

### Avoids high-risk domains
Explicit blocklist: financial advisory, medical advice, legal advice, gambling, crypto trading, etc.

### Prioritizes
- Simple automation, content creation, analysis services
- Low complexity, fast validation, clear value proposition
