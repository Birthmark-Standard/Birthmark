#!/bin/bash
#
# Birthmark Camera - Service Installation Script
#
# Installs and enables the Birthmark camera systemd service.
#
# Usage:
#   sudo ./install_service.sh
#

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
BIRTHMARK_USER="${SUDO_USER:-pi}"
BIRTHMARK_HOME="/home/${BIRTHMARK_USER}/birthmark"
SERVICE_NAME="birthmark-camera"
SERVICE_FILE="${SERVICE_NAME}.service"

echo -e "${BLUE}"
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║        Birthmark Camera - Service Installation                ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}Error: Please run as root (sudo ./install_service.sh)${NC}"
    exit 1
fi

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Check if service file exists
if [ ! -f "${SCRIPT_DIR}/${SERVICE_FILE}" ]; then
    echo -e "${RED}Error: Service file not found: ${SCRIPT_DIR}/${SERVICE_FILE}${NC}"
    exit 1
fi

# Check prerequisites
echo -e "${GREEN}[1/5] Checking prerequisites...${NC}"

if [ ! -d "${BIRTHMARK_HOME}" ]; then
    echo -e "${RED}Error: Birthmark not installed at ${BIRTHMARK_HOME}${NC}"
    echo "Run setup_pi.sh first."
    exit 1
fi

if [ ! -f "${BIRTHMARK_HOME}/data/provisioning.json" ]; then
    echo -e "${YELLOW}Warning: Provisioning not installed${NC}"
    echo "The service will fail without provisioning data."
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Create log directory
echo -e "${GREEN}[2/5] Creating log directory...${NC}"
mkdir -p "${BIRTHMARK_HOME}/logs"
chown "${BIRTHMARK_USER}:${BIRTHMARK_USER}" "${BIRTHMARK_HOME}/logs"
echo "  ✓ Log directory: ${BIRTHMARK_HOME}/logs"

# Customize service file for this user
echo -e "${GREEN}[3/5] Customizing service file...${NC}"
TEMP_SERVICE="/tmp/${SERVICE_FILE}"
sed "s|/home/pi|/home/${BIRTHMARK_USER}|g; s|User=pi|User=${BIRTHMARK_USER}|g; s|Group=pi|Group=${BIRTHMARK_USER}|g" \
    "${SCRIPT_DIR}/${SERVICE_FILE}" > "${TEMP_SERVICE}"
echo "  ✓ Configured for user: ${BIRTHMARK_USER}"

# Install service file
echo -e "${GREEN}[4/5] Installing service...${NC}"
cp "${TEMP_SERVICE}" "/etc/systemd/system/${SERVICE_FILE}"
rm "${TEMP_SERVICE}"
systemctl daemon-reload
echo "  ✓ Service installed: ${SERVICE_FILE}"

# Enable service (but don't start yet)
echo -e "${GREEN}[5/5] Enabling service...${NC}"
systemctl enable "${SERVICE_NAME}"
echo "  ✓ Service enabled for auto-start"

# Summary
echo ""
echo -e "${BLUE}╔════════════════════════════════════════════════════════════════╗"
echo -e "║              Service Installation Complete!                    ║"
echo -e "╚════════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo "Service: ${SERVICE_NAME}"
echo "User:    ${BIRTHMARK_USER}"
echo "Logs:    ${BIRTHMARK_HOME}/logs/"
echo ""
echo -e "${YELLOW}Service commands:${NC}"
echo "  Start:   sudo systemctl start ${SERVICE_NAME}"
echo "  Stop:    sudo systemctl stop ${SERVICE_NAME}"
echo "  Status:  sudo systemctl status ${SERVICE_NAME}"
echo "  Logs:    journalctl -u ${SERVICE_NAME} -f"
echo "  Disable: sudo systemctl disable ${SERVICE_NAME}"
echo ""
echo -e "${GREEN}The service will start automatically on boot.${NC}"
echo ""
read -p "Start the service now? (y/N) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    systemctl start "${SERVICE_NAME}"
    sleep 2
    systemctl status "${SERVICE_NAME}" --no-pager
fi
