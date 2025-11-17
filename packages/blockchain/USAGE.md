# Birthmark Blockchain Node - Usage Guide

Quick start guide for running the Birthmark blockchain node (merged aggregator + validator).

---

## Quick Start (Docker)

The fastest way to get started is using Docker Compose:

```bash
cd packages/blockchain

# Start PostgreSQL and blockchain node
docker compose up -d

# Check logs
docker compose logs -f blockchain-node

# Check status
curl http://localhost:8545/api/v1/status
```

That's it! The node is now running and accepting submissions.

---

## Manual Setup (Development)

### 1. Prerequisites

- Python 3.11+
- PostgreSQL 15+
- (Recommended) Python virtual environment

### 2. Install Dependencies

```bash
cd packages/blockchain

# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install package in development mode
pip install -e ".[dev]"
```

### 3. Configure Environment

```bash
# Copy example environment file
cp .env.example .env

# Edit .env with your settings
nano .env
```

Key settings:
```bash
NODE_ID=my_validator_001
DATABASE_URL=postgresql://birthmark:birthmark@localhost:5432/birthmark_chain
SMA_VALIDATION_ENDPOINT=http://localhost:8001/validate
BATCH_SIZE_MIN=100
BATCH_SIZE_MAX=1000
```

### 4. Start PostgreSQL

**Option A: Docker**
```bash
docker compose up -d postgres
```

**Option B: Local PostgreSQL**
```bash
createdb birthmark_chain
```

### 5. Run Database Migrations

```bash
# Apply migrations
alembic upgrade head
```

### 6. Initialize Genesis Block

```bash
# Create genesis block (block 0)
python scripts/init_genesis.py
```

You should see:
```
INFO - Genesis block created!
INFO -   Block height: 0
INFO -   Block hash: abc123...
INFO -   Timestamp: 1700000000
INFO -   Validator: my_validator_001
INFO - Genesis initialization complete!
```

### 7. Start Node

```bash
# Development mode (with auto-reload)
uvicorn src.main:app --reload --port 8545

# Or production mode
python -m src.main
```

Node will start on http://localhost:8545

---

## Testing the Node

### 1. Check Node Status

```bash
curl http://localhost:8545/api/v1/status | jq
```

Expected response:
```json
{
  "node_id": "my_validator_001",
  "block_height": 0,
  "total_hashes": 0,
  "pending_submissions": 0,
  "last_block_time": null,
  "validator_nodes": 1,
  "consensus_mode": "single",
  "uptime": "0:05:23"
}
```

### 2. Submit Test Image Hash

**Important:** The SMA (Simulated Manufacturer Authority) must be running at the configured endpoint for validation to work.

```bash
# First, start the SMA (in another terminal)
cd packages/sma
uvicorn src.main:app --port 8001

# Then submit a test hash
curl -X POST http://localhost:8545/api/v1/submit \
  -H "Content-Type: application/json" \
  -d '{
    "image_hash": "abc123def456789012345678901234567890abcdef1234567890abcdef123456",
    "encrypted_nuc_token": "dGVzdF9lbmNyeXB0ZWRfdG9rZW4=",
    "table_references": [42, 100, 200],
    "key_indices": [7, 99, 512],
    "timestamp": '$(date +%s)',
    "device_signature": "dGVzdF9zaWduYXR1cmU="
  }'
```

Response:
```json
{
  "receipt_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "pending_validation",
  "message": "Submission received and queued for validation"
}
```

### 3. Wait for Batching

The batching service runs every 30 seconds. After accumulating at least `BATCH_SIZE_MIN` submissions (default: 100), a new block will be created.

For testing with fewer submissions, you can temporarily lower the batch size in `.env`:
```bash
BATCH_SIZE_MIN=1
BATCH_SIZE_MAX=10
```

Then restart the node.

### 4. Verify Image Hash

```bash
# Query the blockchain to verify the hash
curl http://localhost:8545/api/v1/verify/abc123def456789012345678901234567890abcdef1234567890abcdef123456 | jq
```

If found:
```json
{
  "verified": true,
  "image_hash": "abc123def456789012345678901234567890abcdef1234567890abcdef123456",
  "timestamp": 1700000000,
  "block_height": 1,
  "aggregator": "my_validator_001",
  "tx_hash": null,
  "gps_hash": null
}
```

If not found:
```json
{
  "verified": false,
  "image_hash": "abc123def456789012345678901234567890abcdef1234567890abcdef123456",
  "timestamp": null,
  "block_height": null,
  "aggregator": null,
  "tx_hash": null,
  "gps_hash": null
}
```

### 5. Query Blocks

```bash
# Get latest block
curl http://localhost:8545/api/v1/block/latest | jq

# Get specific block by height
curl http://localhost:8545/api/v1/block/1 | jq
```

---

## Integration with Camera

The blockchain node receives submissions from cameras via the `/api/v1/submit` endpoint.

**Camera integration example (Python):**

```python
import hashlib
import requests
import time

# Compute SHA-256 of image
with open("photo.raw", "rb") as f:
    image_data = f.read()
    image_hash = hashlib.sha256(image_data).hexdigest()

# Prepare authentication bundle
bundle = {
    "image_hash": image_hash,
    "encrypted_nuc_token": camera_token.encode('utf-8'),  # From TPM
    "table_references": [42, 1337, 2001],  # Camera's assigned tables
    "key_indices": [7, 99, 512],  # Random indices
    "timestamp": int(time.time()),
    "device_signature": camera_signature,  # TPM signature
}

# Submit to blockchain node
response = requests.post(
    "http://localhost:8545/api/v1/submit",
    json=bundle,
)

print(f"Receipt ID: {response.json()['receipt_id']}")
```

See `packages/camera-pi/` for full camera implementation.

---

## Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ -v --cov=src --cov-report=html

# Run specific test
pytest tests/test_basic.py::TestHashing::test_sha256_hex -v
```

---

## Database Management

### View Database Contents

```bash
# Connect to database
psql birthmark_chain

# Useful queries
SELECT * FROM blocks;
SELECT * FROM image_hashes LIMIT 10;
SELECT COUNT(*) FROM image_hashes;
SELECT * FROM pending_submissions WHERE sma_validated = false;
```

### Reset Database

```bash
# WARNING: This deletes all data

# Downgrade to base
alembic downgrade base

# Upgrade to latest
alembic upgrade head

# Recreate genesis
python scripts/init_genesis.py
```

### Create New Migration

```bash
# After modifying models
alembic revision --autogenerate -m "Add new field"

# Review generated migration
cat alembic/versions/202411_*_add_new_field.py

# Apply migration
alembic upgrade head
```

---

## Monitoring

### Logs

```bash
# Docker
docker compose logs -f blockchain-node

# Manual
tail -f /var/log/birthmark-node.log
```

### Metrics

Current node status:
```bash
watch -n 5 'curl -s http://localhost:8545/api/v1/status | jq'
```

### Database Size

```bash
psql birthmark_chain -c "
SELECT
    pg_size_pretty(pg_database_size('birthmark_chain')) as database_size,
    (SELECT COUNT(*) FROM blocks) as total_blocks,
    (SELECT COUNT(*) FROM image_hashes) as total_hashes;
"
```

---

## Troubleshooting

### Node Won't Start

**Check PostgreSQL:**
```bash
docker compose ps
# or
pg_isready
```

**Check migrations:**
```bash
alembic current
alembic upgrade head
```

### SMA Validation Failing

**Verify SMA is running:**
```bash
curl http://localhost:8001/health
```

**Check SMA endpoint in .env:**
```bash
echo $SMA_VALIDATION_ENDPOINT
```

**View validation errors:**
```bash
psql birthmark_chain -c "
SELECT image_hash, validation_result, validation_attempted_at
FROM pending_submissions
WHERE sma_validated = false;
"
```

### No Blocks Being Created

**Check pending submissions:**
```bash
psql birthmark_chain -c "
SELECT COUNT(*) FROM pending_submissions WHERE sma_validated = true AND batched = false;
"
```

If count is less than `BATCH_SIZE_MIN`, you need more submissions.

**Check batching service logs:**
```bash
# Should see "Found X validated submissions to batch" every 30 seconds
docker compose logs -f blockchain-node | grep batching
```

### Genesis Block Already Exists

This is normal if you've already initialized. To reset:
```bash
alembic downgrade base
alembic upgrade head
python scripts/init_genesis.py
```

---

## Production Deployment

### Systemd Service

Create `/etc/systemd/system/birthmark-node.service`:

```ini
[Unit]
Description=Birthmark Blockchain Node
After=network.target postgresql.service

[Service]
Type=simple
User=birthmark
WorkingDirectory=/opt/birthmark/packages/blockchain
Environment="PATH=/opt/birthmark/venv/bin"
ExecStart=/opt/birthmark/venv/bin/python -m src.main
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl enable birthmark-node
sudo systemctl start birthmark-node
sudo systemctl status birthmark-node
```

### Docker Production

```yaml
# docker-compose.prod.yml
version: '3.8'

services:
  postgres:
    image: postgres:15-alpine
    restart: always
    volumes:
      - /var/lib/birthmark/postgres:/var/lib/postgresql/data
    environment:
      POSTGRES_PASSWORD_FILE: /run/secrets/db_password

  blockchain-node:
    build: .
    restart: always
    depends_on:
      - postgres
    volumes:
      - /var/lib/birthmark/data:/data
    ports:
      - "8545:8545"
    environment:
      DATABASE_URL: postgresql://birthmark:${DB_PASSWORD}@postgres:5432/birthmark_chain
```

---

## API Documentation

Interactive API docs available at:
- **Swagger UI:** http://localhost:8545/docs
- **ReDoc:** http://localhost:8545/redoc

---

## Next Steps

1. **Phase 1 Testing:** Submit 500+ test images from Raspberry Pi camera
2. **Performance Tuning:** Optimize database queries and batch sizes
3. **Integration:** Connect to camera-pi package
4. **Phase 2:** Add multi-node consensus and P2P networking

---

## Support

- **Issues:** https://github.com/Birthmark-Standard/Birthmark/issues
- **Documentation:** `/docs/`
- **Architecture:** `README.md`

---

**The Birthmark Standard: Proving images are real, not generated.**
