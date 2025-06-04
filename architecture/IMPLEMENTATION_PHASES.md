# Agent Architecture: Phased Implementation Plan

This document outlines a phased approach to building the agent architecture described in `ARCHITECTURE.md`. Each phase represents a set of functionalities to be implemented, allowing for incremental development and testing.

## How to Use This Document

- Each phase has a checkbox to mark its status.
- Refer to `ARCHITECTURE.md` for detailed descriptions of nodes, state, and overall goals.
- The goal is to allow different agents/developers to pick up a phase, implement it, and then mark it as complete.

---

## Phase 1: Core State Definition & Basic Plan Loading

- **Status:** `[ ] To Do`
- **Objective:** Establish the foundational data structure (`GraphState`) and implement the initial part of the `Input Validator & Planner` node to load a predefined plan.
- **Key Tasks:**
  1.  Define the `GraphState` `TypedDict` as specified in `ARCHITECTURE.md`, including all fields (even if many are `Optional` initially).
  2.  Create a `plans/` directory.
  3.  Create at least two sample JSON plan files in `plans/` (e.g., `general_device_health_check.json`, `check_interface_status.json`) adhering to the specified format:
      ```json
      {
        "intent": "general_device_health_check",
        "description": "Performs a general health check on a device.",
        "steps": [
          "Check overall device CPU and memory utilization.",
          "Verify status of all critical hardware components.",
          "Review system logs for any recent critical errors."
        ]
      }
      ```
  4.  Implement the `Input Validator & Planner` node (or a function representing its core logic):
      - It should take a `user_query` (can be simple string) and a `device_name` (can be simple string).
      - Load a _hardcoded_ plan from one of the JSON files (e.g., always load `general_device_health_check.json` for now).
      - Populate the following fields in the `GraphState`:
        - `user_query` (from input)
        - `device_name` (from input)
        - `objective` (from the "description" field of the loaded plan)
        - `working_plan_steps` (from the "steps" array of the loaded plan)
        - `max_retries` (e.g., initialize to `3`)
        - `current_retries` (e.g., initialize to `0`)
        - Initialize other fields like `execution_results`, `tool_limitations_report`, etc., to empty lists or `None` as appropriate.
- **LLM Use:** None in this phase.
- **Outputs:** A populated `GraphState` object with initial plan details.

---

## Phase 2: Mocked Network Executor

- **Status:** `[ ] To Do`
- **Objective:** Implement the `Network Executor` node structure that can iterate through plan steps and simulate tool execution without actual network interaction or LLM-based interpretation.
- **Key Tasks:**
  1.  Implement the `Network Executor` node (or a function representing its logic).
  2.  Input: `GraphState` (specifically `working_plan_steps`, `device_name`).
  3.  Iterate through each `natural_language_instruction` in `working_plan_steps`.
  4.  For each step:
      - _Simulate_ execution: For example, print a message like "SIMULATING EXECUTION for step X on [device_name]: [natural_language_instruction]".
      - Create a mock `ExecutedToolCall` entry (e.g., `function="mock_tool"`, `params={"instruction": natural_language_instruction}`, `result={"status": "simulated success"}`, `error=None`).
      - Create a `StepExecutionResult` entry, including the `step_index`, `natural_language_instruction`, and the list of (mocked) `executed_calls`.
  5.  Append each `StepExecutionResult` to the `execution_results` list in the `GraphState`.
  6.  Populate `tool_limitations_report` with a placeholder string (e.g., "No actual tool calls made in this phase.") or leave as `None`.
- **LLM Use:** None in this phase.
- **Outputs:** `GraphState` updated with `execution_results` containing simulated data.

---

## Phase 3: Basic Report Generator (No LLM)

- **Status:** `[ ] To Do`
- **Objective:** Implement a `Report Generator` node that creates a simple, structured report based on the (mocked) execution results.
- **Key Tasks:**
  1.  Implement the `Report Generator` node (or a function).
  2.  Input: `GraphState` (specifically `objective`, `working_plan_steps`, `execution_results`, `tool_limitations_report`, `assessor_notes_for_final_report` which will be `None` for now).
  3.  Generate a basic `summary` (list of strings).
      - Example:
        - "Objective: [objective from state]"
        - "Plan Steps & Simulated Execution:"
        - For each step in `working_plan_steps` and its corresponding entry in `execution_results`:
          - "Step [index]: [natural_language_instruction]"
          - "Simulated Result: [details from mock ExecutedToolCall]"
        - "Tool Limitations: [tool_limitations_report from state]"
        - "Assessor Notes: [assessor_notes_for_final_report from state, or 'N/A']"
  4.  Update the `summary` field in the `GraphState`.
- **LLM Use:** None in this phase.
- **Outputs:** `GraphState` updated with a basic `summary`.

---

## Phase 4: Basic Objective Assessor (No LLM, No Retry)

- **Status:** `[ ] To Do`
- **Objective:** Implement the `Objective Assessor` node structure with minimal logic to allow the flow to proceed to the `Report Generator` without any actual assessment or retry mechanism.
- **Key Tasks:**
  1.  Implement the `Objective Assessor` node (or a function).
  2.  Input: `GraphState`.
  3.  Set `objective_achieved_assessment` to `True` (to always proceed to the report generator for now).
  4.  Set `assessor_notes_for_final_report` to a simple string like "Initial assessment pass-through. No detailed checks performed."
  5.  Ensure `assessor_feedback_for_retry` remains `None`.
  6.  `current_retries` should remain unchanged from its initial value.
- **LLM Use:** None in this phase.
- **Outputs:** `GraphState` updated with `objective_achieved_assessment = True` and basic `assessor_notes_for_final_report`.

---

## Phase 5: `gNMIBuddy` Integration - Device Validation & Simple Execution

- **Status:** `[ ] To Do`
- **Objective:** Integrate actual `gNMIBuddy` tool calls. The `Input Validator & Planner` will use `get_devices()`. The `Network Executor` will make _pre-determined/hardcoded_ `gNMIBuddy` calls for specific plan steps, replacing some mocks.
- **Key Tasks:**
  1.  Set up the `gNMIBuddy` tool environment and ensure it's callable (as per `ARCHITECTURE.md` tooling example, involving MCP). This might require a separate script for `gNMIBuddy` that the agent can invoke.
  2.  Modify `Input Validator & Planner`:
      - Integrate the call to `gNMIBuddy.get_devices()` to validate `device_name`.
      - If validation fails, the process should stop or handle the error appropriately (e.g., update state with an error message).
  3.  Modify `Network Executor`:
      - For one or two _specific_ natural language steps in your sample plans, replace the mock execution with actual calls to `gNMIBuddy` functions.
        - Example: If a step is "Check BGP neighbor status", map this to a call like `gNMIBuddy.get_routing_info(device_name=device_name, resource="bgp_neighbors")` (actual function and params depend on `gNMIBuddy`'s API).
        - This mapping will be rule-based or hardcoded for now, not LLM-driven.
      - Capture the actual `result` or `error` from `gNMIBuddy` into `ExecutedToolCall`.
      - Update `tool_limitations_report` if `gNMIBuddy` calls fail or if some steps still use mocks.
- **LLM Use:** None for tool selection in Network Executor. `Input Validator` uses `get_devices()` tool.
- **Outputs:** `GraphState` with `execution_results` containing some actual `gNMIBuddy` outputs/errors. `device_name` is validated.

---

## Phase 6: LLM-Powered Network Executor - Tool Selection & Parameterization

- **Status:** `[ ] To Do`
- **Objective:** Enhance the `Network Executor` to use an LLM to interpret natural language plan steps, dynamically select `gNMIBuddy` tool functions, and determine their parameters.
- **Key Tasks:**
  1.  Integrate an LLM with tool-use capabilities into the `Network Executor`.
  2.  Provide the LLM with the definitions of available `gNMIBuddy` functions (name, description, parameters).
  3.  For each `natural_language_instruction` in `working_plan_steps`:
      - The LLM interprets the instruction.
      - The LLM selects the appropriate `gNMIBuddy` function(s).
      - The LLM determines the parameters for the selected function(s).
      - The `Network Executor` executes the chosen function(s) via `gNMIBuddy`.
  4.  Record the LLM's chosen function, parameters, and the actual `gNMIBuddy` `result`/`error` in `ExecutedToolCall`.
  5.  Update `tool_limitations_report` based on LLM's inability to find a tool or actual execution failures.
- **LLM Use:** Heavy in `Network Executor` for understanding instructions, selecting tools, and forming parameters.
- **Outputs:** `GraphState` with `execution_results` fully driven by LLM-selected `gNMIBuddy` calls.

---

## Phase 7: LLM-Powered Report Generator - Summary Synthesis

- **Status:** `[ ] To Do`
- **Objective:** Enhance the `Report Generator` to use an LLM to synthesize a coherent, human-readable `summary` from the various state fields.
- **Key Tasks:**
  1.  Integrate an LLM into the `Report Generator`.
  2.  Provide the LLM with `objective`, `working_plan_steps`, `execution_results`, `tool_limitations_report`, and `assessor_notes_for_final_report`.
  3.  The LLM analyzes these inputs to generate a natural language `summary` that:
      - States the objective.
      - Highlights key findings relevant to the objective.
      - Clearly explains if the objective was not fully met, referencing limitations or assessor notes.
      - Summarizes errors or tool limitations encountered.
  4.  Update the `summary` field in `GraphState` with the LLM-generated text.
- **LLM Use:** Moderate to Heavy in `Report Generator` for synthesizing information into a report.
- **Outputs:** `GraphState` with an LLM-generated, comprehensive `summary`.

---

## Phase 8: LLM-Powered Objective Assessor & Retry Loop Implementation

- **Status:** `[ ] To Do`
- **Objective:** Implement the full logic of the `Objective Assessor` node, including LLM-based assessment and the retry loop.
- **Key Tasks:**
  1.  Integrate an LLM into the `Objective Assessor`.
  2.  The LLM compares `execution_results` against the `objective` and `working_plan_steps`.
  3.  Implement the decision logic:
      - If objective met: Set `objective_achieved_assessment = True`. Populate `assessor_notes_for_final_report`.
      - If objective not met but tool limitations are prohibitive: Set `objective_achieved_assessment = True`. Populate `assessor_notes_for_final_report` explaining why.
      - If objective not met and retry is feasible (`current_retries < max_retries`):
        - Set `objective_achieved_assessment = False`.
        - LLM generates `assessor_feedback_for_retry` to guide the `Network Executor`.
        - Increment `current_retries`.
        - The graph should loop back to the `Network Executor`.
      - If max retries reached: Set `objective_achieved_assessment = True`. Populate `assessor_notes_for_final_report` indicating max retries hit.
  4.  The `Network Executor` must be updated to accept and use `assessor_feedback_for_retry` when present.
- **LLM Use:** Moderate in `Objective Assessor` for comparing results to objective and generating retry feedback.
- **Outputs:** `GraphState` updated by the full `Objective Assessor` logic, potentially triggering retries or preparing for final report generation.

---

## Phase 9: Advanced Input Validator & Planner - Intent Parsing & Dynamic Plan Selection

- **Status:** `[ ] To Do`
- **Objective:** Enhance the `Input Validator & Planner` to dynamically parse user intent and select the appropriate plan, rather than using a hardcoded one.
- **Key Tasks:**
  1.  Develop a strategy for intent parsing from `user_query` (e.g., keyword matching, regex, or a small classification LLM).
  2.  Map recognized intents to plan filenames (e.g., "check bgp" intent maps to `check_bgp_neighbors.json`).
  3.  Modify the `Input Validator & Planner` to:
      - Parse intent from `user_query`.
      - Select the corresponding JSON plan file. If no specific plan matches, it could default to `general_device_health_check.json` or report an error.
      - Load the selected plan and populate `objective` and `working_plan_steps` accordingly.
- **LLM Use:** Optional/Minimal for intent classification if a simple LLM is chosen for this.
- **Outputs:** `GraphState` populated with a dynamically selected plan based on user input.

---

## Phase 10: Full Plan Suite Creation & Comprehensive Testing

- **Status:** `[ ] To Do`
- **Objective:** Create all specified JSON plan files and conduct thorough end-to-end testing of the entire system with various user queries and scenarios.
- **Key Tasks:**
  1.  Create all JSON plan files listed in `ARCHITECTURE.md` under "Initial Plans to Create" within the `plans/` directory, adhering to the content guidelines.
      - `check_bgp_neighbors.json`
      - `check_interface_status.json`
      - `review_pe_device.json`
      - `review_p_device.json`
      - `review_rr_device.json`
      - `troubleshoot_vpn_vrf.json`
      - `check_mpls_state.json`
  2.  Test the entire agent flow with a diverse set of user queries covering different intents and targeting various (mocked or real) devices.
  3.  Identify and fix bugs, refine LLM prompts for better tool selection/reporting/assessment, and improve plan instructions.
  4.  Evaluate the effectiveness of the retry loop and assessor feedback.
  5.  Ensure robust error handling throughout the agent.
- **LLM Use:** Testing and refinement of LLM interactions across all relevant nodes.
- **Outputs:** A fully implemented and tested agent capable of handling various network diagnostic queries based on predefined plans.

---
