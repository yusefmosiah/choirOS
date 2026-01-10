# ChoirOS Development Container
# Unified sandbox with Supervisor, Vite, and FastAPI

FROM node:20-slim AS base

# Install Python and system dependencies
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Create Python virtual environment
RUN python3 -m venv /app/venv
ENV PATH="/app/venv/bin:$PATH"
ENV PYTHONPATH="/app"

# Copy and install Python dependencies
COPY api/requirements.txt /app/api/requirements.txt
COPY supervisor/requirements.txt /app/supervisor/requirements.txt
RUN pip install --no-cache-dir -r /app/api/requirements.txt \
    && pip install --no-cache-dir -r /app/supervisor/requirements.txt

# Copy and install Node dependencies
COPY choiros/package.json choiros/yarn.lock* /app/choiros/
RUN cd /app/choiros && yarn install --frozen-lockfile || yarn install

# Copy source code
COPY api/ /app/api/
COPY choiros/ /app/choiros/
COPY supervisor/ /app/supervisor/

# Expose ports
# 5173 - Vite dev server
# 8000 - FastAPI backend
# 8001 - Supervisor
EXPOSE 5173 8000 8001

# Start supervisor (which manages Vite and API)
CMD ["python", "-m", "supervisor.main"]
