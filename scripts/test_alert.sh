#!/usr/bin/env bash
# Send a fake Grafana-format alert to the webhook container to trigger an sp_oncall investigation.
#
# Usage:
#   bash scripts/test_alert.sh [--dry-run] [alert_type]
#
# alert_type: interface_down | bgp_down | isis_down | topology_degraded |
#             interface_flapping | interface_errors
#
# --dry-run: Print the curl commands without sending them.
#
# Override the webhook URL via the WEBHOOK_URL env var:
#   WEBHOOK_URL=http://localhost:9090/alert bash scripts/test_alert.sh interface_down

set -euo pipefail

WEBHOOK_URL="${WEBHOOK_URL:-http://localhost:8080/alert}"
DRY_RUN=false
ALERT_TYPE="${1:-}"

if [[ "${1:-}" == "--dry-run" ]]; then
    DRY_RUN=true
    ALERT_TYPE="${2:-}"
fi

# ── Alert payload builders ────────────────────────────────────────────────────

alert_interface_down() {
    # XRdInterfaceDown — non-loopback interface oper_status drops to 0
    cat <<'EOF'
{
  "receiver": "sp_oncall",
  "status": "firing",
  "title": "XRdInterfaceDown",
  "alerts": [
    {
      "status": "firing",
      "labels": {
        "alertname": "XRdInterfaceDown",
        "severity": "critical",
        "event_type": "interface_state",
        "target": "xrd-3",
        "name": "GigabitEthernet0/0/0/0",
        "affected_object_type": "interface"
      },
      "annotations": {
        "summary": "Interface GigabitEthernet0/0/0/0 down on xrd-3",
        "description": "Non-loopback interface oper_status dropped to 0 on xrd-3"
      },
      "startsAt": "2026-05-23T14:00:00Z",
      "values": { "oper_status": "0" }
    }
  ]
}
EOF
}

alert_bgp_down() {
    # XRdBGPSessionDown — BGP connection_state != 1 (ESTABLISHED)
    cat <<'EOF'
{
  "receiver": "sp_oncall",
  "status": "firing",
  "title": "XRdBGPSessionDown",
  "alerts": [
    {
      "status": "firing",
      "labels": {
        "alertname": "XRdBGPSessionDown",
        "severity": "critical",
        "event_type": "bgp_session_state",
        "target": "xrd-1",
        "neighbor_address": "10.0.0.8",
        "network_instance": "default",
        "protocol": "BGP",
        "affected_object_type": "bgp_neighbor"
      },
      "annotations": {
        "summary": "BGP session to 10.0.0.8 down on xrd-1",
        "description": "BGP connection_state is not ESTABLISHED on xrd-1 toward neighbor 10.0.0.8"
      },
      "startsAt": "2026-05-23T14:00:00Z",
      "values": { "connection_state": "0" }
    }
  ]
}
EOF
}

alert_isis_down() {
    # XRdISISAdjacencyDown — any ISIS adjacency not UP
    cat <<'EOF'
{
  "receiver": "sp_oncall",
  "status": "firing",
  "title": "XRdISISAdjacencyDown",
  "alerts": [
    {
      "status": "firing",
      "labels": {
        "alertname": "XRdISISAdjacencyDown",
        "severity": "warning",
        "event_type": "isis_adjacency_count",
        "target": "xrd-3",
        "name": "GigabitEthernet0/0/0/0",
        "protocol": "ISIS",
        "affected_object_type": "isis_adjacency"
      },
      "annotations": {
        "summary": "ISIS adjacency down on xrd-3",
        "description": "At least one ISIS adjacency is not UP on xrd-3"
      },
      "startsAt": "2026-05-23T14:00:00Z",
      "values": { "adjacency_count": "0" }
    }
  ]
}
EOF
}

alert_topology_degraded() {
    # XRdTopologyDegraded — 3 or more ISIS adjacencies down across the topology
    cat <<'EOF'
{
  "receiver": "sp_oncall",
  "status": "firing",
  "title": "XRdTopologyDegraded",
  "alerts": [
    {
      "status": "firing",
      "labels": {
        "alertname": "XRdTopologyDegraded",
        "severity": "critical",
        "event_type": "topology_degraded",
        "target": "xrd-3",
        "protocol": "ISIS",
        "affected_object_type": "topology"
      },
      "annotations": {
        "summary": "SR topology degraded — 3+ ISIS adjacencies down",
        "description": "3 or more ISIS adjacencies are down, indicating significant topology degradation"
      },
      "startsAt": "2026-05-23T14:00:00Z",
      "values": { "down_adjacency_count": "3" }
    }
  ]
}
EOF
}

alert_interface_flapping() {
    # XRdInterfaceFlapping — more than 3 state changes in a 5-minute window
    cat <<'EOF'
{
  "receiver": "sp_oncall",
  "status": "firing",
  "title": "XRdInterfaceFlapping",
  "alerts": [
    {
      "status": "firing",
      "labels": {
        "alertname": "XRdInterfaceFlapping",
        "severity": "warning",
        "event_type": "interface_flapping",
        "target": "xrd-5",
        "name": "GigabitEthernet0/0/0/1",
        "affected_object_type": "interface"
      },
      "annotations": {
        "summary": "Interface GigabitEthernet0/0/0/1 flapping on xrd-5",
        "description": "More than 3 interface state changes detected in a 5-minute window on xrd-5"
      },
      "startsAt": "2026-05-23T14:00:00Z",
      "values": { "state_changes": "5" }
    }
  ]
}
EOF
}

alert_interface_errors() {
    # XRdInterfaceHighErrorRate — more than 10 errors/sec sustained for 60s
    cat <<'EOF'
{
  "receiver": "sp_oncall",
  "status": "firing",
  "title": "XRdInterfaceHighErrorRate",
  "alerts": [
    {
      "status": "firing",
      "labels": {
        "alertname": "XRdInterfaceHighErrorRate",
        "severity": "warning",
        "event_type": "interface_errors",
        "target": "xrd-5",
        "name": "GigabitEthernet0/0/0/1",
        "affected_object_type": "interface"
      },
      "annotations": {
        "summary": "High error rate on GigabitEthernet0/0/0/1 on xrd-5",
        "description": "More than 10 errors/sec sustained for 60s on xrd-5 interface GigabitEthernet0/0/0/1"
      },
      "startsAt": "2026-05-23T14:00:00Z",
      "values": { "error_rate": "15.3" }
    }
  ]
}
EOF
}

# ── Dispatch ──────────────────────────────────────────────────────────────────

send_alert() {
    local name="$1"
    local payload="$2"

    local cmd
    cmd=$(printf 'curl -s -o /dev/null -w "%%{http_code}" -X POST %s \\\n  -H "Content-Type: application/json" \\\n  -d '\''%s'\''' \
        "$WEBHOOK_URL" \
        "$(echo "$payload" | tr -d '\n')")

    echo ""
    echo "── $name ──"
    echo "$cmd"

    if [[ "$DRY_RUN" == "false" ]]; then
        status_code=$(curl -s -o /dev/null -w "%{http_code}" \
            -X POST "$WEBHOOK_URL" \
            -H "Content-Type: application/json" \
            -d "$payload")
        echo "→ HTTP $status_code"
    fi
}

run_alert() {
    local type="$1"
    case "$type" in
        interface_down)     send_alert "XRdInterfaceDown"        "$(alert_interface_down)" ;;
        bgp_down)           send_alert "XRdBGPSessionDown"       "$(alert_bgp_down)" ;;
        isis_down)          send_alert "XRdISISAdjacencyDown"    "$(alert_isis_down)" ;;
        topology_degraded)  send_alert "XRdTopologyDegraded"     "$(alert_topology_degraded)" ;;
        interface_flapping) send_alert "XRdInterfaceFlapping"    "$(alert_interface_flapping)" ;;
        interface_errors)   send_alert "XRdInterfaceHighErrorRate" "$(alert_interface_errors)" ;;
        all)
            send_alert "XRdInterfaceDown"          "$(alert_interface_down)"
            send_alert "XRdBGPSessionDown"         "$(alert_bgp_down)"
            send_alert "XRdISISAdjacencyDown"      "$(alert_isis_down)"
            send_alert "XRdTopologyDegraded"       "$(alert_topology_degraded)"
            send_alert "XRdInterfaceFlapping"      "$(alert_interface_flapping)"
            send_alert "XRdInterfaceHighErrorRate" "$(alert_interface_errors)"
            ;;
        *)
            echo "Unknown alert type: $type"
            echo "Available: interface_down | bgp_down | isis_down | topology_degraded | interface_flapping | interface_errors | all"
            exit 1
            ;;
    esac
}

echo "Webhook URL: $WEBHOOK_URL"
if [[ "$DRY_RUN" == "true" ]]; then
    echo "Mode: dry-run (commands printed, not sent)"
fi

if [[ -z "$ALERT_TYPE" ]]; then
    echo ""
    echo "No alert type specified — sending all alert types."
    echo "Usage: bash scripts/test_alert.sh [--dry-run] [alert_type]"
    echo "alert_type: interface_down | bgp_down | isis_down | topology_degraded | interface_flapping | interface_errors | all"
    run_alert "all"
else
    run_alert "$ALERT_TYPE"
fi
