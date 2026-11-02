CONTAINER_ENGINE := $(shell command -v podman >/dev/null 2>&1 && podman compose version >/dev/null 2>&1 && echo podman || echo docker)
# Same detection as xrd-observability-stack, except that a working Podman wins
# over a standalone docker-compose binary (which would need a Docker daemon).
COMPOSE          := $(shell [ "$(CONTAINER_ENGINE)" = podman ] && echo podman compose || (command -v docker-compose >/dev/null 2>&1 && echo docker-compose || echo docker compose))
WEBHOOK_COMPOSE  := $(COMPOSE) -f webhook/compose.yaml

# Read only these keys from .env (it also holds API keys, so it is never
# exported wholesale). Environment or command-line values take precedence.
env_get = $(shell [ -f .env ] && sed -n 's/^$(1)=//p' .env | tail -n 1 | tr -d "\"' ")
WEBHOOK_PORT   ?= $(or $(call env_get,WEBHOOK_PORT),8080)
WEBHOOK_BIND   ?= $(or $(call env_get,WEBHOOK_BIND),127.0.0.1)
LANGGRAPH_HOST ?= $(or $(call env_get,LANGGRAPH_HOST),127.0.0.1)
ALERT          ?= interface_down

.PHONY: install run rerun upgrade logger-names help \
        webhook webhook-stop webhook-logs check-webhook test-alert

install:
	@uv sync --locked

rerun:
	uv run langgraph dev --no-browser --host $(LANGGRAPH_HOST) --debug-port 51111 --server-log-level debug

run:
	uv run langgraph dev --host $(LANGGRAPH_HOST) --debug-port 51111 --server-log-level debug

upgrade:
	@uv sync --upgrade

logger-names:
	@uv run show-logger-names

webhook:
	@WEBHOOK_PORT=$(WEBHOOK_PORT) WEBHOOK_BIND=$(WEBHOOK_BIND) $(WEBHOOK_COMPOSE) up -d --build
	@echo ""
	@echo "Webhook proxy ($(CONTAINER_ENGINE)) listening on $(WEBHOOK_BIND):$(WEBHOOK_PORT)"
	@echo "  Health:        http://localhost:$(WEBHOOK_PORT)/health"
	@echo "  Alert URL:     http://localhost:$(WEBHOOK_PORT)/alert"
	@echo "  Alertmanager:  http://host.docker.internal:$(WEBHOOK_PORT)/alert (default WEBHOOK_RECEIVER_URL)"
	@echo "  Forwards to:   http://host.docker.internal:2024 (LangGraph, start it with 'make run')"
	@echo "Next: 'make check-webhook', then 'make run'."

webhook-stop:
	@$(WEBHOOK_COMPOSE) down

webhook-logs:
	@$(WEBHOOK_COMPOSE) logs -f webhook

check-webhook:
	@fail=0; \
	if curl -fsS --max-time 3 http://localhost:$(WEBHOOK_PORT)/health >/dev/null 2>&1; then \
	  echo "PASS (a) proxy answers on http://localhost:$(WEBHOOK_PORT)/health"; \
	else \
	  echo "FAIL (a) proxy not reachable on http://localhost:$(WEBHOOK_PORT)/health"; \
	  echo "     fix: run 'make webhook'; check WEBHOOK_PORT and '$(CONTAINER_ENGINE) ps'"; \
	  fail=1; \
	fi; \
	if curl -fsS --max-time 3 http://127.0.0.1:2024/ok >/dev/null 2>&1; then \
	  echo "PASS (b) LangGraph answers on http://127.0.0.1:2024/ok"; \
	else \
	  echo "FAIL (b) LangGraph not reachable on http://127.0.0.1:2024/ok"; \
	  echo "     fix: start it with 'make run' (expected to fail until then)"; \
	fi; \
	if $(WEBHOOK_COMPOSE) exec -T webhook python -c "import urllib.request; urllib.request.urlopen('http://host.docker.internal:2024/ok', timeout=3)" >/dev/null 2>&1; then \
	  echo "PASS (c) webhook container reaches http://host.docker.internal:2024/ok"; \
	else \
	  echo "FAIL (c) webhook container cannot reach http://host.docker.internal:2024/ok"; \
	  echo "     fix: start LangGraph ('make run'); on Linux Docker set LANGGRAPH_HOST=0.0.0.0 (exposes the agent API on the network)"; \
	fi; \
	exit $$fail

test-alert:
	WEBHOOK_URL=http://localhost:$(WEBHOOK_PORT)/alert bash scripts/test_alert.sh $(ALERT)

help:
	@echo "Available make targets:"
	@echo "  install        - Install dependencies using locked lockfile (first time only)"
	@echo "  run            - Start LangGraph with debug port (binds LANGGRAPH_HOST, default $(LANGGRAPH_HOST))"
	@echo "  rerun          - Start LangGraph without browser (binds LANGGRAPH_HOST, default $(LANGGRAPH_HOST))"
	@echo "  upgrade        - Upgrade dependencies"
	@echo "  logger-names   - Show available logger names for environment configuration"
	@echo "  webhook        - Build and start the webhook proxy container (detached)"
	@echo "  webhook-stop   - Stop the webhook proxy container"
	@echo "  webhook-logs   - Follow the webhook proxy logs"
	@echo "  check-webhook  - Check proxy, LangGraph and the container-to-host hop (PASS/FAIL)"
	@echo "  test-alert     - Send a sample alert to the proxy (ALERT=interface_down|bgp_down|...|all)"
	@echo ""
	@echo "Settings (environment, command line or .env):"
	@echo "  WEBHOOK_PORT   - Host port of the webhook proxy (default 8080, now $(WEBHOOK_PORT))"
	@echo "  WEBHOOK_BIND   - Host bind address of the proxy (default 127.0.0.1, now $(WEBHOOK_BIND))"
	@echo "  LANGGRAPH_HOST - Bind address of LangGraph (default 127.0.0.1, now $(LANGGRAPH_HOST))"
	@echo "Container engine detected: $(CONTAINER_ENGINE)"
