#!/bin/bash

# Birthmark Standard - zkSync Testnet Deployment Script
#
# Purpose: Deploy BirthmarkRegistry smart contract to zkSync testnet
#
# Requirements:
#   - Node.js and npm installed
#   - Hardhat configured in packages/contracts/
#   - .env file with ZKSYNC_TESTNET_RPC and DEPLOYER_PRIVATE_KEY
#   - Testnet ETH in deployer wallet
#
# Phase: 1
# Status: Placeholder - Implementation pending
#
# Usage:
#   ./scripts/deploy_testnet.sh
#
# Environment Variables:
#   AGGREGATOR_ADDRESS - Address to authorize as aggregator (optional)

set -e  # Exit on error

echo "============================================="
echo "Birthmark zkSync Testnet Deployment"
echo "============================================="
echo ""

# Check if contracts directory exists
if [ ! -d "packages/contracts" ]; then
    echo "Error: packages/contracts directory not found"
    echo "Make sure you're running this from the project root"
    exit 1
fi

# Navigate to contracts directory
cd packages/contracts

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "Error: .env file not found in packages/contracts/"
    echo "Copy .env.example and configure:"
    echo "  ZKSYNC_TESTNET_RPC=https://testnet.era.zksync.dev"
    echo "  DEPLOYER_PRIVATE_KEY=0x..."
    exit 1
fi

echo "[1/5] Checking dependencies..."
if ! command -v npm &> /dev/null; then
    echo "Error: npm not found. Please install Node.js"
    exit 1
fi

# TODO: Implement deployment steps
#
# 1. Install dependencies (npm install)
# 2. Compile contracts (npx hardhat compile)
# 3. Run deployment script (npx hardhat run scripts/deploy.ts --network zksync-testnet)
# 4. Verify contract on zkSync explorer
# 5. Authorize aggregator address (if provided)
# 6. Save deployment info to deployments/ directory

echo ""
echo "[TODO] This script is a placeholder and will be implemented in Phase 1"
echo ""
echo "Expected implementation:"
echo "  1. npm install"
echo "  2. npx hardhat compile"
echo "  3. npx hardhat run scripts/deploy.ts --network zksync-testnet"
echo "  4. npx hardhat verify --network zksync-testnet <CONTRACT_ADDRESS>"
echo "  5. Authorize aggregator address"
echo "  6. Save deployment artifacts"
echo ""
echo "For now, deploy manually from packages/contracts/ directory:"
echo "  cd packages/contracts"
echo "  npm install"
echo "  npx hardhat compile"
echo "  npx hardhat run scripts/deploy.ts --network zksync-testnet"

cd ../..  # Return to project root
exit 0
