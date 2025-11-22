#!/bin/bash
#
# Birthmark Camera - Provisioning Installation Script
#
# Installs device provisioning data from SMA to the local system.
# Validates the provisioning file and sets appropriate permissions.
#
# Usage:
#   ./install_provisioning.sh <provisioning_file.json>
#
# Example:
#   ./install_provisioning.sh /tmp/provisioning_PI-001.json
#

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
BIRTHMARK_HOME="${BIRTHMARK_HOME:-/home/${USER}/birthmark}"
DATA_DIR="${BIRTHMARK_HOME}/data"
PROVISIONING_FILE="${DATA_DIR}/provisioning.json"

echo -e "${BLUE}"
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║        Birthmark - Provisioning Installation                  ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Check arguments
if [ $# -lt 1 ]; then
    echo -e "${RED}Error: No provisioning file specified${NC}"
    echo ""
    echo "Usage: $0 <provisioning_file.json>"
    echo ""
    echo "Example:"
    echo "  $0 /tmp/provisioning_PI-001.json"
    exit 1
fi

INPUT_FILE="$1"

# Check if input file exists
if [ ! -f "$INPUT_FILE" ]; then
    echo -e "${RED}Error: Provisioning file not found: $INPUT_FILE${NC}"
    exit 1
fi

# Validate JSON structure
echo -e "${GREEN}[1/5] Validating provisioning file...${NC}"

# Check if jq is available
if ! command -v jq &> /dev/null; then
    echo -e "${YELLOW}Warning: jq not installed. Skipping JSON validation.${NC}"
else
    # Required fields
    REQUIRED_FIELDS=("device_serial" "device_certificate" "certificate_chain" "device_private_key" "device_public_key" "table_assignments" "nuc_hash" "device_family" "master_keys")

    for field in "${REQUIRED_FIELDS[@]}"; do
        if ! jq -e ".$field" "$INPUT_FILE" > /dev/null 2>&1; then
            echo -e "${RED}Error: Missing required field: $field${NC}"
            exit 1
        fi
    done

    # Validate table_assignments has 3 entries
    TABLE_COUNT=$(jq '.table_assignments | length' "$INPUT_FILE")
    if [ "$TABLE_COUNT" != "3" ]; then
        echo -e "${RED}Error: table_assignments must have exactly 3 entries (found $TABLE_COUNT)${NC}"
        exit 1
    fi

    # Validate master_keys matches table_assignments
    for table_id in $(jq -r '.table_assignments[]' "$INPUT_FILE"); do
        if ! jq -e ".master_keys[\"$table_id\"]" "$INPUT_FILE" > /dev/null 2>&1; then
            echo -e "${RED}Error: Missing master_key for table $table_id${NC}"
            exit 1
        fi
    done

    # Extract device info
    DEVICE_SERIAL=$(jq -r '.device_serial' "$INPUT_FILE")
    DEVICE_FAMILY=$(jq -r '.device_family' "$INPUT_FILE")
    NUC_HASH=$(jq -r '.nuc_hash' "$INPUT_FILE")

    echo -e "  ✓ JSON structure valid"
    echo -e "  ✓ Device serial: ${DEVICE_SERIAL}"
    echo -e "  ✓ Device family: ${DEVICE_FAMILY}"
    echo -e "  ✓ NUC hash: ${NUC_HASH:0:16}..."
fi

# Create data directory if needed
echo -e "${GREEN}[2/5] Creating data directory...${NC}"
mkdir -p "$DATA_DIR"
echo -e "  ✓ Data directory: $DATA_DIR"

# Backup existing provisioning if present
if [ -f "$PROVISIONING_FILE" ]; then
    echo -e "${GREEN}[3/5] Backing up existing provisioning...${NC}"
    BACKUP_FILE="${PROVISIONING_FILE}.backup.$(date +%Y%m%d_%H%M%S)"
    cp "$PROVISIONING_FILE" "$BACKUP_FILE"
    echo -e "  ✓ Backup saved: $BACKUP_FILE"
else
    echo -e "${GREEN}[3/5] No existing provisioning to backup${NC}"
fi

# Install provisioning file
echo -e "${GREEN}[4/5] Installing provisioning data...${NC}"
cp "$INPUT_FILE" "$PROVISIONING_FILE"
echo -e "  ✓ Installed to: $PROVISIONING_FILE"

# Set secure permissions (owner read/write only)
echo -e "${GREEN}[5/5] Setting secure permissions...${NC}"
chmod 600 "$PROVISIONING_FILE"
echo -e "  ✓ Permissions set to 600 (owner read/write only)"

# Summary
echo ""
echo -e "${BLUE}╔════════════════════════════════════════════════════════════════╗"
echo -e "║              Provisioning Installation Complete!              ║"
echo -e "╚════════════════════════════════════════════════════════════════╝${NC}"
echo ""

if command -v jq &> /dev/null; then
    echo "Device Information:"
    echo "  Serial:     $DEVICE_SERIAL"
    echo "  Family:     $DEVICE_FAMILY"
    echo "  Tables:     $(jq -c '.table_assignments' "$INPUT_FILE")"
    echo "  NUC Hash:   ${NUC_HASH:0:32}..."
    echo ""
fi

echo -e "${YELLOW}Security Notice:${NC}"
echo "  The provisioning file contains your device's private key."
echo "  It has been secured with restrictive permissions (600)."
echo "  Do NOT share this file or commit it to version control."
echo ""
echo -e "${GREEN}Next steps:${NC}"
echo "  1. Configure server URLs in ${DATA_DIR}/config.json"
echo "  2. Test the installation:"
echo "     source ${BIRTHMARK_HOME}/activate.sh"
echo "     python -m camera_pi.main --test"
echo ""
