# Stage 1: Build the Next.js Frontend
FROM node:20-slim AS frontend-builder
WORKDIR /app/frontend

COPY frontend/package.json ./
RUN npm install --no-audit --no-fund

COPY frontend/ ./
RUN npm run build

# Stage 2: Final Runtime Image with Python + Node.js
FROM python:3.11-slim
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY backend/requirements.txt ./backend/
RUN pip install --no-cache-dir -r ./backend/requirements.txt

# Copy Backend application
COPY backend ./backend

# Copy built Next.js standalone and static assets
COPY --from=frontend-builder /app/frontend/.next/standalone ./frontend
COPY --from=frontend-builder /app/frontend/.next/static ./frontend/.next/static
COPY --from=frontend-builder /app/frontend/public ./frontend/public

# Copy entrypoint runner
COPY entrypoint.sh ./
RUN chmod +x ./entrypoint.sh

ENV PROJECT_ID="mb-poc-352009"
ENV LOCATION="us-central1"
ENV PORT=8080
ENV ENABLE_SMS_DISPATCH="true"
ENV NODE_ENV=production

EXPOSE 8080

CMD ["./entrypoint.sh"]

