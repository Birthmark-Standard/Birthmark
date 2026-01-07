# Birthmark Submission Verification (Simple version)

Write-Host ""
Write-Host "======================================================================"
Write-Host "BIRTHMARK SUBMISSION VERIFICATION"
Write-Host "======================================================================"
Write-Host ""

# Step 1: Check Docker containers
Write-Host "[1/5] Checking Docker containers..." -ForegroundColor Yellow
try {
    $containers = docker ps --format "{{.Names}}" 2>$null

    if ($containers -match "birthmark-node") {
        Write-Host "  [OK] Blockchain node is running" -ForegroundColor Green
    } else {
        Write-Host "  [ERROR] Blockchain node is NOT running" -ForegroundColor Red
        Write-Host "  Run: docker-compose up -d" -ForegroundColor Yellow
        exit 1
    }
} catch {
    Write-Host "  [ERROR] Docker is not running" -ForegroundColor Red
    exit 1
}

# Step 2: Check blockchain status
Write-Host ""
Write-Host "[2/5] Checking blockchain status..." -ForegroundColor Yellow
try {
    $response = Invoke-RestMethod -Uri "http://localhost:8545/api/v1/blockchain/status" -Method Get -TimeoutSec 5
    Write-Host "  [OK] Blockchain Height: $($response.height) blocks" -ForegroundColor Green
    Write-Host "  [OK] Total Transactions: $($response.transaction_count)" -ForegroundColor Green
    Write-Host "  [OK] Total Submissions: $($response.submission_count)" -ForegroundColor Green
} catch {
    Write-Host "  [ERROR] Cannot connect to blockchain" -ForegroundColor Red
    Write-Host "  Error: $_" -ForegroundColor Red
    exit 1
}

# Step 3: Get latest capture from Pi
Write-Host ""
Write-Host "[3/5] Fetching latest capture from Raspberry Pi..." -ForegroundColor Yellow
$piHost = "birthmark@192.168.50.161"

try {
    # Check if plink is available
    if (Get-Command plink -ErrorAction SilentlyContinue) {
        $sshCmd = "plink"
        $sshArgs = "-batch", $piHost
    } elseif (Get-Command ssh -ErrorAction SilentlyContinue) {
        $sshCmd = "ssh"
        $sshArgs = $piHost
    } else {
        Write-Host "  [WARN] No SSH client found, skipping Pi connection" -ForegroundColor Yellow
        $skipPi = $true
    }

    if (-not $skipPi) {
        # Get latest capture file
        $cmd = "ls -t ~/Birthmark/packages/camera-pi/data/captures/IMG_*.json 2>/dev/null | head -1"
        $latestFile = & $sshCmd @sshArgs $cmd 2>$null

        if ($LASTEXITCODE -eq 0 -and $latestFile) {
            Write-Host "  [OK] Latest capture: $latestFile" -ForegroundColor Green

            # Fetch the capture data
            $captureJson = & $sshCmd @sshArgs "cat $latestFile" 2>$null
            $capture = $captureJson | ConvertFrom-Json

            Write-Host ""
            Write-Host "  Capture Details:" -ForegroundColor Cyan
            Write-Host "    Submission ID: $($capture.submission_id)"
            Write-Host "    Raw Hash: $($capture.raw_hash.Substring(0,16))..."
            Write-Host "    Processed Hash: $($capture.processed_hash.Substring(0,16))..."

            if ($capture.owner_hash) {
                Write-Host "    Owner: $($capture.owner_name)" -ForegroundColor Magenta
            }

            $processedHash = $capture.processed_hash
        } else {
            Write-Host "  [WARN] Could not get capture from Pi" -ForegroundColor Yellow
            $skipPi = $true
        }
    }
} catch {
    Write-Host "  [ERROR] Error connecting to Pi: $_" -ForegroundColor Red
    $skipPi = $true
}

# Step 4: Verify hash on blockchain
if ($processedHash) {
    Write-Host ""
    Write-Host "[4/5] Verifying processed hash on blockchain..." -ForegroundColor Yellow

    try {
        $verifyUrl = "http://localhost:8545/api/v1/blockchain/verify/$processedHash"
        $verifyResponse = Invoke-RestMethod -Uri $verifyUrl -Method Get -TimeoutSec 5

        if ($verifyResponse.verified) {
            Write-Host ""
            Write-Host "  *** IMAGE VERIFIED ON BLOCKCHAIN! ***" -ForegroundColor Green -BackgroundColor DarkGreen
            Write-Host ""
            Write-Host "  Modification Level: $($verifyResponse.modification_level)" -ForegroundColor Green
            Write-Host "  Block Height: $($verifyResponse.block_height)" -ForegroundColor Green
            Write-Host "  Transaction ID: $($verifyResponse.tx_id)" -ForegroundColor Green

            if ($verifyResponse.owner_hash) {
                Write-Host "  Owner Hash: $($verifyResponse.owner_hash.Substring(0,16))..." -ForegroundColor Magenta
            }

            if ($verifyResponse.parent_image_hash) {
                Write-Host "  Parent Hash: $($verifyResponse.parent_image_hash.Substring(0,16))..." -ForegroundColor Cyan
            }
        } else {
            Write-Host "  [WARN] Hash NOT verified on blockchain" -ForegroundColor Red
            Write-Host "  The submission may still be pending validation" -ForegroundColor Yellow
        }
    } catch {
        Write-Host "  [ERROR] Error verifying hash: $_" -ForegroundColor Red
    }
} else {
    Write-Host ""
    Write-Host "[4/5] Skipping verification (no hash from Pi)" -ForegroundColor Yellow
    Write-Host "  You can manually verify with:" -ForegroundColor Cyan
    Write-Host '  Invoke-RestMethod -Uri "http://localhost:8545/api/v1/blockchain/verify/YOUR_HASH"' -ForegroundColor Cyan
}

# Step 5: Check verifier
Write-Host ""
Write-Host "[5/5] Checking web verifier..." -ForegroundColor Yellow
try {
    $verifierResponse = Invoke-RestMethod -Uri "http://localhost:8080/health" -Method Get -TimeoutSec 5
    Write-Host "  [OK] Verifier is running at http://localhost:8080" -ForegroundColor Green
} catch {
    Write-Host "  [WARN] Verifier is not running" -ForegroundColor Yellow
}

# Summary
Write-Host ""
Write-Host "======================================================================"
Write-Host "SUMMARY"
Write-Host "======================================================================"

if ($verifyResponse.verified) {
    Write-Host "[SUCCESS] END-TO-END PIPELINE WORKING!" -ForegroundColor Green -BackgroundColor DarkGreen
    Write-Host ""
    Write-Host "Camera -> Submission -> SMA -> Blockchain -> VERIFIED" -ForegroundColor Green
    Write-Host ""
    Write-Host "Next steps:" -ForegroundColor Cyan
    Write-Host "  1. Open web verifier: http://localhost:8080" -ForegroundColor Yellow
    Write-Host "  2. Paste hash to verify: $($processedHash.Substring(0,32))..." -ForegroundColor Yellow
} else {
    Write-Host "[INFO] Check the steps above for details" -ForegroundColor Yellow
}

Write-Host ""
