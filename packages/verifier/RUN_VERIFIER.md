# Running the Birthmark Image Verifier

Simple web application for verifying images against the Birthmark blockchain.

## Quick Start

### 1. Install Dependencies

```bash
cd /home/user/Birthmark/packages/verifier
pip install -r requirements.txt
```

### 2. Make Sure Blockchain Node is Running

The verifier queries the blockchain node at `http://localhost:8545`

```bash
# In another terminal
cd /home/user/Birthmark/packages/blockchain
python -m src.main
```

### 3. Start the Verifier

```bash
cd /home/user/Birthmark/packages/verifier
uvicorn src.app:app --host 0.0.0.0 --port 8080 --reload
```

### 4. Open in Browser

Navigate to: **http://localhost:8080**

## How to Use

### Upload an Image

1. Click the upload area or drag & drop an image
2. The image preview will appear
3. Click "Verify on Blockchain"
4. See verification results!

### Verification Results

**✅ Verified Images show:**
- Block height where image was stored
- Transaction ID
- Timestamp of authentication
- Modification level (Raw, Processed, or Modified)
- Submission server ID
- Parent image hash (for provenance chain tracking)

**❌ Not Verified Images show:**
- "Image not found on blockchain" message
- The image has not been authenticated through Birthmark

### Provenance Chain

If an image shows a parent hash, click it to verify the original raw image that this processed version came from. This shows the complete authentication chain from camera sensor to final image.

## Testing with Demo Images

After running the Phase 1 demo pipeline, you can verify the images:

```bash
# Run the demo first (in another terminal)
cd /home/user/Birthmark
python scripts/demo_phase1_pipeline.py
```

Then verify any image file that matches one of the hashes the demo submitted to the blockchain.

## API Endpoints

### POST /api/verify
Upload an image for verification

**Request:** multipart/form-data with `file` field
**Response:** VerificationResult JSON

### GET /api/verify-hash/{hash}
Verify a hash directly (64 character hex string)

**Response:** VerificationResult JSON

### GET /health
Health check endpoint

**Response:** Service status and blockchain connectivity

## Troubleshooting

### "Cannot connect to blockchain node"

**Problem:** Verifier can't reach blockchain node at localhost:8545

**Solution:** Start the blockchain node:
```bash
cd /home/user/Birthmark/packages/blockchain
python -m src.main
```

### "Image not verified" for demo images

**Problem:** Demo hasn't been run yet

**Solution:** Run the Phase 1 demo to populate blockchain:
```bash
cd /home/user/Birthmark
python scripts/demo_phase1_pipeline.py
```

### Port 8080 already in use

**Solution:** Use a different port:
```bash
uvicorn src.app:app --host 0.0.0.0 --port 8090
```

## Architecture

```
User Browser
     ↓
   Upload Image
     ↓
Verifier Web App (Port 8080)
     ↓
  Hash Image (SHA-256)
     ↓
Query Blockchain Node (Port 8545)
     ↓
  Return Results
     ↓
   Display to User
```

## Features

- **Drag & drop** image upload
- **Real-time** verification against blockchain
- **Provenance chain** tracking (click parent hashes)
- **Beautiful UI** with status indicators
- **Mobile responsive** design
- **Fast** - verification completes in <1 second

## Security

- All hashing happens server-side for consistency
- Direct connection to blockchain node (no intermediaries)
- Image files are not stored - only hashed
- Works with any image format (JPG, PNG, etc.)

## Next Steps

For production deployment:
- Add SSL/TLS certificate
- Configure proper CORS settings
- Add rate limiting
- Deploy behind reverse proxy (nginx)
- Point to production blockchain node

## Support

For issues or questions:
- Check blockchain node logs: `packages/blockchain/logs/`
- Check verifier logs in terminal output
- Verify blockchain contains hashes: `http://localhost:8545/api/v1/blockchain/status`
