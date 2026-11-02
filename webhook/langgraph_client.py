# Copyright 2026 Cisco Systems, Inc. and its affiliates
#
# SPDX-License-Identifier: Apache-2.0
#
# Copied from CiscoDevNet/xrd-observability-stack @ 1fc9dce171f55a10e806fceeafa4308ecfa5dcbc (webhook/).
# Changes from the original:
# - Log the target URL and the HTTP status of every forward attempt.
# - Print an actionable hint (make check-webhook, LANGGRAPH_HOST, host.docker.internal) when LangGraph is unreachable.
# - Docstring says the endpoint answers 202 to the sender (it said Grafana/200).

"""
HTTP client for triggering sp_oncall investigations via the LangGraph API server.

Calls POST /runs on the LangGraph server, which creates a new stateless run
of the `agent` graph. The run is fire-and-forget: we return immediately after
the server accepts the request. Investigators can follow progress in
LangGraph Studio.

API reference: https://langchain-ai.github.io/langgraph/cloud/reference/sdk/python_sdk_ref/
"""

from __future__ import annotations

import logging
import os

import httpx

from schema import NetworkAlert

logger = logging.getLogger(__name__)

# Graph key from sp_oncall/langgraph.json: {"graphs": {"agent": "..."}}
_DEFAULT_ASSISTANT_ID = "agent"


def _langgraph_url() -> str:
    base = os.getenv(
        key="LANGGRAPH_API_URL", default="http://host.docker.internal:2024"
    )
    return base.rstrip("/") + "/runs"


def _assistant_id() -> str:
    return os.getenv(
        key="LANGGRAPH_ASSISTANT_ID", default=_DEFAULT_ASSISTANT_ID
    )


def _build_run_payload(alert: NetworkAlert) -> dict:
    """Construct the POST /runs body for the LangGraph API.

    The `agent` graph (sp_oncall) reads its initial task from the most recent
    HumanMessage in `messages`. We pass the human-readable alert summary so
    the input_validator_node and planner_node can derive device investigations
    without needing to parse raw JSON.

    on_completion=keep means the thread stays visible in LangGraph Studio
    after the run ends — useful during demos.
    """
    return {
        "assistant_id": _assistant_id(),
        "input": {
            "messages": [
                {
                    "type": "human",
                    "content": alert.to_human_message(),
                }
            ]
        },
        "on_completion": "keep",
        "after_seconds": 1,
    }


async def trigger_investigation(alert: NetworkAlert) -> None:
    """Fire a background investigation run in sp_oncall.

    Does NOT wait for the investigation to complete — returns as soon as the
    LangGraph server acknowledges the run. Any HTTP or connection error is
    logged but not re-raised, so the webhook endpoint always answers 202 to
    the sender.
    """
    url = _langgraph_url()
    payload = _build_run_payload(alert)

    logger.info(
        "Triggering sp_oncall investigation: alert=%s device=%s url=%s",
        alert.alert_name,
        alert.device,
        url,
    )
    logger.debug("LangGraph run payload: %s", payload)

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                url,
                json=payload,
                headers={
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                },
            )
            logger.info(
                "LangGraph responded: url=%s status=%s", url, response.status_code
            )
            response.raise_for_status()
            run_info = response.json()
            logger.info(
                "sp_oncall run accepted: run_id=%s thread_id=%s",
                run_info.get("run_id"),
                run_info.get("thread_id"),
            )
    except httpx.HTTPStatusError as exc:
        logger.error(
            "LangGraph API at %s returned HTTP %s: %s",
            url,
            exc.response.status_code,
            exc.response.text,
        )
    except httpx.RequestError as exc:
        logger.error(
            "Cannot reach LangGraph API at %s (no HTTP status): %r. "
            "Hints: run `make check-webhook` on the host; start LangGraph "
            "with `make run`; on Linux Docker set LANGGRAPH_HOST=0.0.0.0 "
            "because host.docker.internal is not loopback; check that "
            "host.docker.internal resolves inside the container "
            "(extra_hosts host-gateway).",
            url,
            exc,
        )
    except Exception as exc:  # noqa: BLE001
        logger.error(
            "Unexpected error triggering investigation at %s: %s", url, exc
        )
