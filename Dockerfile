# Stage 1: Builder
FROM python:3.12-slim as builder

# Install poetry
RUN pip install poetry

# Set working directory
WORKDIR /app

# Copy dependency files
COPY poetry.lock pyproject.toml ./

# Install dependencies
RUN poetry install --no-root --no-dev

# Stage 2: Final Image
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Copy installed dependencies from builder stage
COPY --from=builder /app/.venv /app/.venv

# Add venv to path
ENV PATH="/app/.venv/bin:$PATH"

# Copy the rest of the application code
COPY . .

# Expose the dashboard port
EXPOSE 5000

# The CMD will be set in the docker-compose.yml file
