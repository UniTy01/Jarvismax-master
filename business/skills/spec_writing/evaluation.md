# Technical Spec Writing — Quality Criteria

## Completeness
- Problem statement includes scope, affected users, and success criteria
- Solution design has approach, rejected alternatives, and trade-off decisions
- At least 3 API endpoints with request/response schemas
- Data model with entities, relationships, and indexes
- At least 5 edge cases with handling strategies
- Phased implementation plan with effort estimates

## Structure
- API contracts are concrete (not abstract schemas)
- Data model includes types and storage decisions
- Implementation phases are independently shippable
- Edge cases include trigger condition + handling

## Coherence
- Solution design addresses the problem statement directly
- API contracts match the data model
- Edge cases relate to the specific system (not generic)
- Implementation plan phases build logically on each other

## Red Flags
- Solution without alternatives considered
- API with no error handling
- No edge cases (unrealistic optimism)
- Implementation plan with no effort estimates
- Success criteria not measurable
