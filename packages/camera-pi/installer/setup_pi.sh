#!/bin/bash
#
# Birthmark Camera - Raspberry Pi Setup Script
#
# This script installs all dependencies and configures the Raspberry Pi
# for running the Birthmark camera authentication system.
#
# Usage:
#   chmod +x setup_pi.sh
#   sudo ./setup_pi.sh
#
# Requirements:
#   - Raspberry Pi 4 (or Pi 5) with Raspberry Pi OS (64-bit recommended)
#   - Raspberry Pi HQ Camera connected
#   - Internet connection for package downloads
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
BIRTHMARK_USER="${SUDO_USER:-pi}"
BIRTHMARK_HOME="/home/${BIRTHMARK_USER}/birthmark"
VENV_PATH="${BIRTHMARK_HOME}/venv"
DATA_DIR="${BIRTHMARK_HOME}/data"
LOG_DIR="${BIRTHMARK_HOME}/logs"

echo -e "${BLUE}"
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║        Birthmark Camera - Raspberry Pi Setup                  ║"
echo "║        Phase 1: Hardware Prototype                            ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}Error: Please run as root (sudo ./setup_pi.sh)${NC}"
    exit 1
fi

# Check if on Raspberry Pi
if ! grep -q "Raspberry Pi" /proc/cpuinfo 2>/dev/null; then
    echo -e "${YELLOW}Warning: This doesn't appear to be a Raspberry Pi${NC}"
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

echo -e "${GREEN}[1/7] Updating system packages...${NC}"
apt-get update
apt-get upgrade -y

echo -e "${GREEN}[2/7] Installing system dependencies...${NC}"
apt-get install -y \
    python3-pip \
    python3-venv \
    python3-dev \
    python3-picamera2 \
    libcamera-apps \
    libcamera-dev \
    libcap-dev \
    libatlas-base-dev \
    libjpeg-dev \
    libopenjp2-7 \
    libtiff5 \
    libssl-dev \
    git \
    curl \
    jq

# Install OpenCV dependencies
echo -e "${GREEN}[3/7] Installing OpenCV dependencies...${NC}"
apt-get install -y \
    libopencv-dev \
    python3-opencv

# Check camera connection
echo -e "${GREEN}[4/7] Checking camera connection...${NC}"
if libcamera-hello --list-cameras 2>/dev/null | grep -q "Available cameras"; then
    CAMERAS=$(libcamera-hello --list-cameras 2>&1 | grep -c "^\s*[0-9]:")
    if [ "$CAMERAS" -gt 0 ]; then
        echo -e "${GREEN}  ✓ Camera detected ($CAMERAS camera(s) available)${NC}"
        libcamera-hello --list-cameras 2>&1 | head -10
    else
        echo -e "${YELLOW}  ⚠ No cameras detected. Please check camera connection.${NC}"
    fi
else
    echo -e "${YELLOW}  ⚠ Could not query cameras. libcamera may need configuration.${NC}"
fi

# Create directory structure
echo -e "${GREEN}[5/7] Creating directory structure...${NC}"
mkdir -p "${BIRTHMARK_HOME}"
mkdir -p "${DATA_DIR}"
mkdir -p "${LOG_DIR}"
mkdir -p "${BIRTHMARK_HOME}/captures"

# Set ownership
chown -R "${BIRTHMARK_USER}:${BIRTHMARK_USER}" "${BIRTHMARK_HOME}"

# Create Python virtual environment
echo -e "${GREEN}[6/7] Setting up Python virtual environment...${NC}"
sudo -u "${BIRTHMARK_USER}" python3 -m venv "${VENV_PATH}" --system-site-packages

# Install Python packages
echo -e "${GREEN}[7/7] Installing Python dependencies...${NC}"
sudo -u "${BIRTHMARK_USER}" bash -c "
    source ${VENV_PATH}/bin/activate
    pip install --upgrade pip setuptools wheel
    pip install \
        numpy>=1.24.0 \
        cryptography>=41.0.0 \
        requests>=2.31.0 \
        pillow>=10.0.0 \
        pydantic>=2.5.0 \
        opencv-python-headless>=4.8.0
"

# Copy camera-pi package if we're in the repo
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ -f "${SCRIPT_DIR}/../pyproject.toml" ]; then
    echo -e "${GREEN}Installing Birthmark camera package...${NC}"
    cp -r "${SCRIPT_DIR}/.." "${BIRTHMARK_HOME}/camera-pi"
    chown -R "${BIRTHMARK_USER}:${BIRTHMARK_USER}" "${BIRTHMARK_HOME}/camera-pi"

    sudo -u "${BIRTHMARK_USER}" bash -c "
        source ${VENV_PATH}/bin/activate
        pip install -e ${BIRTHMARK_HOME}/camera-pi
    "
fi

# Create activation script
cat > "${BIRTHMARK_HOME}/activate.sh" << 'EOF'
#!/bin/bash
# Activate Birthmark environment
source /home/${USER}/birthmark/venv/bin/activate
export BIRTHMARK_HOME=/home/${USER}/birthmark
export BIRTHMARK_DATA=/home/${USER}/birthmark/data
echo "Birthmark environment activated"
echo "  BIRTHMARK_HOME: $BIRTHMARK_HOME"
echo "  BIRTHMARK_DATA: $BIRTHMARK_DATA"
EOF
chmod +x "${BIRTHMARK_HOME}/activate.sh"
chown "${BIRTHMARK_USER}:${BIRTHMARK_USER}" "${BIRTHMARK_HOME}/activate.sh"

# Create config template
cat > "${DATA_DIR}/config.json.template" << 'EOF'
{
    "aggregator_url": "http://YOUR_SERVER:8545",
    "sma_url": "http://YOUR_SERVER:8001",
    "capture_format": "SRGGB10",
    "capture_resolution": [4056, 3040],
    "auto_submit": true,
    "save_captures": false,
    "log_level": "INFO"
}
EOF
chown "${BIRTHMARK_USER}:${BIRTHMARK_USER}" "${DATA_DIR}/config.json.template"

# Enable camera interface
echo -e "${GREEN}Enabling camera interface...${NC}"
if command -v raspi-config &> /dev/null; then
    raspi-config nonint do_camera 0 2>/dev/null || true
fi

# Summary
echo ""
echo -e "${BLUE}╔════════════════════════════════════════════════════════════════╗"
echo -e "║                    Setup Complete!                             ║"
echo -e "╚════════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${GREEN}Birthmark has been installed to: ${BIRTHMARK_HOME}${NC}"
echo ""
echo "Directory structure:"
echo "  ${BIRTHMARK_HOME}/"
echo "  ├── venv/              # Python virtual environment"
echo "  ├── data/              # Provisioning data & config"
echo "  ├── logs/              # Application logs"
echo "  ├── captures/          # Captured images (if save enabled)"
echo "  └── activate.sh        # Environment activation script"
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo "  1. Copy provisioning file from SMA server:"
echo "     scp user@server:provisioning_PI-XXX.json ${DATA_DIR}/provisioning.json"
echo ""
echo "  2. Install provisioning data:"
echo "     cd ${BIRTHMARK_HOME}"
echo "     ./installer/install_provisioning.sh ${DATA_DIR}/provisioning.json"
echo ""
echo "  3. Configure server URLs:"
echo "     cp ${DATA_DIR}/config.json.template ${DATA_DIR}/config.json"
echo "     nano ${DATA_DIR}/config.json"
echo ""
echo "  4. Test the camera:"
echo "     source ${BIRTHMARK_HOME}/activate.sh"
echo "     python -m camera_pi.main --test"
echo ""
echo -e "${YELLOW}Note: A reboot may be required for camera changes to take effect.${NC}"
echo ""
read -p "Reboot now? (y/N) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    reboot
fi
