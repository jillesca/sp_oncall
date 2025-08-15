from langgraph.graph import StateGraph, END

from nodes import (
    planner_node,
    llm_network_executor,
    input_validator_node,
    objective_assessor_node,
    generate_llm_report_node,
)
from schemas import GraphState
from configuration import Configuration


def decide_next_step(state: GraphState) -> str:
    """
    Router function for the graph.

    Uses the objective_achieved field to decide whether to continue
    the executor/assessor loop or proceed to report generation.

    Args:
        state: The current graph state

    Returns:
        The name of the next node to execute
    """
    if state.objective_achieved_assessment:
        return "report_generator"
    else:
        return "network_executor"


orchestrator = StateGraph(
    state_schema=GraphState, context_schema=Configuration
)

orchestrator.add_node(node="input_validator_node", action=input_validator_node)
orchestrator.add_node(node="planner_node", action=planner_node)
orchestrator.add_node(node="network_executor", action=llm_network_executor)
orchestrator.add_node(
    node="objective_assessor", action=objective_assessor_node
)
orchestrator.add_node(node="report_generator", action=generate_llm_report_node)

orchestrator.set_entry_point(key="input_validator_node")
orchestrator.add_edge(start_key="input_validator_node", end_key="planner_node")
orchestrator.add_edge(start_key="planner_node", end_key="network_executor")
orchestrator.add_edge(
    start_key="network_executor", end_key="objective_assessor"
)

orchestrator.add_conditional_edges(
    source="objective_assessor",
    path=decide_next_step,
    path_map={
        "report_generator": "report_generator",
        "network_executor": "network_executor",
    },
)

orchestrator.add_edge(start_key="report_generator", end_key=END)

app = orchestrator.compile()

print("LangGraph workflow compiled successfully with 4 nodes and retry loop.")
