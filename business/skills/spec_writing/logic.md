# Technical Spec Writing — Reasoning Structure

## Step 1: Problem Statement
- What problem does this solve? (user pain, not feature request)
- Who is affected? (users, services, operations)
- What is the current behavior vs desired behavior?
- What is the scope? (what is IN and OUT of this spec)
- What are the success criteria? (measurable)
- What is the impact of NOT doing this?

## Step 2: Solution Design
- Describe the high-level approach in 3-5 sentences
- List 2-3 alternatives considered and why they were rejected
- For each architecture decision:
  - What was decided
  - What trade-off was made
  - Under what conditions should this be revisited
- Diagram-worthy: describe component interactions

## Step 3: API Contracts
- For each endpoint:
  - Method + path (e.g., POST /api/v1/resource)
  - Request body schema (fields, types, required/optional)
  - Response schema (success + error cases)
  - Authentication requirements
  - Rate limit considerations
- Use concrete examples, not abstract schemas

## Step 4: Data Model
- List each entity with fields and types
- Define relationships (1:1, 1:N, N:N)
- Identify indexes needed for query patterns
- Storage decision: SQL vs NoSQL vs file with rationale
- Migration strategy if modifying existing data

## Step 5: Edge Cases and Failure Modes
- List at least 5 edge cases
- For each: trigger condition, expected behavior, handling strategy
- Consider: concurrency, timeouts, partial failures, invalid input
- Identify what happens on: network failure, service unavailable, data corruption
- Define degraded mode behavior (what works when something breaks)

## Step 6: Implementation Plan
- Break into 3-5 phases
- Each phase: scope, deliverable, estimated effort, dependencies
- First phase should be shippable independently
- Include testing requirements per phase
- Define rollback strategy for each phase
