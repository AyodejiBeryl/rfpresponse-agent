#!/bin/bash
set -e

# Update system
yum update -y

# Install Docker
yum install -y docker git
systemctl enable docker
systemctl start docker

# Install Docker Compose v2
mkdir -p /usr/local/lib/docker/cli-plugins
curl -SL "https://github.com/docker/compose/releases/latest/download/docker-compose-linux-x86_64" \
  -o /usr/local/lib/docker/cli-plugins/docker-compose
chmod +x /usr/local/lib/docker/cli-plugins/docker-compose

# Add ec2-user to docker group
usermod -aG docker ec2-user

# Create swap (1GB) — t2.micro only has 1GB RAM
dd if=/dev/zero of=/swapfile bs=128M count=8
chmod 600 /swapfile
mkswap /swapfile
swapon /swapfile
echo '/swapfile swap swap defaults 0 0' >> /etc/fstab

# Signal ready
touch /home/ec2-user/.docker-ready
