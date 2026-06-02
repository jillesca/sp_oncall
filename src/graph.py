from langgraph.graph import StateGraph, END
from langgraph.store.memory import InMemoryStore

from nodes import (
    input_validator_node,
    rca_assessor_node,
    investigation_report_node,
)
from nodes.executor import (
    context_investigation_subgraph,
    primary_investigation_subgraph,
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
orchestrator.add_node(
    node="context_investigation", action=context_investigation_subgraph
)
orchestrator.add_node(
    node="primary_investigation", action=primary_investigation_subgraph
)
orchestrator.add_node(node="rca_assessor_node", action=rca_assessor_node)
orchestrator.add_node(
    node="report_generator", action=investigation_report_node
)

orchestrator.set_entry_point(key="input_validator_node")
orchestrator.add_edge(
    start_key="input_validator_node", end_key="context_investigation"
)
orchestrator.add_edge(
    start_key="context_investigation", end_key="primary_investigation"
)
orchestrator.add_edge(
    start_key="primary_investigation", end_key="rca_assessor_node"
)
orchestrator.add_edge(
    start_key="rca_assessor_node", end_key="report_generator"
)
orchestrator.add_edge(start_key="report_generator", end_key=END)

app = orchestrator.compile(store=InMemoryStore())

logger.info(
    "✅ LangGraph workflow compiled: "
    "input_validator → context_investigation "
    "→ primary_investigation → rca_assessor → report_generator"
)
