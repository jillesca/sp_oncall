# Webhook proxy

> Copied from CiscoDevNet/xrd-observability-stack @ 1fc9dce171f55a10e806fceeafa4308ecfa5dcbc (`webhook/`).
> Changes from the original:
>
> - `main.py`: payload summary logging, 400 for malformed payloads, explicit 202, warning for multi-alert payloads.
> - `langgraph_client.py`: logs the target URL and HTTP status of each forward, actionable hint on connection failure.
> - Added `compose.yaml` and this README. `webhook_test_receiver.py` was not copied (the observability stack now ships an `alert-echo` container instead).

A small FastAPI container that receives Alertmanager (or Grafana) webhooks and starts an
sp_oncall investigation by calling `POST /runs` on the LangGraph server running on the host.
It is a standalone utility: it only needs to be reachable by the sender and to reach LangGraph.

| Endpoint      | Purpose                                                                          |
| ------------- | -------------------------------------------------------------------------------- |
| `POST /alert` | Accepts the webhook, answers `202` immediately, forwards to LangGraph in-process |
| `GET /health` | Liveness (used by the compose healthcheck and `make check-webhook`)              |

Malformed payloads get `400`. Failures talking to LangGraph are logged but never returned
to the sender, so Alertmanager does not retry.

## Run it

From the sp_oncall repository root:

```bash
make webhook         # build + start, detached
make check-webhook   # PASS/FAIL per hop with a fix hint
make test-alert      # send a sample alert (ALERT=bgp_down, all, ...)
make webhook-logs    # see what arrived and what was forwarded
make webhook-stop
```

Start order: observability stack, then `make webhook`, then `make run` (LangGraph). The proxy
accepts alerts before LangGraph is up; only the forward call fails, and it logs why.

## Configuration

| Variable                 | Default                            | Where                          | Notes                                                                 |
| ------------------------ | ---------------------------------- | ------------------------------ | --------------------------------------------------------------------- |
| `WEBHOOK_PORT`           | `8080`                             | shell env, `.env` (via `make`) | Host port published by the container                                  |
| `WEBHOOK_BIND`           | `127.0.0.1`                        | shell env, `.env` (via `make`) | Host bind address. Linux Docker needs `0.0.0.0` (see the main README) |
| `LANGGRAPH_API_URL`      | `http://host.docker.internal:2024` | shell env                      | Where the container reaches LangGraph                                 |
| `LANGGRAPH_ASSISTANT_ID` | `agent`                            | shell env                      | Graph key from `langgraph.json`                                       |
| `LOG_LEVEL`              | `INFO`                             | shell env                      | `DEBUG` also logs the full payload                                    |

The compose file does not read sp_oncall's `.env`, because that file holds API keys that
must not reach this container.

## Without `make`

```bash
docker compose -f webhook/compose.yaml up -d --build
```
