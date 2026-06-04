# ── Stage 1: Build React frontend ─────────────────────────────────────────────
FROM node:18-slim AS frontend-builder
WORKDIR /build
COPY frontend/ .
RUN npm install && npm run build

# ── Stage 2: Final image (Python + Node + both services) ──────────────────────
FROM python:3.11-slim

# Install Node.js 18
RUN apt-get update && apt-get install -y curl ca-certificates && \
    curl -fsSL https://deb.nodesource.com/setup_18.x | bash - && \
    apt-get install -y nodejs && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Python dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend source
COPY backend/ ./backend/
RUN mkdir -p ./backend/data

# Copy frontend server + built assets from stage 1
COPY serve.mjs .
COPY --from=frontend-builder /build/dist ./frontend/dist/

EXPOSE 3000 3001

# Start both: Python backend in background, Node frontend in foreground
CMD sh -c "cd /app/backend && python server.py & cd /app && node serve.mjs"
