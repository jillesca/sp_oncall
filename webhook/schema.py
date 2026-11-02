# Copyright 2026 Cisco Systems, Inc. and its affiliates
#
# SPDX-License-Identifier: Apache-2.0
#
# Copied from CiscoDevNet/xrd-observability-stack @ 1fc9dce171f55a10e806fceeafa4308ecfa5dcbc (webhook/).
# Changes from the original: none.

"""
Pydantic models for incoming Grafana webhook payloads and the canonical
NetworkAlert schema passed to sp_oncall.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field

# ── Grafana webhook models ────────────────────────────────────────────────────


class GrafanaAlertLabels(BaseModel):
    """Labels attached to a single Grafana alert instance."""

    model_config = {"extra": "allow"}

    alertname: str = ""
    severity: str = ""
    event_type: str = ""
    affected_object_type: str = ""
    # Prometheus target label (device name, e.g. "xrd-1") — Grafana sends "target"
    target: str = ""
    # Alertmanager sends the device label as "source"
    source: str = ""
    # Interface name or BGP neighbor address
    name: str = ""
    neighbor_address: str = ""
    network_instance: str = ""
    protocol: str = ""


class GrafanaAlertAnnotations(BaseModel):
    model_config = {"extra": "allow"}

    summary: str = ""
    description: str = ""


class GrafanaAlert(BaseModel):
    """A single alert entry inside a Grafana webhook POST body."""

    model_config = {"extra": "allow"}

    status: str = ""
    labels: GrafanaAlertLabels = Field(default_factory=GrafanaAlertLabels)
    annotations: GrafanaAlertAnnotations = Field(
        default_factory=GrafanaAlertAnnotations
    )
    startsAt: str = ""
    endsAt: str = ""
    values: dict[str, Any] = Field(default_factory=dict)
    fingerprint: str = ""


class GrafanaWebhook(BaseModel):
    """Root payload sent by Grafana when an alert fires or resolves."""

    model_config = {"extra": "allow"}

    receiver: str = ""
    status: str = ""  # "firing" | "resolved"
    alerts: list[GrafanaAlert] = Field(default_factory=list)
    title: str = ""
    message: str = ""


# ── Canonical NetworkAlert schema ─────────────────────────────────────────────


class NetworkAlert(BaseModel):
    """Canonical alert schema forwarded to sp_oncall.

    Derived from a Grafana webhook payload. Fields that cannot be derived
    from the payload are left as None — sp_oncall agents fill them in via
    gNMIBuddy MCP tools.
    """

    alert_name: str
    severity: str
    timestamp: str  # RFC3339
    duration_seconds: int
    device: str
    event_type: str
    affected_object: str | None
    affected_object_type: str | None
    previous_state: str = "up"
    current_state: str = "down"
    protocol: str | None
    network_instance: str | None
    neighbor_device: str | None
    metric_value: float | None
    threshold: int = 1

    def to_human_message(self) -> str:
        """Build the human-readable string passed as the HumanMessage to sp_oncall.

        Structured enough for LLM agents to parse unambiguously, readable
        enough to be legible in LangGraph Studio traces.
        """
        lines = [
            f"NETWORK ALERT: {self.alert_name} [{self.severity.upper()}]",
            "",
            f"Device: {self.device}",
            f"Event Type: {self.event_type}",
        ]

        if self.affected_object:
            lines.append(
                f"Affected Object: {self.affected_object}"
                + (
                    f" ({self.affected_object_type})"
                    if self.affected_object_type
                    else ""
                )
            )

        lines += [
            f"State Change: {self.previous_state} → {self.current_state}",
            f"Severity: {self.severity}",
            f"Alert Started: {self.timestamp}",
            f"Firing Duration: {self.duration_seconds}s",
        ]

        if self.network_instance:
            lines.append(f"Network Instance: {self.network_instance}")
        if self.protocol:
            lines.append(f"Protocol: {self.protocol}")
        if self.neighbor_device:
            lines.append(f"Neighbor Device: {self.neighbor_device}")

        return "\n".join(lines)


def parse_grafana_webhook(body: GrafanaWebhook) -> NetworkAlert | None:
    """Transform a Grafana webhook payload into a NetworkAlert.

    Returns None if the webhook is not firing or contains no alerts.
    """
    if body.status != "firing" or not body.alerts:
        return None

    alert = body.alerts[0]
    labels = alert.labels

    starts_at: datetime | None = None
    try:
        starts_at = datetime.fromisoformat(
            alert.startsAt.replace("Z", "+00:00")
        )
    except (ValueError, AttributeError):
        pass

    now = datetime.now(tz=timezone.utc)
    duration = int((now - starts_at).total_seconds()) if starts_at else 0
    timestamp = starts_at.isoformat() if starts_at else now.isoformat()

    # Prefer interface name; fall back to neighbor address for BGP alerts
    affected_object = labels.name or labels.neighbor_address or None

    metric_value: float | None = None
    if alert.values:
        raw = next(iter(alert.values.values()), None)
        try:
            metric_value = float(raw) if raw is not None else None
        except (TypeError, ValueError):
            pass

    return NetworkAlert(
        alert_name=labels.alertname or body.title,
        severity=labels.severity or "unknown",
        timestamp=timestamp,
        duration_seconds=max(duration, 0),
        device=labels.target or labels.source or "unknown",
        event_type=labels.event_type,
        affected_object=affected_object,
        affected_object_type=labels.affected_object_type or None,
        protocol=labels.protocol or None,
        network_instance=labels.network_instance or None,
        neighbor_device=None,  # filled by sp_oncall agents via gNMIBuddy
        metric_value=metric_value,
    )
