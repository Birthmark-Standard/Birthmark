#!/bin/bash

# Birthmark Standard - Device Provisioning Script
#
# Purpose: Provision a new camera device with:
#   - Device certificate (X.509, ECDSA P-256)
#   - NUC hash registration
#   - Key table assignments (3 random tables from 2,500)
#   - TPM/Secure Element initialization
#
# Phase: 1 (Raspberry Pi)
# Status: Placeholder - Implementation pending
#
# Usage:
#   ./scripts/provision_device.sh <device_serial> <sma_url>
#
# Example:
#   ./scripts/provision_device.sh BIRTHMARK-PI-00001 http://localhost:8001

set -e  # Exit on error

DEVICE_SERIAL=${1:-""}
SMA_URL=${2:-"http://localhost:8001"}

if [ -z "$DEVICE_SERIAL" ]; then
    echo "Error: Device serial number required"
    echo "Usage: $0 <device_serial> [sma_url]"
    exit 1
fi

echo "============================================="
echo "Birthmark Device Provisioning"
echo "============================================="
echo "Device Serial: $DEVICE_SERIAL"
echo "SMA URL: $SMA_URL"
echo ""

# TODO: Implement provisioning steps
#
# 1. Check if device is already provisioned
# 2. Initialize TPM/Secure Element
# 3. Generate device key pair (ECDSA P-256)
# 4. Create CSR (Certificate Signing Request)
# 5. Send CSR to SMA for signing
# 6. Receive device certificate and key table assignments
# 7. Store certificate in secure element
# 8. Compute NUC hash from camera sensor
# 9. Register NUC hash with SMA
# 10. Save provisioning data to device

echo "[TODO] This script is a placeholder and will be implemented in Phase 1"
echo ""
echo "Expected implementation:"
echo "  1. TPM initialization"
echo "  2. Key pair generation"
echo "  3. Certificate request to SMA"
echo "  4. NUC hash computation and registration"
echo "  5. Secure storage of credentials"
echo ""
echo "For now, use manual provisioning via Python scripts in packages/sma/"

exit 0
