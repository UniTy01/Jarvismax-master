"""
Tests — Orchestration Intelligence

1. Capability Dispatch
  O1.  Code generation detected
  O2.  Analysis detected
  O3.  Research detected
  O4.  System admin detected
  O5.  Unknown falls back to conversation
  O6.  Multi-keyword improves confidence

2. Mission Planning
  O7.  Create plan for code generation
  O8.  Create plan for analysis
  O9.  Validate valid plan
  O10. Detect missing dependencies
  O11. Detect circular dependencies
  O12. Detect redundant steps
  O13. Detect unknown actions
  O14. Reject oversized plan

3. Memory Injection
  O15. Memory injector doesn't crash with empty stores
  O16. Memory context serializes correctly
  O17. Empty memory produces empty prompt

4. Orchestration Tracer
  O18. Start and complete trace
  O19. Record capability + plan + memory
  O20. Get recent traces
  O21. Duration calculated

5. Mission Checkpointer
  O22. Checkpoint step completion
  O23. Resume from last completed
  O24. Detect need for replan
  O25. Calculate drift score
  O26. Clear checkpoints

6. Full Brain (integration)
  O27. Trivial mission (conversation)
  O28. Analysis mission
  O29. Multi-step code mission
  O30. Mission with memory context
  O31. Long-ish mission (system admin)
  O32. Complete mission records trace
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.orchestration_intelligence import (
    CapabilityType, CapabilityMatch, CapabilityDispatcher,
    PlanStep, PlanValidation, MissionPlanner,
    MemoryContext, MemoryInjector,
    OrchestrationTrace, OrchestrationTracer,
    Checkpoint, MissionCheckpointer,
    OrchestrationBrain,
)


# ═══════════════════════════════════════════════════════════════
# 1. CAPABILITY DISPATCH
# ═══════════════════════════════════════════════════════════════

class TestCapabilityDispatch:

    def test_code_generation(self):
        """O1: Code generation detected."""
        d = CapabilityDispatcher()
        m = d.dispatch("Write code to parse a JSON file")
        assert m.capability == CapabilityType.CODE_GENERATION
        assert m.confidence > 0.3
        assert not m.fallback

    def test_analysis(self):
        """O2: Analysis detected."""
        d = CapabilityDispatcher()
        m = d.dispatch("Analyze the performance of our API endpoints")
        assert m.capability == CapabilityType.ANALYSIS

    def test_research(self):
        """O3: Research detected."""
        d = CapabilityDispatcher()
        m = d.dispatch("Research the best practices for microservices")
        assert m.capability == CapabilityType.RESEARCH

    def test_system_admin(self):
        """O4: System admin detected."""
        d = CapabilityDispatcher()
        m = d.dispatch("Deploy the new version to Docker")
        assert m.capability == CapabilityType.SYSTEM_ADMIN

    def test_unknown_fallback(self):
        """O5: Unknown falls back to conversation."""
        d = CapabilityDispatcher()
        m = d.dispatch("xyzzy qwerty asdfgh")
        assert m.capability == CapabilityType.CONVERSATION
        assert m.fallback is True

    def test_multi_keyword(self):
        """O6: Multi-keyword match improves confidence."""
        d = CapabilityDispatcher()
        single = d.dispatch("implement something")
        multi = d.dispatch("write code to implement a new feature and build it")
        assert multi.confidence >= single.confidence


# ═══════════════════════════════════════════════════════════════
# 2. MISSION PLANNING
# ═══════════════════════════════════════════════════════════════

class TestMissionPlanning:

    def test_code_plan(self):
        """O7: Create plan for code generation."""
        p = MissionPlanner()
        cap = CapabilityMatch(capability=CapabilityType.CODE_GENERATION, confidence=0.8, keywords_matched=[])
        steps = p.create_plan("Write a parser", cap)
        assert len(steps) >= 2
        assert steps[0].action in ("analyze", "read")

    def test_analysis_plan(self):
        """O8: Create plan for analysis."""
        p = MissionPlanner()
        cap = CapabilityMatch(capability=CapabilityType.ANALYSIS, confidence=0.7, keywords_matched=[])
        steps = p.create_plan("Analyze performance", cap)
        assert len(steps) >= 2
        assert any(s.action == "analyze" for s in steps)

    def test_validate_valid_plan(self):
        """O9: Valid plan passes validation."""
        p = MissionPlanner()
        steps = [
            PlanStep(1, "read", "Read file"),
            PlanStep(2, "analyze", "Analyze content", depends_on=[1]),
            PlanStep(3, "report", "Write report", depends_on=[2]),
        ]
        v = p.validate(steps)
        assert v.valid
        assert len(v.errors) == 0

    def test_missing_dependency(self):
        """O10: Detect missing dependencies."""
        p = MissionPlanner()
        steps = [
            PlanStep(1, "read", "Read"),
            PlanStep(2, "analyze", "Analyze", depends_on=[1, 99]),  # 99 doesn't exist
        ]
        v = p.validate(steps)
        assert not v.valid
        assert len(v.missing_deps) > 0

    def test_circular_dependency(self):
        """O11: Detect circular dependencies."""
        p = MissionPlanner()
        steps = [
            PlanStep(1, "read", "A", depends_on=[3]),
            PlanStep(2, "analyze", "B", depends_on=[1]),
            PlanStep(3, "report", "C", depends_on=[2]),
        ]
        v = p.validate(steps)
        assert not v.valid
        assert any("circular" in e.lower() for e in v.errors)

    def test_redundant_steps(self):
        """O12: Detect redundant steps."""
        p = MissionPlanner()
        steps = [
            PlanStep(1, "read", "Read data"),
            PlanStep(2, "read", "Read data"),
            PlanStep(3, "analyze", "Process", depends_on=[1]),
        ]
        v = p.validate(steps)
        assert len(v.redundant_steps) > 0

    def test_unknown_action(self):
        """O13: Unknown actions flagged."""
        p = MissionPlanner()
        steps = [PlanStep(1, "teleport", "Move to Mars")]
        v = p.validate(steps)
        assert len(v.impossible_steps) > 0

    def test_oversized_plan(self):
        """O14: Reject oversized plan."""
        p = MissionPlanner()
        steps = [PlanStep(i, "read", f"Step {i}") for i in range(25)]
        v = p.validate(steps)
        assert not v.valid


# ═══════════════════════════════════════════════════════════════
# 3. MEMORY INJECTION
# ═══════════════════════════════════════════════════════════════

class TestMemoryInjection:

    def test_no_crash(self):
        """O15: Memory injector doesn't crash with empty stores."""
        m = MemoryInjector()
        ctx = m.inject("test goal")
        assert isinstance(ctx, MemoryContext)

    def test_serialization(self):
        """O16: Memory context serializes correctly."""
        ctx = MemoryContext(
            project_context=["project A uses Python"],
            user_preferences=["prefers concise output"],
            total_items=2,
        )
        d = ctx.to_dict()
        assert d["total_items"] == 2
        assert len(d["project_context"]) == 1

    def test_empty_prompt(self):
        """O17: Empty memory produces empty prompt."""
        ctx = MemoryContext()
        assert ctx.as_prompt_context() == ""


# ═══════════════════════════════════════════════════════════════
# 4. ORCHESTRATION TRACER
# ═══════════════════════════════════════════════════════════════

class TestOrchestrationTracer:

    def test_start_complete(self):
        """O18: Start and complete trace."""
        t = OrchestrationTracer()
        t.start("m1", "Test goal")
        result = t.complete("m1", "success", "All steps passed")
        assert result is not None
        assert result.outcome == "success"
        assert result.duration_ms >= 0

    def test_record_all(self):
        """O19: Record capability + plan + memory."""
        t = OrchestrationTracer()
        t.start("m2", "Code task")
        t.record_capability("m2", CapabilityMatch(
            capability="code_generation", confidence=0.8, keywords_matched=["code"]))
        t.record_plan("m2", [PlanStep(1, "a", "b")],
                      PlanValidation(valid=True))
        t.record_memory("m2", MemoryContext(total_items=3))
        trace = t.get("m2")
        assert trace is not None
        assert trace.capability == "code_generation"
        assert trace.plan_steps == 1
        assert trace.memory_items == 3

    def test_recent(self):
        """O20: Get recent traces."""
        t = OrchestrationTracer()
        for i in range(5):
            t.start(f"m{i}", f"Goal {i}")
            t.complete(f"m{i}", "success")
        recent = t.get_recent(limit=3)
        assert len(recent) == 3

    def test_duration(self):
        """O21: Duration calculated."""
        import time
        t = OrchestrationTracer()
        t.start("md", "Duration test")
        time.sleep(0.01)
        result = t.complete("md", "success")
        assert result.duration_ms >= 5  # at least 5ms


# ═══════════════════════════════════════════════════════════════
# 5. MISSION CHECKPOINTER
# ═══════════════════════════════════════════════════════════════

class TestMissionCheckpointer:

    def test_checkpoint(self):
        """O22: Checkpoint step completion."""
        c = MissionCheckpointer()
        step = PlanStep(1, "read", "Read file")
        c.checkpoint("m1", step, "completed", "OK")
        cps = c.get_checkpoints("m1")
        assert len(cps) == 1
        assert cps[0].state == "completed"

    def test_resume(self):
        """O23: Resume from last completed."""
        c = MissionCheckpointer()
        for i in range(1, 4):
            s = PlanStep(i, "step", f"Step {i}")
            state = "completed" if i <= 2 else "failed"
            c.checkpoint("m2", s, state)
        assert c.get_last_completed("m2") == 2
        assert c.get_resume_point("m2") == 3

    def test_replan(self):
        """O24: Detect need for replan."""
        c = MissionCheckpointer()
        s1 = PlanStep(1, "a", "A")
        s2 = PlanStep(2, "b", "B")
        c.checkpoint("m3", s1, "failed")
        c.checkpoint("m3", s2, "failed")
        assert c.needs_replan("m3") is True

    def test_drift(self):
        """O25: Calculate drift score."""
        c = MissionCheckpointer()
        s1 = PlanStep(1, "a", "A")
        s2 = PlanStep(2, "b", "B")
        c.checkpoint("m4", s1, "completed")
        c.checkpoint("m4", s2, "failed")
        drift = c.get_drift_score("m4", original_steps=4)
        assert 0 < drift < 1

    def test_clear(self):
        """O26: Clear checkpoints."""
        c = MissionCheckpointer()
        c.checkpoint("m5", PlanStep(1, "a", "A"), "completed")
        c.clear("m5")
        assert c.get_checkpoints("m5") == []


# ═══════════════════════════════════════════════════════════════
# 6. FULL BRAIN (integration)
# ═══════════════════════════════════════════════════════════════

class TestOrchestrationBrain:

    def test_trivial_mission(self):
        """O27: Trivial mission (conversation)."""
        brain = OrchestrationBrain()
        r = brain.prepare("m-trivial", "Hello, how are you?")
        assert r["capability"]["capability"] == CapabilityType.CONVERSATION
        assert r["plan_valid"]

    def test_analysis_mission(self):
        """O28: Analysis mission."""
        brain = OrchestrationBrain()
        r = brain.prepare("m-analysis", "Analyze the API response times")
        assert r["capability"]["capability"] == CapabilityType.ANALYSIS
        assert len(r["plan"]) >= 2
        assert r["plan_valid"]

    def test_multistep_code(self):
        """O29: Multi-step code mission."""
        brain = OrchestrationBrain()
        r = brain.prepare("m-code", "Write code to implement a REST API endpoint")
        assert r["capability"]["capability"] == CapabilityType.CODE_GENERATION
        assert len(r["plan"]) >= 3  # analyze, generate, test

    def test_memory_context(self):
        """O30: Mission includes memory context."""
        brain = OrchestrationBrain()
        r = brain.prepare("m-mem", "Research best practices for error handling")
        assert "memory" in r
        assert "memory_prompt" in r
        assert isinstance(r["memory"], dict)

    def test_sysadmin_mission(self):
        """O31: Long-ish mission (system admin, 4 steps)."""
        brain = OrchestrationBrain()
        r = brain.prepare("m-deploy", "Deploy the Docker container to production server")
        assert r["capability"]["capability"] == CapabilityType.SYSTEM_ADMIN
        assert len(r["plan"]) >= 4  # analyze, plan, execute, validate
        assert r["strategy"] == "v2_budget"  # >3 steps

    def test_complete_trace(self):
        """O32: Complete mission records full trace."""
        brain = OrchestrationBrain()
        brain.prepare("m-trace", "Analyze performance metrics")
        result = brain.complete_mission("m-trace", "success", "All 3 steps completed")
        assert result is not None
        assert result["outcome"] == "success"
        assert result["capability"] == CapabilityType.ANALYSIS
        assert result["duration_ms"] >= 0
        assert len(result["execution_path"]) >= 3  # capability, memory/plan, strategy
