#!/bin/bash

# Birthmark Standard - End-to-End Integration Test
#
# Purpose: Test the complete Birthmark flow:
#   Camera → Aggregator → SMA → Blockchain → Verification
#
# Requirements:
#   - All services running (camera, aggregator, SMA)
#   - zkSync testnet contract deployed
#   - Test device provisioned
#
# Phase: 1
# Status: Placeholder - Implementation pending
#
# Usage:
#   ./scripts/integration_test.sh
#
# Environment Variables:
#   AGGREGATOR_URL - Aggregator API URL (default: http://localhost:8000)
#   SMA_URL - SMA API URL (default: http://localhost:8001)
#   CONTRACT_ADDRESS - BirthmarkRegistry contract address

set -e  # Exit on error

# Configuration
AGGREGATOR_URL=${AGGREGATOR_URL:-"http://localhost:8000"}
SMA_URL=${SMA_URL:-"http://localhost:8001"}
TEST_DEVICE="BIRTHMARK-TEST-001"
TEST_IMAGE="/tmp/birthmark_test_image.jpg"

echo "============================================="
echo "Birthmark End-to-End Integration Test"
echo "============================================="
echo "Aggregator: $AGGREGATOR_URL"
echo "SMA: $SMA_URL"
echo "Test Device: $TEST_DEVICE"
echo ""

# Function to check service health
check_service() {
    local service_name=$1
    local url=$2

    echo -n "Checking $service_name... "
    if curl -s -f "$url/api/v1/health" > /dev/null 2>&1; then
        echo "✓ OK"
        return 0
    else
        echo "✗ FAILED"
        return 1
    fi
}

echo "[1/7] Checking service health..."
check_service "Aggregator" "$AGGREGATOR_URL" || exit 1
check_service "SMA" "$SMA_URL" || exit 1
echo ""

# TODO: Implement integration test steps
#
# 1. Check all services are running and healthy
# 2. Provision test device (if not already provisioned)
# 3. Capture test image with camera
# 4. Compute image hash
# 5. Create authentication bundle
# 6. Submit bundle to aggregator
# 7. Wait for SMA validation
# 8. Wait for batch creation
# 9. Wait for blockchain posting
# 10. Verify image hash via verification API
# 11. Verify Merkle proof on blockchain
# 12. Clean up test data

echo "[TODO] This script is a placeholder and will be implemented in Phase 1"
echo ""
echo "Expected test flow:"
echo "  [2/7] Provisioning test device..."
echo "  [3/7] Capturing test image..."
echo "  [4/7] Submitting authentication bundle..."
echo "  [5/7] Waiting for SMA validation..."
echo "  [6/7] Waiting for blockchain confirmation..."
echo "  [7/7] Verifying image hash..."
echo ""
echo "Test criteria:"
echo "  ✓ Device provisioning successful"
echo "  ✓ Image capture and hash computation < 650ms"
echo "  ✓ Aggregator accepts submission (202 response)"
echo "  ✓ SMA validates token (PASS response)"
echo "  ✓ Batch posted to blockchain"
echo "  ✓ Verification query returns VERIFIED"
echo "  ✓ Merkle proof validates on-chain"
echo "  ✓ Total end-to-end time < 10 seconds"
echo ""
echo "For now, test manually by:"
echo "  1. Start aggregator: cd packages/aggregator && uvicorn src.main:app"
echo "  2. Start SMA: cd packages/sma && uvicorn src.main:app --port 8001"
echo "  3. Run camera: cd packages/camera-pi && python src/main.py"
echo "  4. Check verification: curl $AGGREGATOR_URL/api/v1/verify/<hash>"

exit 0
