run:
	uv run langgraph dev --debug-port 51111 --server-log-level debug 

upgrade:
	uv sync --upgrade