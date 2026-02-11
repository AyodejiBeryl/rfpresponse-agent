#!/bin/bash
# Initial server setup script for deployment
# Run this once on a fresh Ubuntu server

set -e

echo "=== RFP Response Platform - Server Setup ==="

# Install Docker
if ! command -v docker &> /dev/null; then
    curl -fsSL https://get.docker.com | sh
    sudo usermod -aG docker $USER
    echo "Docker installed. Log out and back in for group changes."
fi

# Install Docker Compose plugin
if ! docker compose version &> /dev/null; then
    sudo apt-get update
    sudo apt-get install -y docker-compose-plugin
fi

# Create app directory
sudo mkdir -p /opt/rfp-platform
sudo chown $USER:$USER /opt/rfp-platform

# Clone repo (replace with your repo URL)
cd /opt/rfp-platform
echo "Clone your repository here:"
echo "  git clone <your-repo-url> ."

echo ""
echo "Then:"
echo "  1. Copy .env.example to .env and fill in values"
echo "  2. Run: docker compose -f docker-compose.prod.yml up -d"
echo "  3. Run: docker compose -f docker-compose.prod.yml exec backend alembic upgrade head"
echo ""
echo "=== Setup complete ==="
