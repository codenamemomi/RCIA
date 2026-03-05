#!/usr/bin/env bash
# ==============================================================================
#  RCIA - Server Setup Script
#  Automates the full project bootstrap after cloning.
#  Usage: bash setup.sh
# ==============================================================================

set -e  # Exit immediately on any error

# --- Colors ---
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m' # No Color

step() { echo -e "\n${CYAN}${BOLD}[SETUP] $1${NC}"; }
ok()   { echo -e "${GREEN}✔ $1${NC}"; }
warn() { echo -e "${YELLOW}⚠ $1${NC}"; }
die()  { echo -e "${RED}✘ $1${NC}"; exit 1; }

echo -e "${BOLD}"
echo "  ╔═══════════════════════════════════════════╗"
echo "  ║     RCIA - Full Server Bootstrap           ║"
echo "  ╚═══════════════════════════════════════════╝"
echo -e "${NC}"

# Guard against port conflicts
DEFAULT_PORT=8001
read -p "  Enter port to run RCIA on (default: ${DEFAULT_PORT}): " INPUT_PORT
RCIA_PORT=${INPUT_PORT:-$DEFAULT_PORT}

# Check if port is already in use
if ss -tlnp | grep -q ":${RCIA_PORT} "; then
    die "Port ${RCIA_PORT} is already in use by another service. Choose a different port."
fi
ok "RCIA will run on port ${RCIA_PORT}. No conflict detected."

# ==============================================================================
# STEP 1 - Check prerequisites
# ==============================================================================
step "Checking prerequisites..."

command -v python3 >/dev/null 2>&1 || die "Python 3 is required. Install it with: sudo apt install python3 python3-venv python3-pip"
command -v pip3 >/dev/null 2>&1 || die "pip3 is required."
command -v psql >/dev/null 2>&1 || warn "PostgreSQL CLI not found. Make sure the DB is accessible at your configured DATABASE_URL."
ok "Prerequisites passed."

# ==============================================================================
# STEP 2 - Create virtual environment
# ==============================================================================
step "Setting up Python virtual environment..."

if [ ! -d "venv" ]; then
    python3 -m venv venv
    ok "Virtual environment created at ./venv"
else
    warn "Virtual environment already exists. Skipping creation."
fi

source venv/bin/activate
ok "Activated venv."

# ==============================================================================
# STEP 3 - Install Python dependencies
# ==============================================================================
step "Installing Python dependencies from requirements.txt..."
pip install --upgrade pip -q
pip install -r requirements.txt -q
ok "All Python dependencies installed."

# ==============================================================================
# STEP 4 - Configure environment
# ==============================================================================
step "Configuring environment..."

if [ ! -f ".env" ]; then
    cp .env.example .env
    warn ".env file created from .env.example."
    echo ""
    echo -e "${YELLOW}${BOLD}  ACTION REQUIRED:${NC}"
    echo "  Please open .env and fill in the following values before starting:"
    echo "    - SECRET_KEY       (generate with: python3 -c \"import secrets; print(secrets.token_hex(32))\")"
    echo "    - DATABASE_URL     (default: postgresql+asyncpg://user:password@localhost/rcia_db)"
    echo "    - DATABASE_SYNC_URL"
    echo "    - AGENT_PRIVATE_KEY (your ERC-8004 wallet private key)"
    echo "    - WEB3_RPC_URL     (Infura, Alchemy, or local node)"
    echo ""
    read -p "  Press ENTER after you have configured .env to continue..." _
else
    ok ".env file already exists. Proceeding with existing configuration."
fi

# ==============================================================================
# STEP 5 - Run database migrations
# ==============================================================================
step "Running database migrations with Alembic..."

# Sync the alembic.ini DATABASE_URL from .env
DB_SYNC_URL=$(grep -E "^DATABASE_SYNC_URL=" .env | cut -d '=' -f2-)
if [ -n "$DB_SYNC_URL" ]; then
    sed -i "s|sqlalchemy.url = .*|sqlalchemy.url = ${DB_SYNC_URL}|g" alembic.ini
    ok "alembic.ini updated with DATABASE_SYNC_URL."
fi

python3 -m alembic upgrade head && ok "Database migrations applied." || warn "Migrations failed or no migrations found. Check your DATABASE_URL in .env."

# ==============================================================================
# STEP 6 - Verify the installation
# ==============================================================================
step "Verifying installation with a quick import check..."
python3 -c "
from core.config import settings
from api.v1.services.trust import TrustService
print('  ✔ Core modules imported successfully.')
print(f'  ✔ Agent: {settings.AGENT_NAME} | Mode: Simulation={settings.SIMULATE_ON_CHAIN}')
" || die "Import check failed. Check your .env and dependencies."

# ==============================================================================
# STEP 7 - Install systemd service (optional)
# ==============================================================================
step "Installing systemd service for auto-start..."

SERVICE_FILE="/etc/systemd/system/rcia.service"
WORKING_DIR=$(pwd)
VENV_PYTHON="${WORKING_DIR}/venv/bin/python3"
RUN_USER=$(whoami)

if command -v systemctl >/dev/null 2>&1; then
    sudo tee "$SERVICE_FILE" > /dev/null <<EOF
[Unit]
Description=RCIA - Autonomous Capital Intelligence API
After=network.target postgresql.service

[Service]
Type=simple
User=${RUN_USER}
WorkingDirectory=${WORKING_DIR}
ExecStart=${VENV_PYTHON} -m uvicorn main:app --host 0.0.0.0 --port ${RCIA_PORT} --root-path /rcia --workers 2
Restart=on-failure
RestartSec=5s
EnvironmentFile=${WORKING_DIR}/.env
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

    sudo systemctl daemon-reload
    sudo systemctl enable rcia.service
    ok "systemd service installed and enabled: rcia.service"
    echo ""
    echo -e "  Start now:    ${BOLD}sudo systemctl start rcia${NC}"
    echo -e "  View logs:    ${BOLD}sudo journalctl -u rcia -f${NC}"
    echo -e "  Check status: ${BOLD}sudo systemctl status rcia${NC}"
else
    warn "systemd not found. Skipping service installation."
    echo ""
    echo -e "  To start manually:"
    echo -e "    ${BOLD}source venv/bin/activate && uvicorn main:app --host 0.0.0.0 --port ${RCIA_PORT} --root-path /rcia${NC}"
fi

# ==============================================================================
# STEP 8 - Nginx: Add /rcia location block (non-destructive)
# ==============================================================================
step "Configuring Nginx at /rcia..."

NGINX_CONF="/etc/nginx/sites-available/api.konasalti.com"
NGINX_SNIPPET="${WORKING_DIR}/nginx/rcia.conf"
MARKER="# -- RCIA location block --"

if ! command -v nginx >/dev/null 2>&1; then
    warn "Nginx not installed. Skipping."
    echo -e "  Add the contents of ${BOLD}nginx/rcia.conf${NC} to your Nginx server block manually."

elif [ ! -f "$NGINX_CONF" ]; then
    warn "Nginx config not found at ${NGINX_CONF}. Skipping."
    echo -e "  Add the contents of ${BOLD}nginx/rcia.conf${NC} to your server's Nginx config manually."

elif grep -q "$MARKER" "$NGINX_CONF"; then
    warn "RCIA Nginx block already present in ${NGINX_CONF}. Skipping."

else
    # Build the injected block with the real port
    INJECT_BLOCK=$(sed "s/RCIA_PORT/${RCIA_PORT}/g" "$NGINX_SNIPPET")

    # Write to a temp file so we can safely test before applying
    TEMP_CONF=$(mktemp)
    # Insert our block before the final closing `}` of the server block
    awk -v block="${MARKER}"$'\n'"${INJECT_BLOCK}" '/^\}$/{print block} {print}' "$NGINX_CONF" > "$TEMP_CONF"

    # Validate the modified config with nginx -t
    if sudo nginx -c "$TEMP_CONF" -t 2>/dev/null; then
        sudo cp "$TEMP_CONF" "$NGINX_CONF"
        sudo systemctl reload nginx
        ok "Nginx reloaded. RCIA is live at https://api.konasalti.com/rcia"
    else
        warn "Nginx config test failed. Changes were NOT applied to protect existing services."
        echo -e "  Add the block from ${BOLD}nginx/rcia.conf${NC} to ${BOLD}${NGINX_CONF}${NC} manually."
    fi
    rm -f "$TEMP_CONF"
fi
# ==============================================================================
echo ""
echo -e "${GREEN}${BOLD}"
echo "  ╔═══════════════════════════════════════════╗"
echo "  ║       ✔  RCIA is ready to launch!         ║"
echo "  ╚═══════════════════════════════════════════╝"
echo -e "${NC}"
echo -e "  API Docs:   ${CYAN}http://<your-server-ip>:${RCIA_PORT}/docs${NC}"
echo -e "  Health:     ${CYAN}http://<your-server-ip>:${RCIA_PORT}/health${NC}"
echo ""
