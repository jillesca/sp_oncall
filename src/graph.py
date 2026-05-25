from langgraph.graph import StateGraph, END
from langgraph.store.memory import InMemoryStore

from nodes import (
    input_validator_node,
    rca_assessor_node,
    investigation_report_node,
)
from nodes.executor import (
    context_device_subgraph,
    primary_device_subgraph,
    context_dispatcher,
    primary_dispatcher,
    route_from_input_validator,
    route_after_context_phase,
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
orchestrator.add_node(node="context_dispatcher", action=context_dispatcher)
orchestrator.add_node(node="context_device_subgraph", action=context_device_subgraph)
orchestrator.add_node(node="primary_dispatcher", action=primary_dispatcher)
orchestrator.add_node(node="primary_device_subgraph", action=primary_device_subgraph)
orchestrator.add_node(node="rca_assessor_node", action=rca_assessor_node)
orchestrator.add_node(node="report_generator", action=investigation_report_node)

orchestrator.set_entry_point(key="input_validator_node")

orchestrator.add_conditional_edges(
    "input_validator_node",
    route_from_input_validator,
    ["context_dispatcher", "primary_dispatcher", "rca_assessor_node"],
)
orchestrator.add_conditional_edges(
    "context_device_subgraph",
    route_after_context_phase,
    ["primary_dispatcher", "rca_assessor_node"],
)
orchestrator.add_edge(start_key="primary_device_subgraph", end_key="rca_assessor_node")
orchestrator.add_edge(start_key="rca_assessor_node", end_key="report_generator")
orchestrator.add_edge(start_key="report_generator", end_key=END)

app = orchestrator.compile(store=InMemoryStore())

logger.info(
    "✅ LangGraph workflow compiled successfully: "
    "input_validator → context_dispatcher → [context_device_subgraph × N] "
    "→ primary_dispatcher → [primary_device_subgraph × M] "
    "→ rca_assessor → report_generator"
)
