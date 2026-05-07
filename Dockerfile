# Build frontend
FROM node:22-alpine as frontend-builder
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm install
COPY frontend .
RUN npm run build

# Build backend
FROM python:3.13-slim
WORKDIR /app

# Install system dependencies for Playwright
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    && rm -rf /var/lib/apt/lists/*

# Install dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Install playwright browsers
RUN playwright install --with-deps chromium

COPY src /app/src
COPY --from=frontend-builder /app/frontend/dist /app/frontend/dist

# Expose port
EXPOSE 8000

# Provide environment variables fallback
ENV DATABASE_URL="sqlite+aiosqlite:///flyingpig.db"
ENV ANTHROPIC_API_KEY=""

# Run FastAPI, serving frontend static files if we want to
CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
