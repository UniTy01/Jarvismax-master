# Business Feasibility Scoring

## estimate_feasibility() → FeasibilityScore

### 7 factors (each 0-1)
- complexity, estimated_demand, competition
- implementation_effort, time_to_first_result
- legal_simplicity, required_cost

### Overall score formula
(1-complexity)*0.2 + demand*0.25 + (1-competition)*0.1 + (1-effort)*0.15 + (1-time)*0.1 + (1-legal)*0.1 + (1-cost)*0.1

### Results by type
- Automation service: ~0.70 (fast, low cost, high demand)
- Content service: ~0.73 (very fast, very low cost)
- Analysis service: ~0.64 (moderate complexity)
- Micro SaaS: ~0.49 (high effort, slower)
