# Birthmark Phase 1 - Startup Checklist

Complete checklist for running all Phase 1 components on a single workstation.

---

## Prerequisites (One-Time Setup)

### ✅ 1. PostgreSQL Database Setup

- [ ] PostgreSQL 16 installed
- [ ] PostgreSQL service running
  ```bash
  pg_ctlcluster 16 main status
  # If not running:
  pg_ctlcluster 16 main start
  ```
- [ ] Database and user created
  ```bash
  psql -U postgres -c "SELECT 1 FROM pg_database WHERE datname='birthmark_chain'" | grep -q 1 || \
    psql -U postgres -c "CREATE DATABASE birthmark_chain OWNER birthmark"
  ```
- [ ] Database migrations applied
  ```bash
  cd /home/user/Birthmark/packages/blockchain
  alembic upgrade head
  ```

**Verify:**
```bash
psql -U birthmark -d birthmark_chain -c "\dt"
# Should show: blocks, transactions, image_hashes, pending_submissions, node_state, modification_records
```

---

### ✅ 2. SMA (Simulated Manufacturer Authority) Setup

- [ ] Dependencies installed
  ```bash
  cd /home/user/Birthmark/packages/sma
  pip install -e .
  ```
- [ ] CA certificates generated
  ```bash
  ls packages/sma/certs/ca_certificate.pem
  # If missing, run:
  python scripts/generate_ca_certificate.py
  ```
- [ ] Key tables generated
  ```bash
  ls packages/sma/data/key_tables.json
  # If missing, run:
  python scripts/setup_sma.py
  ```
- [ ] Camera provisioned
  ```bash
  ls packages/sma/data/device_registry.json
  # Should contain at least one device (BIRTHMARK_PI_001 or similar)
  ```

**Verify:**
```bash
cd /home/user/Birthmark/packages/sma
python -c "
from pathlib import Path
import json

registry = Path('data/device_registry.json')
if registry.exists():
    data = json.load(open(registry))
    print(f'✅ {len(data.get(\"devices\", []))} devices provisioned')
else:
    print('❌ No devices provisioned')
"
```

---

### ✅ 3. Blockchain Node Setup

- [ ] Dependencies installed
  ```bash
  cd /home/user/Birthmark/packages/blockchain
  pip install -e ".[dev]"
  ```
- [ ] Environment configured
  ```bash
  ls packages/blockchain/.env
  # Should exist with DATABASE_URL, SMA_VALIDATION_ENDPOINT, etc.
  ```
- [ ] Database connection tested
  ```bash
  cd /home/user/Birthmark/packages/blockchain
  python -c "
from src.shared.database import SyncSessionLocal
db = SyncSessionLocal()
print('✅ Database connection successful')
db.close()
  "
  ```

---

### ✅ 4. Verifier Setup

- [ ] Dependencies installed
  ```bash
  cd /home/user/Birthmark/packages/verifier
  pip install -r requirements.txt
  ```

---

### ✅ 5. Demo Script Setup (Optional - for testing)

- [ ] Camera provisioning data exists
  ```bash
  ls /home/user/Birthmark/packages/camera-pi/data/provisioning_data.json
  # If missing, provision a test camera in SMA
  ```

---

## Running the System

### Terminal 1: PostgreSQL

```bash
# Check if running
pg_ctlcluster 16 main status

# If not running, start it
pg_ctlcluster 16 main start

# Verify
psql -U birthmark -d birthmark_chain -c "SELECT current_database();"
```

**Expected output:**
```
 current_database
------------------
 birthmark_chain
```

**Keep this terminal open for monitoring PostgreSQL logs if needed**

---

### Terminal 2: SMA (Simulated Manufacturer Authority)

```bash
cd /home/user/Birthmark/packages/sma
uvicorn src.main:app --host 0.0.0.0 --port 8001 --reload
```

**Expected output:**
```
✓ Loaded Phase 1 key tables: 10 tables
✓ Loaded 1 device registrations
✓ Device provisioner ready
INFO:     Uvicorn running on http://0.0.0.0:8001
```

**Test it:**
```bash
# In another terminal
curl http://localhost:8001/health
```

**Expected:** `{"status":"healthy", ...}`

---

### Terminal 3: Blockchain Node (Submission Server + Blockchain)

```bash
cd /home/user/Birthmark/packages/blockchain
python -m src.main
```

**Expected output:**
```
Starting Birthmark Blockchain Node: phase1_blockchain_node
Consensus mode: single
INFO:     Uvicorn running on http://0.0.0.0:8545
```

**Test it:**
```bash
# In another terminal
curl http://localhost:8545/api/v1/blockchain/status
```

**Expected:** `{"node_id":"phase1_blockchain_node","block_height":0,"total_hashes":0,...}`

---

### Terminal 4: Verifier Web App

```bash
cd /home/user/Birthmark/packages/verifier
uvicorn src.app:app --host 0.0.0.0 --port 8080 --reload
```

**Expected output:**
```
INFO:     Uvicorn running on http://0.0.0.0:8080
```

**Test it:**
Open browser to: **http://localhost:8080**

Should see the Birthmark Image Verifier interface.

---

## Testing the System (Optional)

### Terminal 5: Run Demo Script

```bash
cd /home/user/Birthmark
python scripts/demo_phase1_pipeline.py
```

**This will:**
1. Check all services are running
2. Simulate camera capture
3. Submit to blockchain node
4. Validate with SMA
5. Store on blockchain
6. Verify the hashes

**Watch Terminal 3 (Blockchain Node) for detailed logs showing:**
- 📨 Camera submission received
- 🔒 SMA validation
- ⛓️ Blockchain storage
- 🔍 Verification queries

---

## Service Health Check URLs

Once everything is running, these URLs should all respond:

- [ ] SMA Health: http://localhost:8001/health
- [ ] SMA Stats: http://localhost:8001/stats
- [ ] Blockchain Status: http://localhost:8545/api/v1/blockchain/status
- [ ] Verifier Health: http://localhost:8080/health
- [ ] Verifier UI: http://localhost:8080

---

## Quick Verification

After running the demo, test the verifier:

1. Open http://localhost:8080
2. Upload any image file
3. Click "Verify on Blockchain"
4. Should get result (verified or not verified depending on the image)

To test with a verified image, you need an image whose hash matches one submitted by the demo script.

---

## Troubleshooting

### PostgreSQL won't start
```bash
# Check logs
tail -f /var/log/postgresql/postgresql-16-main.log

# Check permissions
ls -la /etc/postgresql/16/main/
# Should be owned by postgres or claude (matching data directory owner)
```

### SMA can't load key tables
```bash
cd /home/user/Birthmark/packages/sma
python scripts/setup_sma.py
```

### Blockchain node can't connect to database
```bash
# Check .env file
cat packages/blockchain/.env | grep DATABASE_URL

# Test connection
psql -U birthmark -d birthmark_chain -c "SELECT 1"
```

### Blockchain node can't reach SMA
```bash
# Check SMA is running on port 8001
curl http://localhost:8001/health

# Check .env file
cat packages/blockchain/.env | grep SMA_VALIDATION_ENDPOINT
```

### Verifier can't reach blockchain
```bash
# Check blockchain node is running on port 8545
curl http://localhost:8545/api/v1/blockchain/status

# Blockchain node must be running before starting verifier
```

### Port already in use
```bash
# Find what's using the port
lsof -i :8001  # or :8545, :8080

# Use different port
uvicorn src.main:app --port 8002  # for example
```

---

## Shutdown Procedure

**Graceful shutdown order:**

1. Stop verifier (Ctrl+C in Terminal 4)
2. Stop blockchain node (Ctrl+C in Terminal 3)
3. Stop SMA (Ctrl+C in Terminal 2)
4. PostgreSQL can stay running or stop with:
   ```bash
   pg_ctlcluster 16 main stop
   ```

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Your Workstation                        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │  PostgreSQL  │  │     SMA      │  │  Blockchain  │     │
│  │   (5432)     │  │   (8001)     │  │    (8545)    │     │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘     │
│         │                 │                  │              │
│         │                 │◄─────validate────┤              │
│         │                 │                  │              │
│         └────────────────►│◄─────query───────┘              │
│                           │                                 │
│                  ┌────────▼────────┐                        │
│                  │    Verifier     │                        │
│                  │     (8080)      │                        │
│                  └─────────────────┘                        │
│                           ▲                                 │
└───────────────────────────┼─────────────────────────────────┘
                            │
                     ┌──────▼──────┐
                     │   Browser   │
                     │ (User)      │
                     └─────────────┘
```

---

## Port Summary

| Service          | Port | URL                            |
|------------------|------|--------------------------------|
| PostgreSQL       | 5432 | localhost:5432                 |
| SMA              | 8001 | http://localhost:8001          |
| Blockchain Node  | 8545 | http://localhost:8545          |
| Verifier         | 8080 | http://localhost:8080          |

---

## Next Steps

Once all services are running:

1. ✅ Run demo script to populate blockchain
2. ✅ Test verifier with demo images
3. ✅ View logs in Terminal 3 to see packet contents
4. 🎬 Ready for presentation!

---

## For Presentation

**Recommended terminal layout:**

```
┌─────────────────┬─────────────────┐
│   Terminal 2    │   Terminal 3    │
│   SMA Logs      │ Blockchain Logs │
│   (Port 8001)   │   (Port 8545)   │
├─────────────────┼─────────────────┤
│   Terminal 4    │   Browser       │
│ Verifier Logs   │   Verifier UI   │
│   (Port 8080)   │ localhost:8080  │
└─────────────────┴─────────────────┘
```

**Terminal 3** shows the most interesting logs:
- Complete submission contents
- SMA validation requests/responses
- Blockchain storage confirmations

Perfect for demonstrating transparency!
