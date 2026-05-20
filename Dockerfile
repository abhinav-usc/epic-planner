# ── Stage 1: build frontend ──────────────────────────────────────────────────
FROM node:20-slim AS frontend-build

WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# ── Stage 2: Python runtime ──────────────────────────────────────────────────
FROM python:3.11-slim

WORKDIR /app

# Install build tools needed by pywebpush / cryptography, then clean up
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libssl-dev \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend source
COPY backend/ ./backend/

# Copy pre-built frontend into a static folder FastAPI will serve
COPY --from=frontend-build /app/frontend/dist ./frontend/dist

# Copy any scripts / data needed at runtime
COPY scripts/ ./scripts/

# Expose the port Fly will route to
EXPOSE 8000

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
