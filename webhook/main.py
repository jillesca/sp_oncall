# Copyright 2026 Cisco Systems, Inc. and its affiliates
#
# SPDX-License-Identifier: Apache-2.0
#
# Copied from CiscoDevNet/xrd-observability-stack @ 1fc9dce171f55a10e806fceeafa4308ecfa5dcbc (webhook/).
# Changes from the original:
# - Log a summary of every received payload (receiver, status, alert count,
#   per-alert name/source/status) at INFO.
# - Return 400 for malformed JSON or payloads that fail validation, so
#   Alertmanager does not retry them.
# - Return 202 explicitly: returning JSONResponse bypassed the decorator's
#   status_code, so the endpoint sent 200 despite its docstring.
# - Warn when a grouped payload has several alerts: only the first one is investigated.

"""
FastAPI webhook receiver for Grafana → sp_oncall alert forwarding.

Endpoint: POST /alert
  - Validates the Grafana webhook payload
  - Transforms it into a NetworkAlert (canonical schema)
  - Fires a background LangGraph run in sp_oncall
  - Returns {"status": "accepted"} immediately (fire-and-forget)

Endpoint: GET /health
  - Returns {"status": "ok"} for compose healthchecks and readiness probes

TODO (future): Handle "resolved" status alerts as a confirmation signal to
sp_oncall that the network has recovered, allowing agents to append a
resolution note to the active investigation thread rather than ignoring it.
"""

from __future__ import annotations

import logging
import os

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from langgraph_client import trigger_investigation
from schema import GrafanaWebhook, parse_grafana_webhook

logging.basicConfig(
    level=os.getenv(key="LOG_LEVEL", default="INFO"),
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="XRd Webhook Receiver",
    description="Translates Grafana alert webhooks into sp_oncall investigations.",
    version="0.1.0",
)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@app.post("/alert", status_code=status.HTTP_202_ACCEPTED)
async def receive_alert(request: Request) -> JSONResponse:
    """Accept a Grafana webhook and trigger an sp_oncall investigation.

    Returns 202 for every well-formed payload so the sender does not retry on
    transient errors. Errors in LangGraph communication are logged but never
    surfaced to the sender. Malformed payloads get 400.
    """
    try:
        body_raw = await request.json()
        webhook = GrafanaWebhook.model_validate(body_raw)
    except (ValueError, ValidationError) as exc:
        # Non-2xx makes Alertmanager retry; a malformed body will never succeed.
        logger.error("Rejected malformed webhook payload: %s", exc)
        return JSONResponse(
            {"status": "rejected", "detail": "invalid payload"},
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    logger.info(
        "Received webhook: receiver=%r status=%s alerts=%d",
        webhook.receiver,
        webhook.status or "unknown",
        len(webhook.alerts),
    )
    for item in webhook.alerts:
        logger.info(
            "  alert=%r source=%r status=%s",
            item.labels.alertname,
            item.labels.source or item.labels.target,
            item.status or "unknown",
        )
    if len(webhook.alerts) > 1:
        logger.warning(
            "Webhook carries %d alerts; only the first one is investigated",
            len(webhook.alerts),
        )
    logger.debug("Webhook body: %s", body_raw)

    if webhook.status == "resolved":
        # TODO (future): send a recovery confirmation to the active sp_oncall
        # thread so agents can append a resolution note without re-running
        # the full investigation.
        logger.info("Alert resolved — no action taken (see TODO in main.py)")
        return JSONResponse(
            {"status": "accepted", "action": "ignored_resolved"},
            status_code=status.HTTP_202_ACCEPTED,
        )

    alert = parse_grafana_webhook(body=webhook)
    if alert is None:
        logger.warning("Webhook dropped: not firing or no alerts present")
        return JSONResponse(
            {"status": "accepted", "action": "ignored"},
            status_code=status.HTTP_202_ACCEPTED,
        )

    logger.info(
        "Parsed alert: name=%r device=%r object=%r",
        alert.alert_name,
        alert.device,
        alert.affected_object,
    )

    await trigger_investigation(alert)

    return JSONResponse(
        {"status": "accepted"}, status_code=status.HTTP_202_ACCEPTED
    )
