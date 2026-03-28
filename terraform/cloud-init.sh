#!/bin/bash
set -euxo pipefail

echo "Starting cloud-init setup..."

# Startup scripts run as root; USER may be empty in this context.
APP_USER=""
if id -u ubuntu >/dev/null 2>&1; then
  APP_USER="ubuntu"
fi

if [ -n "$${APP_USER}" ]; then
  APP_HOME="$(getent passwd "$${APP_USER}" | cut -d: -f6)"
else
  APP_HOME="/root"
fi

# Fix any broken dpkg state from interrupted previous installs
dpkg --configure -a || true
apt-get clean || true
apt-get autoclean || true

# Update system packages
apt-get update
apt-get upgrade -y
apt-get install -y git curl make

# ============================================
# Swap Setup (for low-memory e2-micro)
# ============================================
echo "Setting up swap..."
if [ ! -f /swapfile ]; then
  fallocate -l 2G /swapfile
  chmod 600 /swapfile
  mkswap /swapfile
fi
swapon /swapfile || true
grep -q '^/swapfile ' /etc/fstab || echo '/swapfile none swap sw 0 0' >> /etc/fstab

# ============================================
# Docker Installation
# ============================================
echo "Installing Docker..."
curl -fsSL https://get.docker.com -o /tmp/get-docker.sh
sh /tmp/get-docker.sh

# Add non-root app user to docker group only if that user exists.
if [ -n "$${APP_USER}" ] && id -u "$${APP_USER}" >/dev/null 2>&1; then
  usermod -aG docker "$${APP_USER}"
else
  echo "No non-root app user detected; skipping docker group assignment."
fi

# ============================================
# uv Installation
# ============================================
echo "Installing uv..."
curl -LsSf https://astral.sh/uv/install.sh | sh
source /root/.cargo/env || true

# ============================================
# Clone Repository
# ============================================
echo "Cloning GitHub repository..."
cd "$${APP_HOME}"
if [ ! -d discount-tracker/.git ]; then
  git clone "${github_repo_url}" discount-tracker
else
  echo "Repository already exists at $${APP_HOME}/discount-tracker; pulling latest changes."
  git -C discount-tracker pull --ff-only || true
fi
cd discount-tracker

# ============================================
# Create .env File
# ============================================
echo "Creating .env file..."
cat > .env << 'EOF'
${env_content}
EOF

# ============================================
# Create Logs Directory
# ============================================
echo "Creating logs directory..."
if [ -n "$${APP_USER}" ]; then
  mkdir -p "$${APP_HOME}/logs/cron"
  chown -R "$${APP_USER}:$${APP_USER}" "$${APP_HOME}/logs"
else
  mkdir -p /root/logs/cron
fi

# ============================================
# Start Docker Compose
# ============================================
echo "Starting Docker Compose..."
docker compose up -d

echo "Cloud-init setup completed successfully!"
