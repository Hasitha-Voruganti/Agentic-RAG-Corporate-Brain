#!/usr/bin/env bash
# scripts/setup.sh — Full project setup

set -e
echo "🧠 Corporate Brain — Setup Script"
echo "=================================="

# 1. Create .env if missing
if [ ! -f .env ]; then
  echo "Creating .env file..."
  cat > .env <<EOF
OPENAI_API_KEY=sk-your-openai-key-here
JWT_SECRET=$(python3 -c "import secrets; print(secrets.token_hex(32))")
POSTGRES_USER=brain
POSTGRES_PASSWORD=brain_secret
POSTGRES_DB=corporate_brain
EOF
  echo "✅ .env created. Please set OPENAI_API_KEY!"
fi

# 2. Start Docker services
echo ""
echo "Starting infrastructure (Qdrant, Elasticsearch, Postgres, Redis)..."
docker compose -f docker/docker-compose.yml up -d qdrant elasticsearch postgres redis
echo "Waiting 15s for services to be ready..."
sleep 15

# 3. Check Elasticsearch
echo "Checking Elasticsearch..."
curl -s http://localhost:9200/_cluster/health | python3 -c "import sys,json; h=json.load(sys.stdin); print(f'  ES status: {h[\"status\"]}')"

# 4. Check Qdrant
echo "Checking Qdrant..."
curl -s http://localhost:6333/healthz && echo "  Qdrant: OK"

# 5. Build and start backend
echo ""
echo "Building backend..."
docker compose -f docker/docker-compose.yml build backend
docker compose -f docker/docker-compose.yml up -d backend

# 6. Build and start frontend
echo "Building frontend..."
docker compose -f docker/docker-compose.yml build frontend
docker compose -f docker/docker-compose.yml up -d frontend

echo ""
echo "=================================="
echo "✅ Corporate Brain is running!"
echo ""
echo "  Frontend:      http://localhost:3000"
echo "  Backend API:   http://localhost:8000"
echo "  API Docs:      http://localhost:8000/docs"
echo "  Qdrant UI:     http://localhost:6333/dashboard"
echo ""
echo "Run scripts/seed_users.py to create test users."