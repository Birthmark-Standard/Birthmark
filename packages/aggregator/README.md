# Aggregator Package

**Phase:** Phase 1 (Hardware Prototype)
**Status:** In Development
**Technology:** FastAPI + PostgreSQL

## Overview

The aggregation server is the central hub of the Birthmark Standard system. It receives authentication bundles from cameras, validates them with the SMA, batches verified image hashes into Merkle trees, and posts Merkle roots to the zkSync blockchain.

## Architecture

```
Camera → Aggregator → SMA (validation)
            ↓
      Batch Queue
            ↓
      Merkle Tree
            ↓
      zkSync L2
```

## Key Components

### `src/api/`
FastAPI endpoints:
- `POST /api/v1/submit` - Receive authentication bundles from cameras
- `GET /api/v1/verify/{image_hash}` - Query verification status
- `GET /api/v1/health` - Health check endpoint

### `src/validation/`
SMA validation worker:
- Forwards encrypted NUC tokens to SMA
- Receives PASS/FAIL responses
- **Never shares image hashes with SMA**

### `src/batching/`
Merkle tree generation:
- Batches 1,000-5,000 validated image hashes
- Generates Merkle trees
- Creates and stores Merkle proofs for verification

### `src/blockchain/`
zkSync blockchain interface:
- Posts Merkle roots to smart contract
- Tracks transaction confirmations
- Updates database with blockchain references

## Database Schema

### `pending_submissions`
Stores incoming authentication bundles awaiting SMA validation.

### `batches`
Records of Merkle tree batches posted to blockchain.

### `image_batch_map`
Maps image hashes to batches with Merkle proofs for verification queries.

## Privacy Invariants

**CRITICAL:** The aggregator must maintain these privacy guarantees:
- SMA never receives image hashes (only encrypted NUC tokens)
- Individual cameras cannot be tracked (rotating encrypted tokens)
- Images are never stored (only SHA-256 hashes)

## Performance Targets

- API response time: <100ms for verification queries
- Batch processing: <5s for 1,000 images
- Cost per image: <$0.00003 on zkSync

## Setup

```bash
cd packages/aggregator
pip install -r requirements.txt
cp .env.example .env
# Edit .env with database credentials and SMA endpoint
uvicorn src.main:app --reload
```

## Testing

```bash
pytest tests/
```

## Related Documentation

- Architecture: `docs/phase-plans/Birthmark_Phase_1_Plan_Aggregation_Server.md`
- API specification: `shared/protocols/camera_to_aggregator.yaml`
