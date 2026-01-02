# Multi-stage build for Birthmark Substrate Node
FROM ubuntu:22.04 AS builder

# Install build dependencies
RUN apt-get update && \
    apt-get install -y \
    build-essential \
    git \
    clang \
    libclang-dev \
    pkg-config \
    libssl-dev \
    protobuf-compiler \
    curl && \
    rm -rf /var/lib/apt/lists/*

# Install Rust
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
ENV PATH="/root/.cargo/bin:${PATH}"

# Set working directory
WORKDIR /birthmark

# Copy source code
COPY . .

# Build in release mode
RUN cargo build --release

# Runtime stage
FROM ubuntu:22.04

# Install runtime dependencies
RUN apt-get update && \
    apt-get install -y \
    ca-certificates \
    libssl3 && \
    rm -rf /var/lib/apt/lists/*

# Copy built binary
COPY --from=builder /birthmark/target/release/birthmark-node /usr/local/bin/

# Create user
RUN useradd -m -u 1000 -U -s /bin/sh -d /birthmark birthmark

# Set up data directory
RUN mkdir -p /data && \
    chown -R birthmark:birthmark /data

USER birthmark

# Expose ports
# 9944: WebSocket RPC
# 9933: HTTP RPC
# 30333: P2P
# 9615: Prometheus metrics
EXPOSE 9944 9933 30333 9615

VOLUME ["/data"]

ENTRYPOINT ["/usr/local/bin/birthmark-node"]
CMD ["--chain", "production", "--base-path", "/data"]
