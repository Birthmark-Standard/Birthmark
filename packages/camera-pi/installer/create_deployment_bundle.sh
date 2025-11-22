#!/bin/bash
#
# Birthmark Camera - Create Deployment Bundle
#
# Creates a self-contained deployment package that can be copied to
# a Raspberry Pi for installation without requiring git.
#
# Usage:
#   ./create_deployment_bundle.sh [output_directory]
#
# Example:
#   ./create_deployment_bundle.sh /tmp
#   # Creates: /tmp/birthmark-pi-bundle-YYYYMMDD.tar.gz
#

set -e

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

# Get script and package directories
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PACKAGE_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
REPO_DIR="$(cd "${PACKAGE_DIR}/../.." && pwd)"

# Output directory
OUTPUT_DIR="${1:-$(pwd)}"
DATE_STAMP=$(date +%Y%m%d)
BUNDLE_NAME="birthmark-pi-bundle-${DATE_STAMP}"
BUNDLE_DIR="${OUTPUT_DIR}/${BUNDLE_NAME}"

echo -e "${BLUE}"
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║        Birthmark Camera - Create Deployment Bundle            ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

echo -e "${GREEN}Creating deployment bundle...${NC}"
echo "  Source: ${PACKAGE_DIR}"
echo "  Output: ${OUTPUT_DIR}/${BUNDLE_NAME}.tar.gz"
echo ""

# Create bundle directory
rm -rf "${BUNDLE_DIR}"
mkdir -p "${BUNDLE_DIR}"

# Copy camera-pi package (excluding __pycache__, .git, etc.)
echo "  Copying camera-pi package..."
mkdir -p "${BUNDLE_DIR}/camera-pi"
rsync -a --exclude='__pycache__' \
         --exclude='*.pyc' \
         --exclude='.pytest_cache' \
         --exclude='*.egg-info' \
         --exclude='.git' \
         --exclude='dist' \
         --exclude='build' \
         --exclude='data/*.json' \
         "${PACKAGE_DIR}/" "${BUNDLE_DIR}/camera-pi/"

# Copy shared utilities if they exist
if [ -d "${REPO_DIR}/shared" ]; then
    echo "  Copying shared utilities..."
    mkdir -p "${BUNDLE_DIR}/shared"
    rsync -a --exclude='__pycache__' \
             --exclude='*.pyc' \
             "${REPO_DIR}/shared/" "${BUNDLE_DIR}/shared/"
fi

# Create install script wrapper
cat > "${BUNDLE_DIR}/install.sh" << 'INSTALL_EOF'
#!/bin/bash
#
# Birthmark Camera - Quick Install
#
# Installs the Birthmark camera system from this bundle.
#

set -e

BUNDLE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo ""
echo "Birthmark Camera - Quick Install"
echo "================================="
echo ""

# Check if running on Pi
if ! grep -q "Raspberry Pi" /proc/cpuinfo 2>/dev/null; then
    echo "Warning: This doesn't appear to be a Raspberry Pi"
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Create birthmark directory
BIRTHMARK_HOME="/home/${SUDO_USER:-${USER}}/birthmark"
echo "Installing to: ${BIRTHMARK_HOME}"

# Run main setup if root
if [ "$EUID" -eq 0 ]; then
    echo ""
    echo "Running system setup..."
    "${BUNDLE_DIR}/camera-pi/installer/setup_pi.sh"
else
    echo ""
    echo "For full system setup, run:"
    echo "  sudo ${BUNDLE_DIR}/install.sh"
    echo ""
    echo "Or manually:"
    echo "  1. sudo ${BUNDLE_DIR}/camera-pi/installer/setup_pi.sh"
    echo "  2. ${BUNDLE_DIR}/camera-pi/installer/install_provisioning.sh <provisioning.json>"
fi
INSTALL_EOF
chmod +x "${BUNDLE_DIR}/install.sh"

# Create version file
cat > "${BUNDLE_DIR}/VERSION" << EOF
Birthmark Camera Deployment Bundle
Created: $(date -Iseconds)
Package: camera-pi
Phase: 1 (Hardware Prototype)
EOF

# Create the tarball
echo "  Creating tarball..."
cd "${OUTPUT_DIR}"
tar -czf "${BUNDLE_NAME}.tar.gz" "${BUNDLE_NAME}"

# Cleanup
rm -rf "${BUNDLE_DIR}"

# Calculate size
BUNDLE_SIZE=$(du -h "${OUTPUT_DIR}/${BUNDLE_NAME}.tar.gz" | cut -f1)

echo ""
echo -e "${GREEN}Bundle created successfully!${NC}"
echo ""
echo "  File: ${OUTPUT_DIR}/${BUNDLE_NAME}.tar.gz"
echo "  Size: ${BUNDLE_SIZE}"
echo ""
echo "To deploy to a Raspberry Pi:"
echo "  1. Copy to Pi:  scp ${BUNDLE_NAME}.tar.gz pi@raspberrypi:/tmp/"
echo "  2. SSH to Pi:   ssh pi@raspberrypi"
echo "  3. Extract:     cd /tmp && tar -xzf ${BUNDLE_NAME}.tar.gz"
echo "  4. Install:     sudo /tmp/${BUNDLE_NAME}/install.sh"
echo ""
