"""business.trade_ops — Trade Ops module."""
from business.trade_ops.schema import TradeAgentConfig, TradeOpsSpec, parse_trade_ops_spec

def get_agent(settings):
    from business.trade_ops.agent import TradeOpsAgent
    return TradeOpsAgent(settings)

__all__ = [
    "get_agent",
    "TradeAgentConfig",
    "TradeOpsSpec",
    "parse_trade_ops_spec",
]
