rerun:
	uv run langgraph dev --no-browser --debug-port 51111 --server-log-level debug

run:
	uv run langgraph dev --debug-port 51111 --server-log-level debug

upgrade:
	uv sync --upgrade