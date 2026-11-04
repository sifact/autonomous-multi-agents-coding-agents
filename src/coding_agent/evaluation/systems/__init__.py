"""Systems under evaluation: two baselines and the multi-agent graph."""
from coding_agent.evaluation.systems.base import System, SystemOutput, attach_partial
from coding_agent.evaluation.systems.graph_system import GraphSystem
from coding_agent.evaluation.systems.single_agent import SingleAgentLoop
from coding_agent.evaluation.systems.single_shot import SingleShot

__all__ = [
    "GraphSystem",
    "SingleAgentLoop",
    "SingleShot",
    "System",
    "SystemOutput",
    "attach_partial",
]
