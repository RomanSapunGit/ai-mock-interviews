FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

# Set the working directory
WORKDIR /app

# Enable bytecode compilation
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy

# Copy only the dependency files first
COPY pyproject.toml uv.lock ./

# Install dependencies (this creates the .venv in /app)
RUN uv sync --no-dev

# Copy the rest of the application code (respecting .dockerignore)
COPY . .

# Expose the application port
EXPOSE 8000

# Set environment variables for the application
ENV PYTHONUNBUFFERED=1

# Use uv run to ensure we use the virtual environment correctly
CMD ["uv", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
