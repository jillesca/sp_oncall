# SP Oncall Refactoring Plan

> Phased improvement plan for the SP Oncall LangGraph agent system.
> Each stage is a self-contained unit of work. Agents implementing a stage must
> verify their work by running `make install` and `pytest` after changes or any other terminal command needed.

---

## Phase 1 — Demo-Ready (Cisco Live, one week)

### Stage 1.1 — State Simplification

**Goal:** Slim down `GraphState` and remove dead code.

**Changes:**

1. In `src/schemas/state.py`:
   - Remove `dependencies: List[str]` from `Investigation`
   - Remove `InvestigationPriority` enum and `priority` field from `Investigation`
   - Remove `max_retries` and `current_retries` from `GraphState` (retry logic moves inside executor sub-graph)
   - Remove `assessment` from `GraphState` (moves inside per-device sub-graph)
   - Remove `historical_context` from `GraphState` (will be loaded from LangGraph Store in Phase 2; for now just remove from state — each node can load it independently if needed)
   - Remove `get_ready_investigations()` and `get_pending_investigations()` methods (dependencies gone)
   - Keep: `messages`, `investigations`

2. In `src/schemas/state.py`:
   - Remove `HistoricalContext` dataclass (Phase 2 replaces it with LangGraph Store)
   - Keep `Investigation` with: `device_name`, `role`, `objective`, `working_plan_steps`, `execution_results`, `status`, `report`, `error_details`
   - Keep `ExecutedToolCall` as-is

3. Delete `xrd_sandbox.json` from the project root.

4. Update all nodes that reference removed fields — fix imports and usages:
   - `src/nodes/assessor/context.py` — remove retry info section
   - `src/nodes/planner/context.py` — remove historical context references
   - `src/nodes/reporter/session.py` — deleted (historical context is fully removed)
   - `src/nodes/common/session_context.py` — deleted (historical context helper)
   - `src/nodes/assessor/state.py` — deleted (all functions operated on removed fields; will be recreated in Stage 1.2 for `DeviceState`)
   - `src/graph.py` — remove `decide_next_step` and wire executor → report_generator directly
     > **Decision (Option B):** Rather than keeping a no-op `decide_next_step`, the `objective_assessor` node was removed from the outer graph entirely and the flow was made linear now. Stage 1.2 only needs to add the per-device subgraph inside the executor — the outer graph is already in its final linear shape.

**Verification:**

```bash
make install && python -c "from schemas import GraphState; print('OK')" && pytest
```

---

### Stage 1.2 — Sub-Graph Per Device (Executor + Per-Device Assessor)

**Goal:** Replace the global executor→assessor→retry loop with a per-device sub-graph that retries internally.

**Changes:**

1. Create `src/nodes/executor/device_subgraph.py`:
   - Define a `DeviceState` dataclass: `investigation: Investigation`, `max_retries: int = 3`, `current_retry: int = 0`, `assessment: Optional[AssessmentOutput] = None`
   - Build a sub-graph: `execute_device → assess_device → (retry or done)`
   - `execute_device`: runs MCP agent for one device (extracted from current `execute_investigations_concurrently`)
   - `assess_device`: runs the assessor for that one device only (smaller context = faster)
   - Conditional edge: if `assessment.is_objective_achieved` or `current_retry >= max_retries` → done, else → `execute_device`

2. Modify `src/nodes/executor/core.py`:
   - `llm_network_executor` now:
     1. Gets all pending investigations
     2. Runs each device's sub-graph concurrently via `asyncio.gather`
     3. Returns updated investigations (all completed/failed)

3. Simplify `src/graph.py`:
   - Remove the `objective_assessor` node from the outer graph
   - Remove `decide_next_step` conditional edge
   - New graph: `input_validator → planner → network_executor → report_generator → END`
   - The executor internally handles retries — the outer graph is linear

4. The assessor node files (`src/nodes/assessor/`) remain but are called from within the sub-graph, not from the outer graph.

**Verification:**

```bash
pytest tests/nodes/test_executor.py tests/nodes/test_assessor.py
# Manual: trigger a test alert and confirm per-device retry in LangSmith traces
```

---

### Stage 1.3 — Plans to Skills Migration

**Goal:** Convert JSON plan files to agentskills.io Markdown format and implement alert-to-skill routing.

**Changes:**

1. Create `skills/` directory at project root (replaces `plans/`).

2. Convert each JSON plan to a Markdown skill file following [agentskills.io spec](https://agentskills.io/specification). Example for `check_interface_status.json` → `skills/check_interface_status.md`:

   ```markdown
   ---
   name: check_interface_status
   description: Verifies interface operational state, error counters, and utilization.
   tags: [interface, troubleshooting, health]
   ---

   # Check Interface Status

   ## Steps

   1. List all interfaces and their operational status...
      ...
   ```

3. Create `skills/skill_routing.py`:
   - A mapping from alert `event_type` to skill names:

     ```python
     ALERT_SKILL_ROUTING = {
         "interface_state": ["check_interface_status", "general_device_health_check"],
         "bgp_session_state": ["check_bgp_neighbors", "review_pe_device"],
         "isis_adjacency_count": ["check_interface_status", "review_p_device"],
         "topology_degraded": ["check_interface_status", "review_p_device"],
         "interface_flapping": ["check_interface_status"],
         "interface_errors": ["check_interface_status"],
     }
     ```

   - A function `get_skills_for_alert(event_type: str) -> List[str]` that returns filtered skills
   - A function `get_all_skills() -> List[str]` for the manual path

4. Update `src/nodes/planner/planning.py`:
   - Replace `load_available_plans()` (JSON loader) with a Markdown skill loader
   - Accept a `skill_filter: Optional[List[str]]` parameter
   - When alert context is present in the message, use the routing table to filter
   - When manual query, load all skills

5. Delete the `plans/` directory.

**Verification:**

```bash
python -c "from skills.skill_routing import get_skills_for_alert; print(get_skills_for_alert('interface_state'))"
pytest tests/nodes/test_planner.py
```

---

### Stage 1.4 — Prompts to Markdown Files

**Goal:** Move all prompts from Python string constants to Markdown files. Tailor them for the alert-driven investigation use case.

**Changes:**

1. Create `prompts/` directory at project root (replaces `src/prompts/`):
   - `prompts/device_discovery.md` — was `input_validator.md`; named for what it does: discover and profile devices from the trigger context
   - `prompts/planner.md`
   - `prompts/network_executor.md`
   - `prompts/objective_assessor.md`
   - `prompts/report_generator.md`
   - `prompts/learning_insights.md` — **deleted** (no node uses it; see YAGNI note below)

   > **YAGNI note:** `learning_insights.py` and `LearningInsights` schema (`src/schemas/learning_insights_schema.py`) are both dead code — defined but not used by any node. They were not migrated. If a learning-insights node is built in Phase 2, the prompt and schema should be written at that point with full context of the node's actual needs. The `LearningInsights` schema should be cleaned up in a separate task.

2. Convert each Python prompt string to Markdown. During conversion, **tailor the content**:
   - Remove generic boilerplate (the prompts are currently very verbose)
   - Add alert-awareness: when the input is an alert, the prompt should guide the agent to focus on root-cause analysis
   - Add explicit instructions about what context the agent receives and what it should produce
   - Keep prompts concise — shorter prompts = faster LLM response
   - Reference the device's role and the alert type when available
   - Remove instructions about things the agent can't do (e.g. reporter shouldn't say "I can kick off")
   - For the assessor: add per-device assessment framing (since it now runs per-device in the sub-graph)

3. Create `src/util/prompt_loader.py`:
   - A function `load_prompt(name: str) -> str` that reads from `prompts/{name}.md`
   - Cache loaded prompts in memory (they don't change at runtime)

4. Update all nodes to use `load_prompt()` instead of importing Python constants.

5. Delete `src/prompts/` directory (the Python module).

**Verification:**

```bash
python -c "from src.util.prompt_loader import load_prompt; print(load_prompt('planner')[:100])"
pytest
```

---

### Stage 1.5 — Configuration & Documentation

**Goal:** Clean up configuration, add env var support for new knobs, and write a quick-start guide.

**Changes:**

1. Update `src/configuration.py`:
   - Add `max_retries_per_device: int` field, read from `SP_ONCALL_MAX_RETRIES` env var (default: 3)
   - Keep `model` field as-is (LangGraph Studio UI integration)
   - Remove `max_search_results` if unused

2. Create/update `.env.example` with all configuration options:

   ```bash
   # Required
   OPENAI_API_KEY=
   LANGSMITH_API_KEY=
   LANGSMITH_PROJECT=sp_oncall
   LANGSMITH_TRACING=true

   # Optional — SP Oncall settings
   SP_ONCALL_LOG_LEVEL=info
   SP_ONCALL_MAX_RETRIES=3
   SP_ONCALL_DRY_RUN=false
   ```

3. Update `README.md`:
   - Rewrite the Quick Start to reflect new project structure (skills, prompts as markdown, no xrd_sandbox.json)
   - Add a "Configuration Reference" section listing all `SP_ONCALL_*` env vars
   - Add a "Demo Workflow" section documenting the Thread-per-Alert flow:
     1. Alert fires → webhook POST → LangGraph creates thread
     2. Open LangGraph Studio → join thread by ID
     3. Follow up with manual queries in same thread
   - Reference `CONTEXT.md` for domain glossary

4. Create `scripts/test_alert.sh`:
   - Sample curl commands to POST fake alerts to the webhook container
   - One command per alert type (`XRdInterfaceDown`, `XRdBGPSessionDown`, `XRdISISAdjacencyDown`, `XRdTopologyDegraded`, `XRdInterfaceFlapping`, `XRdInterfaceHighErrorRate`)
   - Include a comment explaining each field

**Verification:**

```bash
bash scripts/test_alert.sh --dry-run  # just prints the curl commands
python -c "from configuration import Configuration; c = Configuration.from_context(); print(c)"
```

---

### Stage 1.6 — Validation Gate Utility

**Goal:** Add a reusable structured output validation utility that retries on malformed output without crashing.

**Changes:**

1. Create `src/util/validation.py`:

   ```python
   def validate_structured_output(
       raw_text: str,
       schema,
       model,
       validators: List[Callable],
       max_attempts: int = 2,
   ):
       """
       Parse raw_text into schema using model.with_structured_output().
       Run validators on the result. If validation fails, retry with
       feedback up to max_attempts. Never raises — returns best-effort result.

       Args:
           raw_text: The LLM output text to parse
           schema: The dataclass/pydantic schema to parse into
           model: The LLM model to use for parsing
           validators: List of callables that take the parsed result and return
                      a list of violation strings (empty = valid)
           max_attempts: Max parsing attempts (default 2, so 3 total with initial)

       Returns:
           Tuple of (parsed_result, list_of_violations)
           If all attempts fail, returns (last_result, remaining_violations)
       """
   ```

2. Create sample validators for existing schemas:
   - `validate_planning_response(result) -> List[str]`: checks device_name non-empty, working_plan_steps non-empty
   - `validate_investigation_planning(result) -> List[str]`: checks devices list non-empty, each device has name

3. Integrate into the planner and input_validator nodes (replace direct `with_structured_output` calls).

**Verification:**

```bash
pytest tests/  # existing tests pass
python -c "from src.util.validation import validate_structured_output; print('OK')"
```

---

## Phase 2 — Post-Demo Improvements

> **Note — README full rewrite:** The README was surgically updated in Stage 1.5 (Quick Start, Configuration Reference, Demo Workflow). A full rewrite is deferred here. At the end of Phase 2, rewrite the complete README to reflect the final architecture: linear outer graph, per-device sub-graph with retry loop, skills and prompts as Markdown files, and the updated mermaid sequence diagram.

### Stage 2.1 — Device Profiles via LangGraph Store

**Goal:** Implement cross-thread device memory using LangGraph's built-in Store.

**Changes:**

1. Add `store: BaseStore` parameter to nodes that need device context (planner, executor, reporter).

2. Create `src/util/device_store.py`:
   - `async def get_device_profile(store, device_name) -> dict` — reads from namespace `("device_profiles", device_name)`
   - `async def update_device_profile(store, device_name, static_facts=None, dynamic_facts=None)` — merges new facts
   - Static facts: role, ISIS area, BGP AS, direct neighbours, interfaces
   - Dynamic facts: last_alert, last_known_state, last_investigation_summary

3. Update the executor sub-graph:
   - Before executing: load device profile from Store, inject into prompt context
   - After completing: update device profile with dynamic facts (last alert, findings)

4. Update the reporter:
   - After generating report: write dynamic facts to each investigated device's profile

**Verification:**

```bash
# Start langgraph dev, trigger alert, check Store contents in LangGraph Studio
pytest
```

---

### Stage 2.2 — Two Model Slots + OpenRouter

**Goal:** Support a "main" model for reasoning and a "fast" model for structured output parsing. Enable OpenRouter as a provider.

**Changes:**

1. Update `src/configuration.py`:
   - Add `fast_model` field (default: `openai/gpt-4o-mini`) read from `SP_ONCALL_FAST_MODEL` env var
   - Keep `model` as the main reasoning model
   - Add OpenRouter models to `LLMModel` enum (e.g. `openrouter/anthropic/claude-sonnet-4`)

2. Update `src/util/llm.py`:
   - Add `load_fast_model()` function
   - For OpenRouter: use `ChatOpenAI(openai_api_base="https://openrouter.ai/api/v1", openai_api_key=OPENROUTER_API_KEY, model_name=...)`
   - Consult LangChain docs for `init_chat_model` with OpenRouter — provider string may be `openai` with base_url override

3. Update all structured output parsing calls to use `load_fast_model()` instead of `load_model()`.

4. Update `.env.example`:

   ```bash
   SP_ONCALL_FAST_MODEL=openai/gpt-4o-mini
   OPENROUTER_API_KEY=  # optional, only if using openrouter/ models
   ```

**Verification:**

```bash
# Test with OpenAI fast model (no OpenRouter needed initially)
SP_ONCALL_FAST_MODEL=openai/gpt-4o-mini make run
# Then test with OpenRouter model
```

---

### Stage 2.3 — Schema Simplification for Multi-Provider Support

**Goal:** Flatten structured output schemas so more LLM providers can handle them reliably.

**Changes:**

1. Simplify `InvestigationPlanningResponse`:
   - Current: nested `List[DeviceToInvestigate]` with sub-fields
   - Target: flat structure or single-device response (call once per device if needed)

2. Simplify `PlanningResponse`:
   - Current: nested `List[DevicePlan]`
   - Target: single `DevicePlan` per call (the planner runs once per device in the sub-graph)

3. Review `LearningInsights` — already flat, likely fine as-is.

4. Test with at least 2 providers (OpenAI + one OpenRouter model) to confirm compatibility.

**Verification:**

```bash
pytest
# Manual: run full pipeline with openrouter/anthropic/claude-sonnet-4 as main model
```

---

### Stage 2.4 — Historical Context Per-Device

**Goal:** Replace global historical context with per-device history linked to Device Profiles.

**Changes:**

1. Remove the old `HistoricalContext` pattern entirely (if any stubs remain from Stage 1.1).

2. In `src/util/device_store.py`, add:
   - `async def get_device_history(store, device_name, limit=5) -> List[dict]` — returns last N investigation summaries
   - `async def append_device_history(store, device_name, summary: dict)` — appends after each run

3. Update the executor sub-graph prompt builder:
   - Inject last 3 investigation summaries for the target device as "previous findings"
   - This replaces the old global `historical_context` injection

4. Update the reporter:
   - After report generation, call `append_device_history()` for each investigated device

**Verification:**

```bash
# Trigger same device alert twice, verify second run's prompt includes first run's findings
pytest
```

---

## Implementation Notes for Agents

### General Rules

- **Always verify**: After each stage, run `make install && pytest`. If tests fail, fix them before moving on.
- **Terminal verification**: Use the terminal to confirm imports work and the graph compiles.
- **Don't break the demo flow**: The webhook → LangGraph → Studio flow must keep working throughout. If unsure, test with `scripts/test_alert.sh`.
- **Preserve the outer contract**: The LangGraph API expects `{"messages": [{"type": "human", "content": "..."}]}` as input. Don't change this.
- **Preserve LangGraph Studio integration**: The `Configuration` class with `__template_metadata__` enables the model selector in Studio. Keep it.

### Key File Locations

| What                     | Where                                                                                               |
| ------------------------ | --------------------------------------------------------------------------------------------------- |
| Graph definition         | `src/graph.py`                                                                                      |
| State schemas            | `src/schemas/state.py`                                                                              |
| Assessment schema        | `src/schemas/assessment_schema.py`                                                                  |
| Configuration            | `src/configuration.py`                                                                              |
| MCP client               | `src/mcp_client.py`                                                                                 |
| Model loading            | `src/util/llm.py`                                                                                   |
| Node implementations     | `src/nodes/{node_name}/`                                                                            |
| Current prompts (Python) | `src/prompts/`                                                                                      |
| Current plans (JSON)     | `plans/`                                                                                            |
| Tests                    | `tests/`                                                                                            |
| Webhook container        | `/Users/jillesca/DevNet/cisco_live/26clus/xrd-observability-stack/webhook/`                         |
| Alert rules              | `/Users/jillesca/DevNet/cisco_live/26clus/xrd-observability-stack/prometheus/rules/xrd-alerts.yaml` |
| gNMIBuddy MCP            | `/Users/jillesca/DevNet/cisco_live/25clus/gNMIBuddy/`                                               |
| Domain glossary          | `CONTEXT.md`                                                                                        |

### XRd Sandbox Topology Reference

```
               xrd-7 (PCE)
               /           \
           xrd-3 ——— xrd-4
            / |           | \
src — xrd-1   |           |   xrd-2 — dst
            \ |           | /
           xrd-5 ——— xrd-6
               \           /
               xrd-8 (vRR)
```

- xrd-1, xrd-2: PE (Provider Edge)
- xrd-3, xrd-4, xrd-5, xrd-6: P (Provider core)
- xrd-7: PCE (Path Computation Element)
- xrd-8: vRR (virtual Route Reflector)

### Alert Types (from Prometheus rules)

| Alert                     | event_type           | Fires when                             |
| ------------------------- | -------------------- | -------------------------------------- |
| XRdInterfaceDown          | interface_state      | Non-loopback interface oper_status < 1 |
| XRdISISAdjacencyDown      | isis_adjacency_count | Any ISIS adjacency not UP              |
| XRdTopologyDegraded       | topology_degraded    | ≥3 ISIS adjacencies down               |
| XRdBGPSessionDown         | bgp_session_state    | BGP connection_state ≠ 1 (ESTABLISHED) |
| XRdInterfaceFlapping      | interface_flapping   | >3 state changes in 5min               |
| XRdInterfaceHighErrorRate | interface_errors     | >10 errors/sec sustained 60s           |

### Demo Scenario (Primary)

1. Shut down an interface on xrd-3 (or xrd-5)
2. Prometheus detects `XRdInterfaceDown` (15s)
3. Alertmanager forwards to Grafana webhook
4. Webhook container receives alert, POSTs to LangGraph `/runs`
5. sp_oncall graph runs: validates alert → plans investigation → executes gNMI queries → assesses → reports
6. Presenter joins thread in LangGraph Studio, reviews report, asks follow-up questions
