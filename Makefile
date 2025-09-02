install:
	@uv sync --frozen

rerun:
	uv run langgraph dev --no-browser --debug-port 51111 --server-log-level debug

run:
	uv run langgraph dev --debug-port 51111 --server-log-level debug

upgrade:
	@uv sync --upgrade

logger-names:
	@uv run show-logger-names

help:
	@echo "Available make targets:"
	@echo "  install       - Install dependencies using frozen lockfile (first time only)"
	@echo "  run           - Start the application with debug port"
	@echo "  rerun         - Start the application without browser"
	@echo "  upgrade       - Upgrade dependencies"
	@echo "  logger-names  - Show available logger names for environment configuration"
