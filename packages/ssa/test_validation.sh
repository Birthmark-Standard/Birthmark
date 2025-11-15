#!/bin/bash
# Test SSA validation endpoint

cd "$(dirname "$0")"

echo "Testing SSA Validation Endpoint"
echo "================================"
echo ""

# Compute baseline hash
echo "1. Computing baseline hash..."
BASELINE_HASH=$(sha256sum test_wrapper.py | cut -d' ' -f1)
echo "   Baseline hash: $BASELINE_HASH"
echo ""

# Load certificate
echo "2. Loading certificate..."
CERT=$(cat provisioned_software/test-wrapper-001/software_certificate.pem)
echo "   Certificate loaded"
echo ""

# Test validation with valid data
echo "3. Testing validation with valid version 1.0.0..."
RESPONSE=$(curl -s -X POST http://localhost:8001/api/v1/validate/software \
  -H "Content-Type: application/json" \
  -d "{
    \"software_certificate\": \"$CERT\",
    \"current_wrapper_hash\": \"$BASELINE_HASH\",
    \"version\": \"1.0.0\"
  }")
echo "$RESPONSE" | python3 -m json.tool
echo ""

# Test with invalid version
echo "4. Testing validation with invalid version 2.0.0 (should fail)..."
RESPONSE=$(curl -s -X POST http://localhost:8001/api/v1/validate/software \
  -H "Content-Type: application/json" \
  -d "{
    \"software_certificate\": \"$CERT\",
    \"current_wrapper_hash\": \"$BASELINE_HASH\",
    \"version\": \"2.0.0\"
  }")
echo "$RESPONSE" | python3 -m json.tool
echo ""

# Test adding new version
echo "5. Adding version 1.1.0 to valid versions..."
RESPONSE=$(curl -s -X POST http://localhost:8001/api/v1/versions/add \
  -H "Content-Type: application/json" \
  -d '{
    "software_id": "Test-Wrapper-001",
    "version": "1.1.0"
  }')
echo "$RESPONSE" | python3 -m json.tool
echo ""

# Test with newly added version (should still fail because hash doesn't match)
echo "6. Testing validation with newly added version 1.1.0 (should fail - hash mismatch)..."
RESPONSE=$(curl -s -X POST http://localhost:8001/api/v1/validate/software \
  -H "Content-Type: application/json" \
  -d "{
    \"software_certificate\": \"$CERT\",
    \"current_wrapper_hash\": \"$BASELINE_HASH\",
    \"version\": \"1.1.0\"
  }")
echo "$RESPONSE" | python3 -m json.tool
echo ""

echo "================================"
echo "Testing complete!"
