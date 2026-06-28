#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

COMPOSE_FILE="docker-compose.prod.yml"
ENV_FILE=".env"

red() { printf '\033[0;31m%s\033[0m\n' "$*"; }
green() { printf '\033[0;32m%s\033[0m\n' "$*"; }

require_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    red "Missing required command: $1"
    exit 1
  fi
}

require_env() {
  local key="$1"
  if ! grep -q "^${key}=" "$ENV_FILE" 2>/dev/null; then
    red "Missing ${key} in ${ENV_FILE}"
    exit 1
  fi
  local value
  value="$(grep "^${key}=" "$ENV_FILE" | cut -d= -f2-)"
  if [[ -z "$value" || "$value" == *"yourdomain"* || "$value" == *"replace-with"* || "$value" == *"tvly-your-key"* ]]; then
    red "Please set a real value for ${key} in ${ENV_FILE}"
    exit 1
  fi
}

green "ContentOrchester production deploy"
echo

require_cmd docker
if ! docker compose version >/dev/null 2>&1; then
  red "Docker Compose v2 is required (docker compose)."
  exit 1
fi

if [[ ! -f "$ENV_FILE" ]]; then
  if [[ -f deploy/.env.production.example ]]; then
    cp deploy/.env.production.example "$ENV_FILE"
    green "Created ${ENV_FILE} from template. Edit it, then run this script again."
    exit 0
  fi
  red "No ${ENV_FILE} found."
  exit 1
fi

for key in DOMAIN ACME_EMAIL PUBLIC_API_URL TAVILY_API_KEY JWT_SECRET POSTGRES_PASSWORD; do
  require_env "$key"
done

green "Building and starting services (first run may take 5–10 min while Ollama pulls the model)..."
docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" up -d --build

echo
green "Waiting for API health check..."
for i in {1..30}; do
  if docker compose -f "$COMPOSE_FILE" exec -T api python -c \
    "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/v1/health')" \
    >/dev/null 2>&1; then
    break
  fi
  sleep 5
done

echo
green "Deploy complete."
echo "  App:    https://${DOMAIN:-your-domain}"
echo "  API:    https://${DOMAIN:-your-domain}/api/v1/health"
echo "  Docs:   https://${DOMAIN:-your-domain}/docs"
echo
echo "Useful commands:"
echo "  docker compose -f $COMPOSE_FILE logs -f worker"
echo "  docker compose -f $COMPOSE_FILE logs -f ollama"
echo "  docker compose -f $COMPOSE_FILE ps"
