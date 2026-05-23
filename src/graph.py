from langgraph.graph import StateGraph, END

from nodes import (
    planner_node,
    llm_network_executor,
    input_validator_node,
    investigation_report_node,
)
from schemas import GraphState
from configuration import Configuration

from src.logging import configure_logging, configure_langchain, get_logger

configure_logging()
configure_langchain()

logger = get_logger(__name__)

logger.info("🏗️ Constructing LangGraph orchestrator")

orchestrator = StateGraph(
    state_schema=GraphState, context_schema=Configuration
)

orchestrator.add_node(node="input_validator_node", action=input_validator_node)
orchestrator.add_node(node="planner_node", action=planner_node)
orchestrator.add_node(node="network_executor", action=llm_network_executor)
orchestrator.add_node(
    node="report_generator", action=investigation_report_node
)

orchestrator.set_entry_point(key="input_validator_node")
orchestrator.add_edge(start_key="input_validator_node", end_key="planner_node")
orchestrator.add_edge(start_key="planner_node", end_key="network_executor")
orchestrator.add_edge(
    start_key="network_executor", end_key="report_generator"
)
orchestrator.add_edge(start_key="report_generator", end_key=END)

app = orchestrator.compile()

logger.info(
    "✅ LangGraph workflow compiled successfully with 4 nodes (linear flow)"
)
