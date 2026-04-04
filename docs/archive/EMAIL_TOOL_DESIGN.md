# Email Tool Design — First External Tool Candidate

## Status: DESIGNED (not yet implemented)

---

## Why Email?

| Criteria | Score | Reason |
|----------|-------|--------|
| Safety | ✅ HIGH | Send-only, no shell access, no filesystem |
| Usefulness | ✅ HIGH | Business missions need to send reports |
| Risk | ✅ LOW | SMTP is well-understood, rate-limited by provider |
| Reversibility | ⚠️ MEDIUM | Can't unsend, but damage is limited |
| Complexity | ✅ LOW | SMTP library, ~50 lines |
| v1 Compliance | ✅ | Uses JarvisError, capability schema, policy check |

## Capability Schema

```python
Capability(
    name="email_send",
    risk_level="MEDIUM",        # Not LOW — sends external content
    description="Send email via SMTP",
    requires_approval=True,     # Always require approval before sending
    allowed_agents=["*"],       # Any agent can request
)
```

## Tool Interface

```python
class EmailTool(BaseTool):
    name = "email_send"
    risk_level = "MEDIUM"
    description = "Send email via configured SMTP server"
    timeout_seconds = 15.0

    def execute(self, to: str, subject: str, body: str, **kw) -> ToolResult:
        # 1. Validate inputs
        # 2. Check policy engine (cost, approval)
        # 3. Send via SMTP
        # 4. Return ToolResult
```

## Configuration (.env)

```
JARVIS_SMTP_HOST=smtp.gmail.com
JARVIS_SMTP_PORT=587
JARVIS_SMTP_USER=jarvis@yourdomain.com
JARVIS_SMTP_PASSWORD=app-specific-password
JARVIS_SMTP_FROM=Jarvis <jarvis@yourdomain.com>
```

## Safety Measures

1. **Always requires approval** — no auto-send
2. **Rate limit** — max 10 emails per hour
3. **Body size limit** — max 10KB
4. **Recipient validation** — configurable allowlist
5. **PolicyEngine check** — scored as MEDIUM risk
6. **JarvisError on failure** — standardized errors
7. **Idempotency key** — prevents duplicate sends

## NOT Implemented Yet

This is a design document. Implementation requires:
1. SMTP credentials configured in .env
2. User approval of the design
3. Integration tests

## Integration Points

```
MetaOrchestrator → CanonicalAction(tool_name="email_send")
  → PolicyEngine.evaluate() → MEDIUM risk, requires approval
  → CapabilityRegistry.check_permission() → allowed
  → tool_executor.execute("email_send", {to, subject, body})
  → EmailTool.safe_execute() → ToolResult
  → CircuitBreaker.record_success/failure()
  → EventCollector.emit("tool", "tool_call", {tool: "email_send"})
```
