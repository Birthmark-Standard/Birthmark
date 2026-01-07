# Comprehensive verification script for Birthmark submissions
# Run this in PowerShell on Windows

Write-Host "`n" -NoNewline
Write-Host "=" * 70 -ForegroundColor Cyan
Write-Host "BIRTHMARK SUBMISSION VERIFICATION" -ForegroundColor Cyan
Write-Host "=" * 70 -ForegroundColor Cyan
Write-Host ""

# Step 1: Check Docker containers
Write-Host "[1/5] Checking Docker containers..." -ForegroundColor Yellow
try {
    $containers = docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
    Write-Host $containers -ForegroundColor Green

    if ($containers -match "birthmark-node") {
        Write-Host "  ✓ Blockchain node is running" -ForegroundColor Green
    } else {
        Write-Host "  ✗ Blockchain node is NOT running" -ForegroundColor Red
        Write-Host "  Run: docker-compose up -d" -ForegroundColor Yellow
        exit 1
    }
} catch {
    Write-Host "  ✗ Docker is not running or not accessible" -ForegroundColor Red
    Write-Host "  Start Docker Desktop and try again" -ForegroundColor Yellow
    exit 1
}

# Step 2: Check blockchain status
Write-Host "`n[2/5] Checking blockchain status..." -ForegroundColor Yellow
try {
    $response = Invoke-RestMethod -Uri "http://localhost:8545/api/v1/blockchain/status" -Method Get -TimeoutSec 5
    Write-Host "  ✓ Blockchain Height: $($response.height) blocks" -ForegroundColor Green
    Write-Host "  ✓ Total Transactions: $($response.transaction_count)" -ForegroundColor Green
    Write-Host "  ✓ Total Submissions: $($response.submission_count)" -ForegroundColor Green

    if ($response.height -eq 0) {
        Write-Host "  ⚠ Blockchain has no blocks yet (waiting for submissions)" -ForegroundColor Yellow
    }
} catch {
    Write-Host "  ✗ Cannot connect to blockchain at localhost:8545" -ForegroundColor Red
    Write-Host "  Error: $_" -ForegroundColor Red
    exit 1
}

# Step 3: Get latest capture from Pi
Write-Host "`n[3/5] Fetching latest capture from Raspberry Pi..." -ForegroundColor Yellow
$piHost = "birthmark@192.168.50.161"

try {
    # Check if plink is available
    $plinkTest = Get-Command plink -ErrorAction SilentlyContinue

    if (-not $plinkTest) {
        Write-Host "  ⚠ plink not found. Trying ssh..." -ForegroundColor Yellow
        $sshTest = Get-Command ssh -ErrorAction SilentlyContinue

        if (-not $sshTest) {
            Write-Host "  ✗ Neither plink nor ssh found" -ForegroundColor Red
            Write-Host "  Install PuTTY or OpenSSH to connect to Pi" -ForegroundColor Yellow
            Write-Host "  Skipping Pi connection..." -ForegroundColor Yellow
            $skipPi = $true
        } else {
            $sshCmd = "ssh"
        }
    } else {
        $sshCmd = "plink -batch"
    }

    if (-not $skipPi) {
        # Get latest capture file
        $latestFile = & $sshCmd $piHost "ls -t ~/Birthmark/packages/camera-pi/data/captures/IMG_*.json 2>/dev/null | head -1"

        if ($LASTEXITCODE -eq 0 -and $latestFile) {
            Write-Host "  ✓ Latest capture: $latestFile" -ForegroundColor Green

            # Fetch the capture data
            $captureJson = & $sshCmd $piHost "cat $latestFile"
            $capture = $captureJson | ConvertFrom-Json

            Write-Host "`n  Capture Details:" -ForegroundColor Cyan
            Write-Host "    Submission ID: $($capture.submission_id)"
            Write-Host "    Timestamp: $(Get-Date -UnixTimeSeconds $capture.timestamp -Format 'yyyy-MM-dd HH:mm:ss')"
            Write-Host "    Raw Hash: $($capture.raw_hash.Substring(0,16))..."
            Write-Host "    Processed Hash: $($capture.processed_hash.Substring(0,16))..."

            if ($capture.owner_hash) {
                Write-Host "    Owner: $($capture.owner_name)" -ForegroundColor Magenta
                Write-Host "    Owner Hash: $($capture.owner_hash.Substring(0,16))..."
            }

            $processedHash = $capture.processed_hash
        } else {
            Write-Host "  ✗ Could not get capture from Pi" -ForegroundColor Red
            Write-Host "  Check Pi connection at $piHost" -ForegroundColor Yellow
            $skipPi = $true
        }
    }
} catch {
    Write-Host "  ✗ Error connecting to Pi: $_" -ForegroundColor Red
    $skipPi = $true
}

# Step 4: Verify hash on blockchain
if ($processedHash) {
    Write-Host "`n[4/5] Verifying processed hash on blockchain..." -ForegroundColor Yellow

    try {
        $verifyUrl = "http://localhost:8545/api/v1/blockchain/verify/$processedHash"
        $verifyResponse = Invoke-RestMethod -Uri $verifyUrl -Method Get -TimeoutSec 5

        if ($verifyResponse.verified) {
            Write-Host "  ✓✓✓ IMAGE VERIFIED ON BLOCKCHAIN! ✓✓✓" -ForegroundColor Green -BackgroundColor DarkGreen
            Write-Host ""
            Write-Host "  Modification Level: $($verifyResponse.modification_level)" -ForegroundColor Green
            Write-Host "  Block Height: $($verifyResponse.block_height)" -ForegroundColor Green
            Write-Host "  Transaction ID: $($verifyResponse.tx_id)" -ForegroundColor Green
            Write-Host "  Timestamp: $(Get-Date -UnixTimeSeconds $verifyResponse.timestamp -Format 'yyyy-MM-dd HH:mm:ss')" -ForegroundColor Green

            if ($verifyResponse.owner_hash) {
                Write-Host "  Owner Hash: $($verifyResponse.owner_hash.Substring(0,16))..." -ForegroundColor Magenta
            }

            if ($verifyResponse.parent_image_hash) {
                Write-Host "  Parent Hash: $($verifyResponse.parent_image_hash.Substring(0,16))..." -ForegroundColor Cyan
                Write-Host "  (This image has provenance chain)" -ForegroundColor Cyan
            }
        } else {
            Write-Host "  ✗ Hash NOT verified on blockchain" -ForegroundColor Red
            Write-Host "  The submission may still be pending validation" -ForegroundColor Yellow
        }
    } catch {
        Write-Host "  ✗ Error verifying hash: $_" -ForegroundColor Red
    }
} else {
    Write-Host "`n[4/5] Skipping verification (no hash from Pi)" -ForegroundColor Yellow
    Write-Host "  You can manually verify by running:" -ForegroundColor Cyan
    Write-Host '  Invoke-RestMethod -Uri "http://localhost:8545/api/v1/blockchain/verify/<YOUR_HASH>"' -ForegroundColor Cyan
}

# Step 5: Check verifier
Write-Host "`n[5/5] Checking web verifier..." -ForegroundColor Yellow
try {
    $verifierResponse = Invoke-RestMethod -Uri "http://localhost:8080/health" -Method Get -TimeoutSec 5
    Write-Host "  ✓ Verifier is running at http://localhost:8080" -ForegroundColor Green
    Write-Host "  ✓ Blockchain connection: $($verifierResponse.blockchain_node.status)" -ForegroundColor Green
} catch {
    Write-Host "  ✗ Verifier is not running at localhost:8080" -ForegroundColor Red
    Write-Host "  Start verifier with: uvicorn src.app:app --host 0.0.0.0 --port 8080" -ForegroundColor Yellow
}

# Summary
Write-Host "`n" -NoNewline
Write-Host "=" * 70 -ForegroundColor Cyan
Write-Host "SUMMARY" -ForegroundColor Cyan
Write-Host "=" * 70 -ForegroundColor Cyan

if ($verifyResponse.verified) {
    Write-Host "✓ END-TO-END PIPELINE SUCCESSFUL!" -ForegroundColor Green -BackgroundColor DarkGreen
    Write-Host ""
    Write-Host "Camera → Submission Server → SMA Validation → Blockchain → ✓ VERIFIED" -ForegroundColor Green
    Write-Host ""
    Write-Host "Next steps:" -ForegroundColor Cyan
    Write-Host "  1. Open web verifier: http://localhost:8080" -ForegroundColor Yellow
    Write-Host "  2. Drag and drop the captured image file to verify visually" -ForegroundColor Yellow
    Write-Host "  3. Or paste the hash to verify: $($processedHash.Substring(0,32))..." -ForegroundColor Yellow
} else {
    Write-Host "⚠ Verification incomplete" -ForegroundColor Yellow
    Write-Host "Check the steps above for any errors" -ForegroundColor Yellow
}

Write-Host ""
