#!/bin/bash
# Run all tests for Birthmark registry

set -e

echo "Running Birthmark pallet tests..."
cargo test -p pallet-birthmark --lib

echo ""
echo "Running runtime tests..."
cargo test -p birthmark-runtime

echo ""
echo "Running all workspace tests..."
cargo test

echo ""
echo "All tests passed!"
