from langgraph.graph import StateGraph, END

from sp_oncall.schemas import GraphState
from sp_oncall.planner import planner_node
from sp_oncall.configuration import Configuration
from sp_oncall.executor import llm_network_executor
from sp_oncall.assessor import objective_assessor_node
from sp_oncall.reporter import generate_llm_report_node
from sp_oncall.input_validator import input_validator_node


def decide_next_step(state: GraphState):
    """
    Determines the next step after the objective assessor.
    - If objective_achieved_assessment is True, proceed to report_generator.
    - If False (and retries are permissible), loop back to network_executor.
    """
    if state.get("objective_achieved_assessment"):
        return "report_generator"
    else:
        return "network_executor"


# Build the LangGraph workflow
orchestrator = StateGraph(GraphState, config_schema=Configuration)

# Add nodes to the workflow
orchestrator.add_node("input_validator_node", input_validator_node)
orchestrator.add_node("planner_node", planner_node)
orchestrator.add_node("network_executor", llm_network_executor)
orchestrator.add_node("objective_assessor", objective_assessor_node)
orchestrator.add_node("report_generator", generate_llm_report_node)

# Define the workflow edges
orchestrator.set_entry_point("input_validator_node")
orchestrator.add_edge("input_validator_node", "planner_node")
orchestrator.add_edge("planner_node", "network_executor")
orchestrator.add_edge("network_executor", "objective_assessor")

# Add conditional edge for retry loop
orchestrator.add_conditional_edges(
    "objective_assessor",
    decide_next_step,
    {
        "report_generator": "report_generator",
        "network_executor": "network_executor",
    },
)

orchestrator.add_edge("report_generator", END)

# Compile the workflow
app = orchestrator.compile()

print("LangGraph workflow compiled successfully with 4 nodes and retry loop.")
