#!/bin/bash
# Build script for Birthmark Substrate node

set -e

echo "Building Birthmark Substrate Node..."
echo "This may take 20-40 minutes on first build..."

# Build in release mode
cargo build --release

echo ""
echo "Build complete!"
echo "Binary location: ./target/release/birthmark-node"
echo ""
echo "Run development node:"
echo "  ./target/release/birthmark-node --dev --tmp"
echo ""
echo "Run production validator:"
echo "  ./target/release/birthmark-node --chain production --validator"
