#!/bin/bash
# Start development node with temporary storage

set -e

echo "Starting Birthmark development node..."
echo "RPC endpoints:"
echo "  WebSocket: ws://localhost:9944"
echo "  HTTP: http://localhost:9933"
echo ""
echo "Press Ctrl+C to stop"
echo ""

./target/release/birthmark-node --dev --tmp \
    --rpc-port 9944 \
    --rpc-external \
    --rpc-cors all \
    --rpc-methods=Unsafe
