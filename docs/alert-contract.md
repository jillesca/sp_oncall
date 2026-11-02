# Alert Contract

This document defines the alert labels that the
[xrd-observability-stack](https://github.com/CiscoDevNet/xrd-observability-stack)
emits (Prometheus rules in `prometheus/rules/xrd-alerts.yaml`, routed by Alertmanager)
and that sp_oncall relies on. The webhook proxy in [`webhook/`](../webhook/) parses
these labels (`event_type`, `affected_object_type`, `protocol`, `name`,
`neighbor_address`, `network_instance`, `source`) into a `NetworkAlert`
(`webhook/schema.py`), and `src/util/skill_routing.py` selects investigation skills
from `event_type`.

Adapted from `docs/tasks/alert-use-cases.md` in xrd-observability-stack at
`1fc9dce171f55a10e806fceeafa4308ecfa5dcbc`. Instructions that only apply to building
the observability stack (Grafana provisioning, dashboard annotations, Alertmanager and
Prometheus configuration, implementation checklists) were removed; they stay with that
repository. Scenarios SC-07 and SC-08 were annotation-only (dashboard context, no
alert) and are not part of the contract.

If you change a label name or an `event_type` value in the stack, update the
`NetworkAlert` parsing in `webhook/schema.py` and the skills in `skills/`.

## Alertmanager payload compatibility

Alertmanager sends webhooks in a format nearly identical to Grafana's (an `alerts[]`
array with `labels`, `annotations`, `status`, `startsAt`). The `GrafanaWebhook` and
`GrafanaAlert` Pydantic models in `webhook/schema.py` set `extra="allow"`, so they
accept Alertmanager's additional fields (`groupKey`, `groupLabels`, `commonLabels`,
`externalURL`, ...) without changes. Alertmanager labels the device as `source`; the
proxy falls back to it when `target` is absent.

One difference: Alertmanager does not include `values` (metric values at alert time).
`metric_value` in `NetworkAlert` is therefore `None` for all Alertmanager-sourced
alerts. This is expected: agents retrieve current metric values with gNMIBuddy tools.

Alertmanager groups alerts (`group_by` in the stack's `alertmanager.yaml`) and inhibits
symptom alerts while a root-cause alert is firing. The proxy investigates only the
first alert of a payload and logs a warning when a payload carries more than one.

Verify the contract without the stack by sending a sample alert to the proxy:
`make test-alert` (see [README](../README.md#optional-observability-integration)).

## Context: gNMIBuddy MCP tools (used by sp_oncall agents)

| Tool category | Relevant commands                                        |
| ------------- | -------------------------------------------------------- |
| `device`      | `info`, `profile` — device role and system state         |
| `network`     | `routing` (BGP/ISIS), `interface`, `mpls`, `vpn`         |
| `topology`    | `neighbors`, `adjacency`, `network` — full topology view |
| `ops`         | `logs` — retrieve and filter device logs by keyword      |

## Alert Catalog

Each scenario below is structured as:

1. **Trigger** — the Prometheus condition that fires the alert
2. **NetworkAlert labels** — the labels the webhook proxy maps onto the `NetworkAlert`
3. **Investigation guidance** — what gNMIBuddy tools sp_oncall should call first

Scenarios marked **[OUT OF SCOPE]** are catalogued for reference only: they cannot be
triggered in the sandbox environment and the stack does not emit them.

---

### SC-01: Interface Down — **[IN SCOPE]**

- **Trigger**: `openconfig_interfaces_interface_state_oper_status{name!~"Loopback.*|MgmtEth.*"} < 1`
- **event_type label**: `interface_state`
- **Agent investigation**: `gnmibuddy network interface`, then `gnmibuddy topology adjacency`

---

### SC-02: BGP Session Down — **[IN SCOPE]**

BGP peer connection goes from ESTABLISHED to any non-established state. The primary
BGP sessions in this topology are from xrd-1 and xrd-2 (PE routers) to xrd-8 (vRR).

**Trigger (Prometheus)**:

```promql
# connection-state values: bgp-st-estab = ESTABLISHED; others = not established
# Alert fires when any neighbor is NOT in established state
Cisco_IOS_XR_ipv4_bgp_oper_bgp_instances_instance_instance_active_default_vrf_neighbors_neighbor_connection_state != 1
```

**NetworkAlert labels**:

```
event_type: bgp_session_state
affected_object_type: bgp_neighbor
affected_object: <neighbor_address label from Prometheus>
protocol: bgp
network_instance: default
neighbor_device: null  # agents determine this via topology tools
```

**Agent investigation**:

1. `gnmibuddy network routing --device <device>` — full BGP neighbor table
2. `gnmibuddy topology adjacency --all-devices` — who lost peers
3. `gnmibuddy ops logs --device <device> --keyword BGP` — log context

---

### SC-03: Interface Flapping — **[IN SCOPE]**

An interface transitions up→down or down→up more than 3 times in a 5-minute window.
This indicates physical instability, not a clean maintenance shutdown.

**Trigger (Prometheus)**:

```promql
changes(openconfig_interfaces_interface_state_oper_status{name!~"Loopback.*|MgmtEth.*"}[5m]) > 3
```

**NetworkAlert labels**:

```
event_type: interface_flapping
affected_object_type: interface
affected_object: <name label>
protocol: null
```

**Agent investigation**:

1. `gnmibuddy network interface --device <device>` — current interface state and counters
2. `gnmibuddy ops logs --device <device> --keyword UPDOWN` — recent up/down events
3. `gnmibuddy topology neighbors --device <device>` — which peer is on that interface

---

### SC-04: High Interface Error Rate — **[IN SCOPE]**

Input or output error counter rate exceeds a threshold. Indicates physical-layer issues
(bad cable, SFP, or peer NIC) even while the interface remains operationally UP.

**Trigger (Prometheus)**:

```promql
rate(openconfig_interfaces_interface_state_counters_in_errors{name!~"Loopback.*|MgmtEth.*"}[5m]) > 10
```

**NetworkAlert labels**:

```
event_type: interface_errors
affected_object_type: interface
affected_object: <name label>
metric_value: <error rate from $values.B>
```

**Agent investigation**:

1. `gnmibuddy network interface --device <device>` — full counter state
2. `gnmibuddy topology neighbors --device <device>` — identify the peer on that link
3. `gnmibuddy network interface --device <neighbor>` — check peer-side counters

---

### SC-05: Memory Pressure — **[OUT OF SCOPE]**

> Cannot be triggered in the sandbox environment. XRd containers do not consume enough
> memory to breach a meaningful threshold during a demo. Documented for reference only.
> Do not implement.

Node memory free percentage drops below a threshold. Uses the already-collected
`xrd-system-health` subscription (XR native memory summary YANG).

**Trigger (Prometheus)**:

```promql
# Free memory as percentage of total RAM — alert below 15%
(
  Cisco_IOS_XR_nto_misc_oper_memory_summary_nodes_node_summary_free_application_memory
  /
  Cisco_IOS_XR_nto_misc_oper_memory_summary_nodes_node_summary_ram_memory
) * 100 < 15
```

**NetworkAlert labels**:

```
event_type: memory_pressure
affected_object_type: system
affected_object: null
metric_value: <free memory percentage>
```

**Agent investigation**:

1. `gnmibuddy device info --device <device>` — system health snapshot
2. `gnmibuddy ops logs --device <device> --keyword memory` — log context

---

### SC-06: Traffic Saturation (High Interface Throughput) — **[OUT OF SCOPE]**

> No traffic generator is available in this sandbox. XRd software interfaces carry only
> control-plane traffic (BGP, ISIS) during the demo — far below any meaningful threshold.
> Documented for reference only. Do not implement.

Outbound throughput on a non-loopback interface exceeds 80% of assumed link capacity.
Useful for detecting unexpected traffic spikes or traffic engineering failures routing
traffic over a congested path.

> **Caveat**: XRd GigabitEthernet interfaces in the sandbox are software interfaces;
> actual capacity is CPU-bound, not 1 Gbps. Tune the threshold to a realistic value
> for your environment (e.g., 50 Mbps = 50,000,000 bps). Adjust after running
> baseline traffic.

**Trigger (Prometheus)**:

```promql
rate(openconfig_interfaces_interface_state_counters_out_octets{name!~"Loopback.*|MgmtEth.*"}[5m]) * 8 > 50000000
```

**NetworkAlert labels**:

```
event_type: traffic_saturation
affected_object_type: interface
affected_object: <name label>
metric_value: <bps from $values.B>
```

**Agent investigation**:

1. `gnmibuddy network mpls --device <device>` — SR label forwarding table
2. `gnmibuddy network interface --device <device>` — traffic distribution per interface
3. `gnmibuddy topology network` — full topology to find alternate paths
4. `gnmibuddy network routing --device <device>` — routing table changes

---

### SC-09: Topology Degraded (Multiple Adjacencies Lost) — **[IN SCOPE]**

When 3 or more ISIS adjacencies drop simultaneously, the topology has degraded beyond
a single link failure. This is a higher-severity composite signal indicating either a
device failure or a partitioning event.

**Trigger (Prometheus)**:

```promql
# Count adjacency rows whose state is NOT the UP value
count(
  Cisco_IOS_XR_clns_isis_oper_isis_instances_instance_neighbors_neighbor_neighbor_state{neighbor_state!="isis-adj-1-state"}
) >= 3
```

**NetworkAlert labels**:

```
event_type: topology_degraded
affected_object_type: topology
affected_object: null
protocol: isis
metric_value: <count of adjacencies down>
```

**Agent investigation** (scope is topology-wide, not device-specific):

1. `gnmibuddy topology network` — full topology snapshot
2. `gnmibuddy topology adjacency --all-devices` — which links are down across all devices
3. `gnmibuddy device info --all-devices` — check all devices responding
4. `gnmibuddy ops logs --all-devices --keyword ISIS` — correlate reasons

---

### SC-10: MPLS Label Pool Exhaustion [UNVERIFIED]

MPLS label allocation failure or pool critically low. Uses the `xrd-mpls-labels`
subscription (already collected).

**Trigger (Prometheus)**:

```promql
# Free labels as percentage of total — alert below 10%
(
  Cisco_IOS_XR_mpls_lsd_oper_mpls_lsd_label_summary_free_labels_count
  /
  (Cisco_IOS_XR_mpls_lsd_oper_mpls_lsd_label_summary_free_labels_count
   + Cisco_IOS_XR_mpls_lsd_oper_mpls_lsd_label_summary_in_use_labels_count)
) * 100 < 10
```

**NetworkAlert labels**:

```
event_type: mpls_label_exhaustion
affected_object_type: mpls_pool
metric_value: <free label percentage>
```

**Agent investigation**:

1. `gnmibuddy network mpls --device <device>` — current MPLS forwarding state
2. `gnmibuddy ops logs --device <device> --keyword MPLS` — allocation errors

---

## Demo Scenario Matrix

| Scenario trigger            | Alerts fired (reach sp_oncall)         | Inhibited (visible in AM, not forwarded) | Agents investigate                    |
| --------------------------- | -------------------------------------- | ---------------------------------------- | ------------------------------------- |
| `shutdown` one interface    | SC-01 (interface_state)                | ISIS adjacency-count, SC-03 (flapping)   | Interface → ISIS → topology           |
| Cascade ≥3 adjacencies      | SC-01 + SC-09 (separate groups)        | ISIS adjacency-count                     | Device + topology-wide                |
| BGP session drops           | SC-02 (bgp_session_state)              | —                                        | BGP neighbors → routing               |
| Repeated `shut/no shut`     | SC-03 (interface_flapping), then SC-01 | SC-03 inhibited once SC-01 fires         | Interface stability → peers           |
