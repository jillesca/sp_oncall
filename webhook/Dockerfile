# ── Stage 1: dependency installer ────────────────────────────────────────────
FROM python:3.12-slim AS builder

# Bring in the uv binary from the official image — no uv installation needed
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

WORKDIR /app

# Tell uv to:
#   - compile .pyc files (faster container startup)
#   - copy files instead of hard-linking (required inside Docker overlay FS)
#   - never download Python (use the system Python from the base image)
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never

# Install only dependencies (not the project itself) using the locked lockfile.
# pyproject.toml + uv.lock are copied before app source so this layer is only
# invalidated when deps change, not on every source edit — maximising cache reuse.
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-install-project --no-dev

# Stage 1 ends here — no application source copied, so this entire stage is
# cached as long as pyproject.toml and uv.lock are unchanged.


# ── Stage 2: minimal runtime image ───────────────────────────────────────────
FROM python:3.12-slim

WORKDIR /app

# Copy the populated virtualenv from the builder stage
COPY --from=builder /app/.venv /app/.venv

# Copy application source directly from the build context — NOT from builder.
# Changing app code invalidates only this layer; stage 1 (deps) stays cached.
COPY main.py schema.py langgraph_client.py ./

ENV PATH="/app/.venv/bin:$PATH"

EXPOSE 8080

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]

