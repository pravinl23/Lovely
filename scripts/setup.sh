#!/bin/bash

echo "🚀 WhatsApp Automation System Setup"
echo "=================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if .env exists
if [ ! -f .env ]; then
    echo -e "${YELLOW}Creating .env file from template...${NC}"
    cp .env.example .env
    echo -e "${GREEN}✓ .env file created${NC}"
    echo -e "${YELLOW}Please edit .env file with your credentials before proceeding.${NC}"
    exit 1
fi

# Check required environment variables
source .env
required_vars=(
    "WHATSAPP_PHONE_NUMBER_ID"
    "WHATSAPP_ACCESS_TOKEN"
    "WHATSAPP_WEBHOOK_VERIFY_TOKEN"
    "WHATSAPP_WEBHOOK_SECRET"
    "DATABASE_URL"
    "REDIS_URL"
)

missing_vars=()
for var in "${required_vars[@]}"; do
    if [ -z "${!var}" ]; then
        missing_vars+=($var)
    fi
done

if [ ${#missing_vars[@]} -ne 0 ]; then
    echo -e "${RED}Missing required environment variables:${NC}"
    printf '%s\n' "${missing_vars[@]}"
    exit 1
fi

# Check Docker
if ! command -v docker &> /dev/null; then
    echo -e "${RED}Docker is not installed. Please install Docker first.${NC}"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}Docker Compose is not installed. Please install Docker Compose first.${NC}"
    exit 1
fi

echo -e "${GREEN}✓ All prerequisites met${NC}"

# Start services
echo -e "\n${YELLOW}Starting services...${NC}"
docker-compose up -d db redis

# Wait for database to be ready
echo -e "${YELLOW}Waiting for database to be ready...${NC}"
for i in {1..30}; do
    if docker-compose exec -T db pg_isready -U postgres > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Database is ready${NC}"
        break
    fi
    if [ $i -eq 30 ]; then
        echo -e "${RED}Database failed to start${NC}"
        exit 1
    fi
    sleep 1
done

# Run migrations
echo -e "\n${YELLOW}Running database migrations...${NC}"
docker-compose run --rm app alembic upgrade head
echo -e "${GREEN}✓ Migrations complete${NC}"

# Start all services
echo -e "\n${YELLOW}Starting all services...${NC}"
docker-compose up -d

# Wait for services to be healthy
sleep 5

# Check health
echo -e "\n${YELLOW}Checking service health...${NC}"
if curl -f http://localhost:8000/health > /dev/null 2>&1; then
    echo -e "${GREEN}✓ API is healthy${NC}"
else
    echo -e "${RED}API health check failed${NC}"
fi

echo -e "\n${GREEN}Setup complete!${NC}"
echo -e "\nServices running:"
echo -e "  - API: http://localhost:8000"
echo -e "  - Metrics: http://localhost:9090/metrics"
echo -e "  - PgAdmin: http://localhost:8080"
echo -e "  - Flower (Celery): http://localhost:5555"

echo -e "\n${YELLOW}Next steps:${NC}"
echo -e "1. Configure your webhook URL in WhatsApp Business Platform"
echo -e "2. Your webhook URL: https://yourdomain.com/webhook"
echo -e "3. Verification token: ${WHATSAPP_WEBHOOK_VERIFY_TOKEN}"

echo -e "\n${GREEN}Happy automating! 🤖${NC}" 