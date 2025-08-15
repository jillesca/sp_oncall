from langgraph.graph import StateGraph, END

from schemas import GraphState
from nodes import (
    planner_node,
    llm_network_executor,
    objective_assessor_node,
    generate_llm_report_node,
    input_validator_node,
)
from configuration import Configuration


def decide_next_step(state: GraphState) -> str:
    """
    Determines the next step after the objective assessor.
    - If objective_achieved_assessment is True, proceed to report_generator.
    - If False (and retries are permissible), loop back to network_executor.
    """
    if state.get("objective_achieved_assessment"):
        return "report_generator"

    return "network_executor"


# Build the LangGraph workflow
orchestrator = StateGraph(
    state_schema=GraphState, context_schema=Configuration
)

# Add nodes to the workflow
orchestrator.add_node(node="input_validator_node", action=input_validator_node)
orchestrator.add_node(node="planner_node", action=planner_node)
orchestrator.add_node(node="network_executor", action=llm_network_executor)
orchestrator.add_node(
    node="objective_assessor", action=objective_assessor_node
)
orchestrator.add_node(node="report_generator", action=generate_llm_report_node)

# Define the workflow edges
orchestrator.set_entry_point(key="input_validator_node")
orchestrator.add_edge(start_key="input_validator_node", end_key="planner_node")
orchestrator.add_edge(start_key="planner_node", end_key="network_executor")
orchestrator.add_edge(
    start_key="network_executor", end_key="objective_assessor"
)

# Add conditional edge for retry loop
orchestrator.add_conditional_edges(
    source="objective_assessor",
    path=decide_next_step,
    path_map={
        "report_generator": "report_generator",
        "network_executor": "network_executor",
    },
)

orchestrator.add_edge(start_key="report_generator", end_key=END)

# Compile the workflow
app = orchestrator.compile()

print("LangGraph workflow compiled successfully with 4 nodes and retry loop.")
