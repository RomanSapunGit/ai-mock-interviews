FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

# Set the working directory
WORKDIR /app

# Enable bytecode compilation
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy

# Copy only the dependency files first
COPY pyproject.toml uv.lock ./

# Install dependencies (cache mount keeps downloaded packages between builds)
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --no-dev

# Copy the rest of the application code (respecting .dockerignore)
COPY . .

# Copy entrypoint outside /app so volume mounts can't overwrite it
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Set environment variables for the application
ENV PYTHONUNBUFFERED=1

# Expose the application port
EXPOSE 8000

ENTRYPOINT ["/entrypoint.sh"]
