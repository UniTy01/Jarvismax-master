# Surgical Fix Pass Report

## Fix applied: Risk keyword overmatch

### Before
_RISK_KW_SYSTEM = {'docker', 'container', 'restart', 'deploy', 'config', 'service', 'daemon', 'systemctl'}

### After
_RISK_KW_SYSTEM = {'docker', 'container', 'restart', 'deploy', 'systemctl', 'daemon'}

### Removed keywords
- 'service': too broad — matches business service offers, not system services
- 'config': too broad — matches business configuration discussions

### Impact
- Business missions: score dropped from 7 (BLOCKED) to 4 (MEDIUM, passes with approval)
- Destructive operations: unchanged (delete/drop still +4)
- System operations: docker/restart/systemctl still flagged (+3)

### Verification
- 2 previously BLOCKED missions resubmitted → both DONE ✅
- 10/10 total missions completed successfully
