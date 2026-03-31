# Output Standardization

## Standard outputs
- **Business**: BusinessOpportunity.to_dict() / .to_markdown()
- **General**: output_formatter removes LLM noise
- **Traces**: DecisionTrace.human_summary() for readability
- **JSON**: try_extract_json() from markdown blocks

## Flutter-ready
- All outputs serializable as JSON
- Traces have both structured (summary()) and human (human_summary()) formats
- Mission states use canonical MissionStatus enum
