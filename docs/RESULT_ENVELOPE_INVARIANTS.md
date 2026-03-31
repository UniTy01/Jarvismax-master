# Result Envelope Invariants — ENFORCED 🔒

## Core Rule

> `final_output` = human-readable markdown ONLY.
> `result_envelope` = structured machine-readable JSON ONLY.
> These are NEVER mixed.

## FinalOutput Required Fields

Every `result_envelope` (via `FinalOutput.to_dict()`) MUST contain:

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| mission_id | string | YES | Non-empty |
| trace_id | string | YES | `tr-{12hex}` format |
| status | string | YES | One of: COMPLETED, FAILED, CANCELLED |
| summary | string | YES | May be empty |
| agent_outputs | list | YES | May be empty list |
| decision_trace | list | YES | May be empty list |
| metrics | dict | YES | May have null values |

## Canonical Statuses (PUBLIC)

Only these statuses appear in public output:

| Status | Meaning |
|--------|---------|
| COMPLETED | Mission finished successfully |
| FAILED | Mission failed (agent error, blocked, timeout) |
| CANCELLED | Mission cancelled (rejected, user-cancelled) |

## Legacy → Canonical Mapping (INTERNAL ONLY)

| Legacy | Canonical |
|--------|-----------|
| DONE | COMPLETED |
| EXECUTED | COMPLETED |
| REJECTED | CANCELLED |
| BLOCKED | FAILED |

## Failure States

Failure states MUST still return a valid envelope:
- `status`: FAILED or CANCELLED
- `agent_outputs`: list of agent results (may include ERROR status agents)
- `summary`: describes what went wrong
- `metrics`: includes duration even for failures

## Forbidden

- ❌ Raw truncated JSON in `final_output`
- ❌ Non-canonical status in public `result_envelope`
- ❌ Missing `trace_id` in envelope
- ❌ `null` for `agent_outputs` (must be empty list)
- ❌ `null` for `metrics` (must be empty dict)

## Test Coverage

| Test | File |
|------|------|
| test_required_fields_exist | test_result_invariants.py |
| test_agent_outputs_is_list | test_result_invariants.py |
| test_metrics_is_dict | test_result_invariants.py |
| test_aggregate_status_mapping | test_result_invariants.py |
| test_to_dict_is_json_serializable | test_result_invariants.py |
| test_final_output_trace_id_in_dict | test_trace_invariants.py |
