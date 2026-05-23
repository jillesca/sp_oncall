# Domain Glossary — SP Oncall

> Pure glossary. No implementation details, specs, or decisions here.
> Decisions live in `docs/adr/`. Implementation plans live in `docs/`.

---

## Entry Point

The way a user or external system initiates an investigation.

Two kinds exist:

- **Alert Entry Point** — an observability system (Grafana/Alertmanager) fires a webhook that triggers the graph automatically.
- **Manual Entry Point** — a human types a query directly (via LangGraph Studio, CLI, or future chat GUI).

Both are first-class. The alert path is the primary demo path; the manual path supports follow-up questions, development testing, and a future chat interface.

---

## Investigation

The unit of work for a single network device. An investigation has a lifecycle
(pending → in-progress → completed / failed / skipped), an objective, a plan, execution
results, and a final report. Multiple investigations may run concurrently within one Run.

---

## Run

A single end-to-end execution of the sp_oncall graph, from entry point to final report.
Triggered either by an Alert Entry Point or a Manual Entry Point.

---

## Thread

A LangGraph persistent conversation context identified by a `thread_id`. A Thread holds
full graph state across multiple Runs and messages, enabling conversation continuity.

The canonical demo flow:

1. An Alert fires → webhook POSTs to `/runs` → LangGraph creates a new Thread and starts
   the graph in the background.
2. The presenter opens LangGraph Studio and joins that Thread (by `thread_id`).
3. Follow-up manual queries are sent into the same Thread — agents have full access to
   the investigation state produced in step 1.

This is the **Thread-per-Alert** continuity model. Device Profiles complement it by
providing cross-Thread (cross-session) memory for the same physical device.

---

## Alert

A structured notification produced by the observability system (Prometheus → Alertmanager →
Grafana → webhook) describing a network event. Parsed into a `NetworkAlert` before being
handed to the graph. Contains: alert name, severity, timestamp, affected device, affected
object, event type, and optional protocol / network-instance / neighbor fields.

---

## Device Profile

Cross-Thread, per-device knowledge stored in the LangGraph Store (built-in key-value
store, no external DB required). Not committed to the repository — the repo remains
topology-agnostic.

Two layers:

- **Static facts** — role, IGP area, BGP AS, direct neighbours with interface names,
  topology position. Discovered on first investigation via gNMIBuddy and cached.
- **Dynamic facts** — last alert seen, last known issue, confirmed healthy/degraded
  state. Updated by the reporter at the end of each Run.

Profiles build up organically: the first Run for a device is a discovery run; subsequent
Runs benefit from cached profile data.

---

## Skill

A reusable investigation strategy for a specific intent (e.g. "check BGP neighbors").
Stored as a Markdown file in the `skills/` directory following the agentskills.io specification.
The planner selects relevant skills based on the alert's `event_type` (see `src/util/skill_routing.py`).

---

## Historical Context

Cross-Run memory per device. The last N investigation summaries for each device are stored
in its Device Profile (via `append_device_history` / `get_device_history` in `device_store.py`)
and injected into the executor context on subsequent Runs. This replaces the old global
historical context approach.

---

## Topology (XRd Sandbox)

The specific Cisco DevNet XRd Sandbox segment-routing topology used for demos:

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

Device roles:

- **xrd-1, xrd-2** — PE (Provider Edge) — customer-facing
- **xrd-3, xrd-4, xrd-5, xrd-6** — P (Provider core)
- **xrd-7** — PCE (Path Computation Element)
- **xrd-8** — vRR (virtual Route Reflector)
