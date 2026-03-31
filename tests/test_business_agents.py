"""
Tests — Business Agent Factory (Full Validation)

Phase 1: Template System
  B1. Templates load and validate
  B2. All 3 templates pass validation
  B3. Template registry lists all templates
  B4. Template schema fields are correct

Phase 2: Agent Factory
  B5. Create quote agent for heating company
  B6. Create support agent for small business
  B7. Create content agent for CBD ecommerce
  B8. Generated agents have correct structure
  B9. Factory persists and reloads agents

Phase 3: Tool Bindings
  B10. Structured intake tool works
  B11. Markdown generator works
  B12. Email draft tool works
  B13. CRM store tool works
  B14. Quote formatter works
  B15. Tool registry lists all tools

Phase 4: Business Memory
  B16. Store and retrieve memory
  B17. Memory scopes are bounded
  B18. Memory TTL expiry works
  B19. Memory search works
  B20. Per-agent isolation

Phase 5: Test Harness
  B21. Test battery generated for each template
  B22. Test suite runs on quote agent
  B23. Test suite runs on support agent
  B24. Test suite runs on content agent
  B25. Valid input passes, missing input fails

Phase 6: Self-Improvement
  B26. Performance tracking works
  B27. Improvement candidates detected
  B28. Suggestions generated

Phase 7: Registry
  B29. Agent registry populates
  B30. Registry summary has correct structure

Phase 8: End-to-end validation
  B31. Heating quote agent full lifecycle
  B32. Small business support agent full lifecycle
  B33. CBD content agent full lifecycle
"""
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


# ═══════════════════════════════════════════════════════════════
# PHASE 1: TEMPLATE SYSTEM
# ═══════════════════════════════════════════════════════════════

class TestTemplateSystem:

    def test_templates_load(self):
        """B1: Templates import without error."""
        from business_agents.templates.quote_agent import QUOTE_AGENT_TEMPLATE
        from business_agents.templates.support_agent import SUPPORT_AGENT_TEMPLATE
        from business_agents.templates.content_agent import CONTENT_AGENT_TEMPLATE
        assert QUOTE_AGENT_TEMPLATE.agent_name == "quote_agent"
        assert SUPPORT_AGENT_TEMPLATE.agent_name == "support_agent"
        assert CONTENT_AGENT_TEMPLATE.agent_name == "content_agent"

    def test_templates_validate(self):
        """B2: All 3 templates pass validation."""
        from business_agents.templates.quote_agent import QUOTE_AGENT_TEMPLATE
        from business_agents.templates.support_agent import SUPPORT_AGENT_TEMPLATE
        from business_agents.templates.content_agent import CONTENT_AGENT_TEMPLATE
        assert QUOTE_AGENT_TEMPLATE.validate() == []
        assert SUPPORT_AGENT_TEMPLATE.validate() == []
        assert CONTENT_AGENT_TEMPLATE.validate() == []

    def test_registry_lists_all(self):
        """B3: Template registry has all 3 templates."""
        from business_agents.template_registry import list_templates
        templates = list_templates()
        names = [t["name"] for t in templates]
        assert "quote_agent" in names
        assert "support_agent" in names
        assert "content_agent" in names

    def test_template_fields(self):
        """B4: Templates have required fields."""
        from business_agents.templates.quote_agent import QUOTE_AGENT_TEMPLATE as t
        assert len(t.allowed_capabilities) > 0
        assert len(t.required_tools) > 0
        assert len(t.input_schema) > 0
        assert len(t.output_schema) > 0
        assert len(t.evaluation_rules) > 0
        assert t.system_prompt.content != ""
        assert t.risk_profile in ("low", "medium", "high", "critical")


# ═══════════════════════════════════════════════════════════════
# PHASE 2: AGENT FACTORY
# ═══════════════════════════════════════════════════════════════

class TestAgentFactory:

    def test_create_quote_agent(self, tmp_path):
        """B5: Create quote agent for heating company."""
        from business_agents.factory import AgentFactory
        factory = AgentFactory(persist_dir=tmp_path / "agents")
        agent = factory.create("quote_agent", {
            "business_name": "Smith Heating Ltd",
            "business_type": "HVAC",
            "service_area": "London",
            "currency": "GBP",
        })
        assert agent.id.startswith("ba-quote_agent-")
        assert agent.business_name == "Smith Heating Ltd"
        assert "GBP" in agent.system_prompt
        assert "HVAC" in agent.system_prompt

    def test_create_support_agent(self, tmp_path):
        """B6: Create support agent for small business."""
        from business_agents.factory import AgentFactory
        factory = AgentFactory(persist_dir=tmp_path / "agents")
        agent = factory.create("support_agent", {
            "business_name": "TechFix Solutions",
            "business_type": "IT Support",
            "support_hours": "Mon-Fri 9-17",
            "escalation_email": "support@techfix.com",
        })
        assert agent.id.startswith("ba-support_agent-")
        assert "TechFix Solutions" in agent.system_prompt
        assert "Mon-Fri 9-17" in agent.system_prompt

    def test_create_content_agent(self, tmp_path):
        """B7: Create content agent for CBD ecommerce."""
        from business_agents.factory import AgentFactory
        factory = AgentFactory(persist_dir=tmp_path / "agents")
        agent = factory.create("content_agent", {
            "business_name": "Green Leaf CBD",
            "business_type": "ecommerce",
            "brand_voice": "Professional, wellness-focused, trustworthy",
            "target_audience": "Health-conscious adults 25-55",
        })
        assert agent.id.startswith("ba-content_agent-")
        assert "Green Leaf CBD" in agent.system_prompt
        assert "wellness" in agent.system_prompt

    def test_generated_structure(self, tmp_path):
        """B8: Generated agents have correct structure."""
        from business_agents.factory import AgentFactory
        factory = AgentFactory(persist_dir=tmp_path / "agents")
        agent = factory.create("quote_agent", {"business_name": "Test Co"})
        d = agent.to_dict()
        assert "id" in d
        assert "template" in d
        assert "capabilities" in d
        assert "tools" in d
        assert "memory_config" in d
        assert d["status"] == "created"

    def test_persistence(self, tmp_path):
        """B9: Factory persists and reloads agents."""
        from business_agents.factory import AgentFactory
        f1 = AgentFactory(persist_dir=tmp_path / "agents")
        agent = f1.create("quote_agent", {"business_name": "Persist Test"})
        agent_id = agent.id

        f2 = AgentFactory(persist_dir=tmp_path / "agents")
        reloaded = f2.get(agent_id)
        assert reloaded is not None
        assert reloaded.business_name == "Persist Test"


# ═══════════════════════════════════════════════════════════════
# PHASE 3: TOOL BINDINGS
# ═══════════════════════════════════════════════════════════════

class TestToolBindings:

    def test_structured_intake(self):
        """B10: Structured intake tool works."""
        from business_agents.tools.business_tools import execute_tool
        result = execute_tool("structured_intake",
                              raw_input="I need a boiler repair at 123 Main St",
                              schema=[{"name": "service", "required": True},
                                      {"name": "address", "required": True}])
        assert result.success
        assert "parsed" in result.data

    def test_markdown_generator(self):
        """B11: Markdown generator works."""
        from business_agents.tools.business_tools import execute_tool
        result = execute_tool("markdown_generator",
                              title="Test Quote",
                              sections=[{"heading": "Summary", "content": "Test content"}])
        assert result.success
        assert "# Test Quote" in result.data["markdown"]

    def test_email_draft(self):
        """B12: Email draft tool works."""
        from business_agents.tools.business_tools import execute_tool
        result = execute_tool("email_draft",
                              to="customer@test.com",
                              subject="Your Quote",
                              body="Please find your quote attached.")
        assert result.success
        assert result.data["status"] == "draft"
        assert result.data["subject"] == "Your Quote"

    def test_crm_store(self, tmp_path):
        """B13: CRM store tool works."""
        from business_agents.tools.business_tools import CRMStoreTool
        crm = CRMStoreTool(storage_dir=tmp_path / "crm")
        result = crm.execute(action="store", record_type="customer",
                             record_id="c1", data={"name": "John", "email": "j@t.com"})
        assert result.success

        result2 = crm.execute(action="retrieve", record_type="customer", record_id="c1")
        assert result2.success
        assert result2.data["data"]["name"] == "John"

    def test_quote_formatter(self):
        """B14: Quote formatter works."""
        from business_agents.tools.business_tools import execute_tool
        result = execute_tool("quote_formatter",
                              customer_name="John Smith",
                              line_items=[
                                  {"description": "Boiler repair", "amount": 250},
                                  {"description": "Parts", "amount": 80},
                              ],
                              currency="GBP", tax_rate=0.20)
        assert result.success
        assert result.data["subtotal"] == 330
        assert result.data["tax_amount"] == 66.0
        assert result.data["total"] == 396.0
        assert result.data["currency"] == "GBP"

    def test_tool_registry(self):
        """B15: Tool registry lists all tools."""
        from business_agents.tools.business_tools import list_business_tools
        tools = list_business_tools()
        names = [t["name"] for t in tools]
        assert "structured_intake" in names
        assert "markdown_generator" in names
        assert "email_draft" in names
        assert "crm_store" in names
        assert "quote_formatter" in names


# ═══════════════════════════════════════════════════════════════
# PHASE 4: BUSINESS MEMORY
# ═══════════════════════════════════════════════════════════════

class TestBusinessMemory:

    def test_store_retrieve(self, tmp_path):
        """B16: Store and retrieve memory."""
        from business_agents.memory.business_memory import BusinessMemory
        mem = BusinessMemory("test-agent", storage_dir=tmp_path / "mem")
        assert mem.store("client_context_memory", "customer_john",
                         {"name": "John", "phone": "555-1234"})
        result = mem.retrieve("client_context_memory", "customer_john")
        assert result["name"] == "John"

    def test_scope_bounds(self, tmp_path):
        """B17: Memory scopes are bounded."""
        from business_agents.memory.business_memory import BusinessMemory
        mem = BusinessMemory("test-agent", storage_dir=tmp_path / "mem")
        # Business profile has limit of 50
        for i in range(55):
            mem.store("business_profile_memory", f"item_{i}", {"value": i})
        stats = mem.get_stats()
        assert stats["scopes"]["business_profile_memory"]["count"] <= 50

    def test_ttl_expiry(self, tmp_path):
        """B18: Memory TTL expiry works."""
        from business_agents.memory.business_memory import BusinessMemory, MemoryEntry
        mem = BusinessMemory("test-agent", storage_dir=tmp_path / "mem")
        # Store with 0 second TTL (immediate expiry)
        mem.store("agent_local_memory", "temp", {"data": "temporary"}, ttl_seconds=0.001)
        time.sleep(0.01)
        result = mem.retrieve("agent_local_memory", "temp")
        assert result is None

    def test_search(self, tmp_path):
        """B19: Memory search works."""
        from business_agents.memory.business_memory import BusinessMemory
        mem = BusinessMemory("test-agent", storage_dir=tmp_path / "mem")
        mem.store("client_context_memory", "c1", {"name": "John Smith", "type": "residential"})
        mem.store("client_context_memory", "c2", {"name": "Jane Doe", "type": "commercial"})
        results = mem.search("client_context_memory", "John")
        assert len(results) >= 1
        assert any("John" in str(r["value"]) for r in results)

    def test_per_agent_isolation(self, tmp_path):
        """B20: Per-agent isolation."""
        from business_agents.memory.business_memory import BusinessMemory
        mem1 = BusinessMemory("agent-1", storage_dir=tmp_path / "mem")
        mem2 = BusinessMemory("agent-2", storage_dir=tmp_path / "mem")
        mem1.store("agent_local_memory", "secret", {"data": "agent1_only"})
        result = mem2.retrieve("agent_local_memory", "secret")
        assert result is None


# ═══════════════════════════════════════════════════════════════
# PHASE 5: TEST HARNESS
# ═══════════════════════════════════════════════════════════════

class TestHarness:

    def test_battery_generated(self):
        """B21: Test battery generated for each template."""
        from business_agents.test_harness import generate_test_battery
        from business_agents.templates.quote_agent import QUOTE_AGENT_TEMPLATE
        tests = generate_test_battery(QUOTE_AGENT_TEMPLATE)
        assert len(tests) >= 5
        names = [t.name for t in tests]
        assert "valid_complete_input" in names
        assert "missing_required_fields" in names

    def test_suite_quote_agent(self, tmp_path):
        """B22: Test suite runs on quote agent."""
        from business_agents.factory import AgentFactory
        from business_agents.test_harness import run_test_suite
        factory = AgentFactory(persist_dir=tmp_path / "agents")
        agent = factory.create("quote_agent", {"business_name": "Test Heating"})
        result = run_test_suite(agent)
        assert result.total_tests >= 5
        assert result.passed > 0
        assert result.score > 0

    def test_suite_support_agent(self, tmp_path):
        """B23: Test suite runs on support agent."""
        from business_agents.factory import AgentFactory
        from business_agents.test_harness import run_test_suite
        factory = AgentFactory(persist_dir=tmp_path / "agents")
        agent = factory.create("support_agent", {"business_name": "Test Support"})
        result = run_test_suite(agent)
        assert result.total_tests >= 5
        assert result.passed > 0

    def test_suite_content_agent(self, tmp_path):
        """B24: Test suite runs on content agent."""
        from business_agents.factory import AgentFactory
        from business_agents.test_harness import run_test_suite
        factory = AgentFactory(persist_dir=tmp_path / "agents")
        agent = factory.create("content_agent", {"business_name": "Test CBD"})
        result = run_test_suite(agent)
        assert result.total_tests >= 5
        assert result.passed > 0

    def test_valid_vs_missing(self, tmp_path):
        """B25: Valid input passes, missing input fails correctly."""
        from business_agents.factory import AgentFactory
        from business_agents.test_harness import run_test_case, TestCase
        factory = AgentFactory(persist_dir=tmp_path / "agents")
        agent = factory.create("quote_agent", {"business_name": "Test"})

        # Valid input
        valid = TestCase(name="valid", description="valid",
                         input_data={"customer_message": "I need a boiler repair"},
                         expected_behavior="success")
        r1 = run_test_case(agent, valid)
        assert r1.passed

        # Missing required
        missing = TestCase(name="missing", description="missing",
                           input_data={},
                           expected_behavior="validation_error")
        r2 = run_test_case(agent, missing)
        assert r2.passed  # Correctly detected as validation error


# ═══════════════════════════════════════════════════════════════
# PHASE 6: SELF-IMPROVEMENT
# ═══════════════════════════════════════════════════════════════

class TestSelfImprovement:

    def test_performance_tracking(self, tmp_path):
        """B26: Performance tracking works."""
        from business_agents.improvement_bridge import ImprovementBridge
        bridge = ImprovementBridge(persist_path=tmp_path / "perf.json")
        bridge.record("agent-1", True, 0.8)
        bridge.record("agent-1", True, 0.9)
        bridge.record("agent-1", False, 0.3, "timeout")
        stats = bridge.get_stats("agent-1")
        assert stats["total_executions"] == 3
        assert stats["success_rate"] > 0.5

    def test_improvement_candidates(self, tmp_path):
        """B27: Improvement candidates detected."""
        from business_agents.improvement_bridge import ImprovementBridge
        bridge = ImprovementBridge(persist_path=tmp_path / "perf.json")
        for _ in range(4):
            bridge.record("bad-agent", False, 0.2, "parsing_error")
        for _ in range(2):
            bridge.record("bad-agent", True, 0.5)
        candidates = bridge.get_improvement_candidates()
        assert any(c["agent_id"] == "bad-agent" for c in candidates)

    def test_suggestions(self, tmp_path):
        """B28: Suggestions generated."""
        from business_agents.improvement_bridge import ImprovementBridge
        bridge = ImprovementBridge(persist_path=tmp_path / "perf.json")
        for _ in range(5):
            bridge.record("failing-agent", False, 0.1, "crash")
        for _ in range(1):
            bridge.record("failing-agent", True, 0.3)
        candidates = bridge.get_improvement_candidates()
        assert len(candidates) > 0
        assert "suggestion" in candidates[0]


# ═══════════════════════════════════════════════════════════════
# PHASE 7: REGISTRY
# ═══════════════════════════════════════════════════════════════

class TestRegistry:

    def test_registry_populates(self, tmp_path):
        """B29: Agent registry populates."""
        from business_agents.factory import AgentFactory
        from business_agents.registry_api import get_agent_registry
        factory = AgentFactory(persist_dir=tmp_path / "agents")
        factory.create("quote_agent", {"business_name": "Test"})
        registry = get_agent_registry(factory)
        assert len(registry) >= 1
        assert "health" in registry[0]
        assert "performance" in registry[0]

    def test_registry_summary(self, tmp_path):
        """B30: Registry summary has correct structure."""
        from business_agents.factory import AgentFactory
        from business_agents.registry_api import get_registry_summary
        factory = AgentFactory(persist_dir=tmp_path / "agents")
        factory.create("quote_agent", {"business_name": "Test"})
        summary = get_registry_summary(factory)
        assert "total_agents" in summary
        assert "total_templates" in summary
        assert "by_health" in summary
        assert "by_status" in summary
        assert summary["total_agents"] >= 1
        assert summary["total_templates"] >= 3


# ═══════════════════════════════════════════════════════════════
# PHASE 8: END-TO-END VALIDATION
# ═══════════════════════════════════════════════════════════════

class TestEndToEnd:

    def test_heating_quote_agent(self, tmp_path):
        """B31: Heating company quote agent full lifecycle."""
        from business_agents.factory import AgentFactory
        from business_agents.test_harness import run_test_suite
        from business_agents.improvement_bridge import ImprovementBridge
        from business_agents.memory.business_memory import BusinessMemory

        factory = AgentFactory(persist_dir=tmp_path / "agents")
        bridge = ImprovementBridge(persist_path=tmp_path / "perf.json")

        # 1. Create
        agent = factory.create("quote_agent", {
            "business_name": "Smith Heating Ltd",
            "business_type": "HVAC / Heating",
            "service_area": "Greater London",
            "currency": "GBP",
        })
        assert agent.status == "created"

        # 2. Test
        result = run_test_suite(agent)
        assert result.total_tests >= 5
        assert result.score > 0

        # 3. Execute sample input
        output = agent.execute({"customer_message": "My boiler stopped working, need repair ASAP"})
        assert output.get("input_validated") or output.get("status")

        # 4. Memory
        mem = BusinessMemory(agent.id, storage_dir=tmp_path / "mem")
        mem.store("business_profile_memory", "services",
                  {"boiler_repair": 250, "installation": 3000, "maintenance": 120})
        assert mem.retrieve("business_profile_memory", "services")["boiler_repair"] == 250

        # 5. Track performance
        bridge.record(agent.id, True, result.score)

    def test_support_agent(self, tmp_path):
        """B32: Small business customer support agent full lifecycle."""
        from business_agents.factory import AgentFactory
        from business_agents.test_harness import run_test_suite
        from business_agents.improvement_bridge import ImprovementBridge

        factory = AgentFactory(persist_dir=tmp_path / "agents")
        bridge = ImprovementBridge(persist_path=tmp_path / "perf.json")

        agent = factory.create("support_agent", {
            "business_name": "TechFix Solutions",
            "business_type": "IT Support",
            "support_hours": "Mon-Fri 9:00-17:00 GMT",
            "escalation_email": "urgent@techfix.com",
        })

        result = run_test_suite(agent)
        assert result.total_tests >= 5

        output = agent.execute({
            "customer_message": "My printer isn't connecting to the network",
            "customer_name": "Sarah Johnson",
        })
        assert output.get("input_validated") or output.get("status")

        bridge.record(agent.id, True, result.score)

    def test_cbd_content_agent(self, tmp_path):
        """B33: Ecommerce/CBD content agent full lifecycle."""
        from business_agents.factory import AgentFactory
        from business_agents.test_harness import run_test_suite
        from business_agents.improvement_bridge import ImprovementBridge

        factory = AgentFactory(persist_dir=tmp_path / "agents")
        bridge = ImprovementBridge(persist_path=tmp_path / "perf.json")

        agent = factory.create("content_agent", {
            "business_name": "Green Leaf CBD",
            "business_type": "CBD ecommerce",
            "brand_voice": "Professional, wellness-focused, trustworthy, no medical claims",
            "target_audience": "Health-conscious adults 25-55",
        })

        result = run_test_suite(agent)
        assert result.total_tests >= 5

        output = agent.execute({
            "content_type": "product_page",
            "content_brief": "New CBD oil tincture, 1000mg, full spectrum, organic hemp",
        })
        assert output.get("input_validated") or output.get("status")

        bridge.record(agent.id, True, result.score)
