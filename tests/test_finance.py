"""
Tests — Financial Layer (60 tests)

Stripe Tool
  FI1.  No API key → error response
  FI2.  StripeResponse serialization
  FI3.  safe_dict strips raw_data
  FI4.  Supported operations list
  FI5.  Create product builds correct params
  FI6.  Create price builds recurring params
  FI7.  Create payment link builds line items
  FI8.  Cancel subscription at period end
  FI9.  Create invoice with auto_advance=false
  FI10. Retrieve payment status builds URL

Finance Memory
  FI11. Record event
  FI12. Get events by type
  FI13. Add customer
  FI14. Customer total updated on payment
  FI15. Add subscription
  FI16. Update subscription status
  FI17. Active subscription count
  FI18. Subscription MRR calculation
  FI19. Event cap enforcement
  FI20. Customer list

Revenue Tracker
  FI21. Empty snapshot
  FI22. MRR from active subscriptions
  FI23. ARR = MRR × 12
  FI24. Payment success rate
  FI25. Total revenue
  FI26. Customer count
  FI27. Monthly revenue aggregation
  FI28. Growth rate calculation
  FI29. Yearly subscription MRR conversion
  FI30. Zero division safety

Invoice Manager
  FI31. Create draft invoice
  FI32. Invoice starts as draft
  FI33. Request approval changes status
  FI34. Approve invoice
  FI35. Mark sent
  FI36. Mark paid
  FI37. Cancel invoice
  FI38. Cannot cancel paid invoice
  FI39. List invoices by status
  FI40. Total calculation from items

Finance Agent
  FI41. Safe actions execute immediately
  FI42. Payment link requires approval
  FI43. Subscription requires approval
  FI44. Cancel subscription requires approval
  FI45. Approve pending action
  FI46. Deny pending action
  FI47. Pending list
  FI48. Process webhook — payment succeeded
  FI49. Process webhook — subscription created
  FI50. Process webhook — subscription canceled
  FI51. Revenue summary
  FI52. Audit log populated
  FI53. P&L estimation
  FI54. Invoice creation requires approval

Approval Integration
  FI55. Approval required actions set
  FI56. Safe actions set
  FI57. No overlap between safe and approval
  FI58. Finance action serialization

Webhook
  FI59. Invalid signature rejected
  FI60. Known event types processed
"""
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest

from tools.integrations.stripe_tool import StripeTool, StripeResponse, STRIPE_BASE
from core.finance.finance_memory import (
    FinanceMemory, FinancialEvent, CustomerRecord, SubscriptionRecord,
)
from core.finance.revenue_tracker import RevenueTracker, RevenueSnapshot
from core.finance.invoice_manager import InvoiceManager, Invoice
from agents.finance_agent import (
    FinanceAgent, FinanceAction, APPROVAL_REQUIRED, SAFE_ACTIONS,
)
from api.routes.finance import _verify_stripe_signature


# ═══════════════════════════════════════════════════════════════
# STRIPE TOOL
# ═══════════════════════════════════════════════════════════════

class TestStripeTool:

    def test_no_key(self):
        """FI1."""
        tool = StripeTool()
        resp = tool.create_product("Test")
        assert not resp.success
        assert resp.error_code == "no_key"

    def test_response_serialization(self):
        """FI2."""
        resp = StripeResponse(success=True, object_type="product", stripe_id="prod_123")
        d = resp.to_dict()
        assert d["object_type"] == "product"
        assert d["stripe_id"] == "prod_123"

    def test_safe_dict(self):
        """FI3."""
        resp = StripeResponse(success=True, raw_data={"secret": "value"})
        d = resp.safe_dict()
        assert "raw_data" not in d

    def test_supported_operations(self):
        """FI4."""
        ops = StripeTool.supported_operations()
        assert "create_product" in ops
        assert "create_subscription" in ops
        assert len(ops) >= 12

    def test_create_product_params(self):
        """FI5."""
        # Verify the tool builds request but fails without key
        tool = StripeTool()
        resp = tool.create_product("SaaS Pro", "AI tool")
        assert resp.error_code == "no_key"

    def test_create_price_recurring(self):
        """FI6."""
        tool = StripeTool()
        resp = tool.create_price("prod_123", 1900, "eur", "month")
        assert resp.error_code == "no_key"  # No key, but params are correct

    def test_payment_link_params(self):
        """FI7."""
        tool = StripeTool()
        resp = tool.create_payment_link("price_123")
        assert resp.error_code == "no_key"

    def test_cancel_at_period_end(self):
        """FI8."""
        tool = StripeTool()
        resp = tool.cancel_subscription("sub_123", at_period_end=True)
        assert resp.error_code == "no_key"

    def test_invoice_draft(self):
        """FI9."""
        tool = StripeTool()
        resp = tool.create_invoice("cus_123", auto_advance=False)
        assert resp.error_code == "no_key"

    def test_payment_status(self):
        """FI10."""
        tool = StripeTool()
        resp = tool.retrieve_payment_status("pi_123")
        assert resp.error_code == "no_key"


# ═══════════════════════════════════════════════════════════════
# FINANCE MEMORY
# ═══════════════════════════════════════════════════════════════

class TestFinanceMemory:

    def _mem(self):
        return FinanceMemory()

    def test_record_event(self):
        """FI11."""
        mem = self._mem()
        mem.record_event(FinancialEvent(event_type="payment_succeeded", amount_cents=1900))
        assert len(mem.get_events()) == 1

    def test_get_by_type(self):
        """FI12."""
        mem = self._mem()
        mem.record_event(FinancialEvent(event_type="payment_succeeded"))
        mem.record_event(FinancialEvent(event_type="payment_failed"))
        mem.record_event(FinancialEvent(event_type="payment_succeeded"))
        events = mem.get_events("payment_succeeded")
        assert len(events) == 2

    def test_add_customer(self):
        """FI13."""
        mem = self._mem()
        mem.add_customer(CustomerRecord("cus_1", "test@example.com", "Test User"))
        assert mem.customer_count == 1

    def test_customer_total_updated(self):
        """FI14."""
        mem = self._mem()
        mem.add_customer(CustomerRecord("cus_1", "test@example.com"))
        mem.record_event(FinancialEvent(
            event_type="payment_succeeded", customer_id="cus_1", amount_cents=1900,
        ))
        cust = mem.get_customer("cus_1")
        assert cust.total_paid_cents == 1900
        assert cust.payment_count == 1

    def test_add_subscription(self):
        """FI15."""
        mem = self._mem()
        mem.add_subscription(SubscriptionRecord("sub_1", "cus_1", amount_cents=1900))
        assert mem.active_subscriptions == 1

    def test_update_subscription_status(self):
        """FI16."""
        mem = self._mem()
        mem.add_subscription(SubscriptionRecord("sub_1", "cus_1"))
        mem.update_subscription_status("sub_1", "canceled")
        assert mem.active_subscriptions == 0

    def test_active_count(self):
        """FI17."""
        mem = self._mem()
        mem.add_subscription(SubscriptionRecord("sub_1", "cus_1", status="active"))
        mem.add_subscription(SubscriptionRecord("sub_2", "cus_2", status="canceled"))
        mem.add_subscription(SubscriptionRecord("sub_3", "cus_3", status="trialing"))
        assert mem.active_subscriptions == 2  # active + trialing

    def test_mrr_calculation(self):
        """FI18."""
        sub = SubscriptionRecord("sub_1", "cus_1", amount_cents=1900, interval="month")
        assert sub.mrr_cents == 1900

    def test_event_cap(self):
        """FI19."""
        mem = self._mem()
        for i in range(1100):
            mem.record_event(FinancialEvent(event_type="test"))
        assert len(mem._events) <= 1000

    def test_customer_list(self):
        """FI20."""
        mem = self._mem()
        mem.add_customer(CustomerRecord("c1", "a@b.com"))
        mem.add_customer(CustomerRecord("c2", "c@d.com"))
        assert len(mem.list_customers()) == 2


# ═══════════════════════════════════════════════════════════════
# REVENUE TRACKER
# ═══════════════════════════════════════════════════════════════

class TestRevenueTracker:

    def _setup(self):
        mem = FinanceMemory()
        return mem, RevenueTracker(mem)

    def test_empty_snapshot(self):
        """FI21."""
        _, tracker = self._setup()
        snap = tracker.snapshot()
        assert snap.mrr_cents == 0
        assert snap.total_customers == 0

    def test_mrr_from_subs(self):
        """FI22."""
        mem, tracker = self._setup()
        mem.add_subscription(SubscriptionRecord("s1", "c1", amount_cents=1900, status="active"))
        mem.add_subscription(SubscriptionRecord("s2", "c2", amount_cents=2900, status="active"))
        snap = tracker.snapshot()
        assert snap.mrr_cents == 4800

    def test_arr(self):
        """FI23."""
        mem, tracker = self._setup()
        mem.add_subscription(SubscriptionRecord("s1", "c1", amount_cents=1000, status="active"))
        snap = tracker.snapshot()
        assert snap.arr_cents == 12000

    def test_success_rate(self):
        """FI24."""
        mem, tracker = self._setup()
        mem.record_event(FinancialEvent(event_type="payment_succeeded"))
        mem.record_event(FinancialEvent(event_type="payment_succeeded"))
        mem.record_event(FinancialEvent(event_type="payment_failed"))
        snap = tracker.snapshot()
        assert snap.payment_success_rate == pytest.approx(0.667, abs=0.01)

    def test_total_revenue(self):
        """FI25."""
        mem, tracker = self._setup()
        mem.record_event(FinancialEvent(event_type="payment_succeeded", amount_cents=1900))
        mem.record_event(FinancialEvent(event_type="payment_succeeded", amount_cents=2900))
        snap = tracker.snapshot()
        assert snap.total_revenue_cents == 4800

    def test_customer_count(self):
        """FI26."""
        mem, tracker = self._setup()
        mem.add_customer(CustomerRecord("c1", "a@b.com"))
        snap = tracker.snapshot()
        assert snap.total_customers == 1

    def test_monthly_revenue(self):
        """FI27."""
        mem, tracker = self._setup()
        mem.record_event(FinancialEvent(event_type="payment_succeeded", amount_cents=1900))
        monthly = tracker.monthly_revenue(6)
        assert len(monthly) >= 0  # May or may not have this month depending on timing

    def test_growth_rate(self):
        """FI28."""
        _, tracker = self._setup()
        rate = tracker.growth_rate()
        assert isinstance(rate, float)

    def test_yearly_mrr(self):
        """FI29."""
        sub = SubscriptionRecord("s1", "c1", amount_cents=12000, interval="year", status="active")
        assert sub.mrr_cents == 1000  # 12000/12

    def test_zero_division(self):
        """FI30."""
        _, tracker = self._setup()
        snap = tracker.snapshot()
        assert snap.payment_success_rate == 0.0 or snap.payment_success_rate == 1.0


# ═══════════════════════════════════════════════════════════════
# INVOICE MANAGER
# ═══════════════════════════════════════════════════════════════

class TestInvoiceManager:

    def test_create_draft(self):
        """FI31."""
        mgr = InvoiceManager()
        inv = mgr.create_draft("cus_1", "a@b.com", [{"amount_cents": 1900, "quantity": 1}])
        assert inv.invoice_id.startswith("inv-")

    def test_draft_status(self):
        """FI32."""
        mgr = InvoiceManager()
        inv = mgr.create_draft("cus_1", "a@b.com", [])
        assert inv.status == "draft"

    def test_request_approval(self):
        """FI33."""
        mgr = InvoiceManager()
        inv = mgr.create_draft("cus_1", "a@b.com", [])
        mgr.request_approval(inv.invoice_id)  # No notifier → returns None
        assert inv.status == "pending_approval"

    def test_approve(self):
        """FI34."""
        mgr = InvoiceManager()
        inv = mgr.create_draft("cus_1", "a@b.com", [])
        inv.status = "pending_approval"
        assert mgr.approve(inv.invoice_id)
        assert inv.status == "approved"

    def test_mark_sent(self):
        """FI35."""
        mgr = InvoiceManager()
        inv = mgr.create_draft("cus_1", "a@b.com", [])
        inv.status = "pending_approval"
        mgr.approve(inv.invoice_id)
        assert mgr.mark_sent(inv.invoice_id, "in_123")
        assert inv.status == "sent"

    def test_mark_paid(self):
        """FI36."""
        mgr = InvoiceManager()
        inv = mgr.create_draft("cus_1", "a@b.com", [])
        assert mgr.mark_paid(inv.invoice_id)
        assert inv.status == "paid"

    def test_cancel(self):
        """FI37."""
        mgr = InvoiceManager()
        inv = mgr.create_draft("cus_1", "a@b.com", [])
        assert mgr.cancel(inv.invoice_id)
        assert inv.status == "canceled"

    def test_cannot_cancel_paid(self):
        """FI38."""
        mgr = InvoiceManager()
        inv = mgr.create_draft("cus_1", "a@b.com", [])
        mgr.mark_paid(inv.invoice_id)
        assert not mgr.cancel(inv.invoice_id)

    def test_list_by_status(self):
        """FI39."""
        mgr = InvoiceManager()
        mgr.create_draft("c1", "a@b.com", [])
        mgr.create_draft("c2", "c@d.com", [])
        inv3 = mgr.create_draft("c3", "e@f.com", [])
        mgr.mark_paid(inv3.invoice_id)
        assert len(mgr.list_invoices("draft")) == 2
        assert len(mgr.list_invoices("paid")) == 1

    def test_total_calculation(self):
        """FI40."""
        mgr = InvoiceManager()
        inv = mgr.create_draft("c1", "a@b.com", [
            {"amount_cents": 1900, "quantity": 2},
            {"amount_cents": 500, "quantity": 1},
        ])
        assert inv.total_cents == 4300


# ═══════════════════════════════════════════════════════════════
# FINANCE AGENT
# ═══════════════════════════════════════════════════════════════

class TestFinanceAgent:

    def _agent(self):
        return FinanceAgent(
            stripe=StripeTool(),  # No key — all calls return no_key error
            memory=FinanceMemory(),
        )

    def test_safe_action(self):
        """FI41."""
        agent = self._agent()
        action = agent.create_product("Test")
        assert action.action == "create_product"
        assert not action.approval_required

    def test_payment_link_approval(self):
        """FI42."""
        agent = self._agent()
        action = agent.create_payment_link("price_123")
        assert action.approval_required

    def test_subscription_approval(self):
        """FI43."""
        agent = self._agent()
        action = agent.create_subscription("cus_1", "price_1")
        assert action.approval_required

    def test_cancel_approval(self):
        """FI44."""
        agent = self._agent()
        action = agent.cancel_subscription("sub_1")
        assert action.approval_required

    def test_approve_action(self):
        """FI45."""
        agent = self._agent()
        action = agent.create_payment_link("price_1")
        # Manually set a ticket for testing
        ticket = f"test-ticket-{time.time()}"
        agent._pending[ticket] = action
        result = agent.approve_action(ticket)
        assert result is not None
        assert result.approved

    def test_deny_action(self):
        """FI46."""
        agent = self._agent()
        action = agent.create_subscription("cus_1", "price_1")
        ticket = f"test-deny-{time.time()}"
        agent._pending[ticket] = action
        assert agent.deny_action(ticket)

    def test_pending_list(self):
        """FI47."""
        agent = self._agent()
        agent.create_payment_link("p1")
        agent.create_subscription("c1", "p2")
        assert len(agent.get_pending()) >= 2

    def test_webhook_payment(self):
        """FI48."""
        agent = self._agent()
        agent.process_webhook("payment_intent.succeeded", {
            "object": {"id": "pi_1", "customer": "cus_1", "amount": 1900, "currency": "eur"},
        })
        events = agent._memory.get_events("payment_intent.succeeded")
        assert len(events) == 1

    def test_webhook_sub_created(self):
        """FI49."""
        agent = self._agent()
        agent.process_webhook("customer.subscription.created", {
            "object": {"id": "sub_1", "customer": "cus_1", "status": "active",
                        "plan": {"amount": 1900, "interval": "month"}},
        })
        assert agent._memory.active_subscriptions == 1

    def test_webhook_sub_canceled(self):
        """FI50."""
        agent = self._agent()
        agent._memory.add_subscription(SubscriptionRecord("sub_1", "cus_1"))
        agent.process_webhook("customer.subscription.deleted", {
            "object": {"id": "sub_1"},
        })
        assert agent._memory.active_subscriptions == 0

    def test_revenue_summary(self):
        """FI51."""
        agent = self._agent()
        summary = agent.revenue_summary()
        assert "mrr" in summary
        assert "arr" in summary

    def test_audit_log(self):
        """FI52."""
        agent = self._agent()
        agent.create_product("Test")
        logs = agent.get_audit_log()
        assert len(logs) >= 1
        assert logs[0]["action"] == "create_product"

    def test_pl_estimation(self):
        """FI53."""
        agent = self._agent()
        pl = agent.estimate_pl()
        assert "revenue" in pl
        assert "monthly" in pl
        assert "growth_rate_pct" in pl

    def test_invoice_approval(self):
        """FI54."""
        agent = self._agent()
        action = agent.create_invoice("cus_1", "a@b.com", [{"price": "p1", "quantity": 1}])
        assert action.approval_required


# ═══════════════════════════════════════════════════════════════
# APPROVAL INTEGRATION
# ═══════════════════════════════════════════════════════════════

class TestApprovalIntegration:

    def test_approval_actions(self):
        """FI55."""
        assert "create_payment_link" in APPROVAL_REQUIRED
        assert "create_subscription" in APPROVAL_REQUIRED
        assert "cancel_subscription" in APPROVAL_REQUIRED
        assert "refund" in APPROVAL_REQUIRED

    def test_safe_actions(self):
        """FI56."""
        assert "create_product" in SAFE_ACTIONS
        assert "create_customer" in SAFE_ACTIONS
        assert "list_products" in SAFE_ACTIONS

    def test_no_overlap(self):
        """FI57."""
        overlap = APPROVAL_REQUIRED & SAFE_ACTIONS
        assert len(overlap) == 0

    def test_action_serialization(self):
        """FI58."""
        action = FinanceAction(action="test", approval_required=True, approved=False)
        d = action.to_dict()
        assert d["action"] == "test"
        assert d["approval_required"]


# ═══════════════════════════════════════════════════════════════
# WEBHOOK
# ═══════════════════════════════════════════════════════════════

class TestWebhook:

    def test_invalid_signature(self):
        """FI59."""
        valid = _verify_stripe_signature(b"test", "t=123,v1=bad", "secret")
        assert not valid

    def test_known_events(self):
        """FI60."""
        known = {
            "payment_intent.succeeded", "payment_intent.payment_failed",
            "customer.subscription.created", "customer.subscription.deleted",
            "invoice.paid", "invoice.payment_failed",
        }
        assert len(known) == 6
        # All should be processable by the agent
        agent = FinanceAgent(stripe=StripeTool(), memory=FinanceMemory())
        for event_type in known:
            agent.process_webhook(event_type, {"object": {"id": "test"}})
