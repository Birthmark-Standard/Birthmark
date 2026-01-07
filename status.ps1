# Birthmark Status Dashboard
# Quick overview of all system components

param(
    [switch]$Detailed
)

function Write-StatusLine {
    param($Label, $Status, $Details = "")

    $labelWidth = 30
    $statusWidth = 15

    Write-Host "  " -NoNewline
    Write-Host $Label.PadRight($labelWidth) -NoNewline -ForegroundColor Cyan

    if ($Status -eq "OK") {
        Write-Host "✓ RUNNING".PadRight($statusWidth) -NoNewline -ForegroundColor Green
    } elseif ($Status -eq "WARN") {
        Write-Host "⚠ WARNING".PadRight($statusWidth) -NoNewline -ForegroundColor Yellow
    } else {
        Write-Host "✗ OFFLINE".PadRight($statusWidth) -NoNewline -ForegroundColor Red
    }

    if ($Details) {
        Write-Host " $Details" -ForegroundColor Gray
    } else {
        Write-Host ""
    }
}

Clear-Host
Write-Host ""
Write-Host "╔════════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║" -NoNewline -ForegroundColor Cyan
Write-Host "        BIRTHMARK STANDARD - PHASE 1 STATUS DASHBOARD        " -NoNewline -ForegroundColor White
Write-Host "║" -ForegroundColor Cyan
Write-Host "╚════════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

# Docker Services
Write-Host "Docker Services" -ForegroundColor Yellow -BackgroundColor DarkGray
Write-Host ""

try {
    $dockerRunning = docker ps --format "{{.Names}}" 2>$null

    if ($dockerRunning -match "birthmark-node") {
        Write-StatusLine "Blockchain Node" "OK" "Port 8545"
    } else {
        Write-StatusLine "Blockchain Node" "ERROR" "Container not running"
    }

    if ($dockerRunning -match "birthmark-postgres") {
        Write-StatusLine "PostgreSQL Database" "OK" "Port 5432"
    } else {
        Write-StatusLine "PostgreSQL Database" "ERROR" "Container not running"
    }
} catch {
    Write-StatusLine "Docker" "ERROR" "Docker not running"
}

Write-Host ""

# External Services
Write-Host "External Services" -ForegroundColor Yellow -BackgroundColor DarkGray
Write-Host ""

# Check SMA
try {
    $smaHealth = Invoke-RestMethod -Uri "http://localhost:8001/health" -Method Get -TimeoutSec 2 -ErrorAction Stop
    Write-StatusLine "SMA Server" "OK" "Port 8001"
} catch {
    Write-StatusLine "SMA Server" "ERROR" "Port 8001 not responding"
}

# Check Verifier
try {
    $verifierHealth = Invoke-RestMethod -Uri "http://localhost:8080/health" -Method Get -TimeoutSec 2 -ErrorAction Stop
    Write-StatusLine "Web Verifier" "OK" "Port 8080"
} catch {
    Write-StatusLine "Web Verifier" "ERROR" "Port 8080 not responding"
}

Write-Host ""

# Blockchain Status
Write-Host "Blockchain Status" -ForegroundColor Yellow -BackgroundColor DarkGray
Write-Host ""

try {
    $chainStatus = Invoke-RestMethod -Uri "http://localhost:8545/api/v1/blockchain/status" -Method Get -TimeoutSec 3 -ErrorAction Stop

    Write-StatusLine "Blockchain Height" "OK" "$($chainStatus.height) blocks"
    Write-StatusLine "Total Transactions" "OK" "$($chainStatus.transaction_count)"
    Write-StatusLine "Total Submissions" "OK" "$($chainStatus.submission_count)"

    if ($chainStatus.pending_validations -gt 0) {
        Write-StatusLine "Pending Validations" "WARN" "$($chainStatus.pending_validations)"
    } else {
        Write-StatusLine "Pending Validations" "OK" "0"
    }
} catch {
    Write-StatusLine "Blockchain API" "ERROR" "Cannot query status"
}

Write-Host ""

# Camera (Raspberry Pi)
Write-Host "Camera Hardware" -ForegroundColor Yellow -BackgroundColor DarkGray
Write-Host ""

$piHost = "birthmark@192.168.50.161"
$sshCmd = if (Get-Command plink -ErrorAction SilentlyContinue) { "plink -batch" } else { "ssh" }

try {
    $pingResult = Test-Connection -ComputerName "192.168.50.161" -Count 1 -Quiet -TimeoutSeconds 2

    if ($pingResult) {
        Write-StatusLine "Raspberry Pi" "OK" "$piHost"

        # Check captures
        try {
            $captureCount = & $sshCmd $piHost "ls ~/Birthmark/packages/camera-pi/data/captures/IMG_*.json 2>/dev/null | wc -l" 2>$null

            if ($captureCount -gt 0) {
                Write-StatusLine "Captures" "OK" "$captureCount images"
            } else {
                Write-StatusLine "Captures" "WARN" "No captures found"
            }

            # Get latest capture time
            $latestFile = & $sshCmd $piHost "ls -t ~/Birthmark/packages/camera-pi/data/captures/IMG_*.json 2>/dev/null | head -1" 2>$null
            if ($latestFile) {
                $latestTime = & $sshCmd $piHost "stat -c %y '$latestFile' 2>/dev/null" 2>$null
                Write-StatusLine "Latest Capture" "OK" "$latestTime"
            }
        } catch {
            Write-StatusLine "Captures" "WARN" "Could not check captures"
        }
    } else {
        Write-StatusLine "Raspberry Pi" "ERROR" "Cannot reach $piHost"
    }
} catch {
    Write-StatusLine "Raspberry Pi" "ERROR" "Network error"
}

Write-Host ""

# Summary
Write-Host "Quick Actions" -ForegroundColor Yellow -BackgroundColor DarkGray
Write-Host ""
Write-Host "  Verify latest submission:  " -NoNewline -ForegroundColor Cyan
Write-Host ".\verify_submission.ps1" -ForegroundColor White
Write-Host "  Check images on Pi:        " -NoNewline -ForegroundColor Cyan
Write-Host ".\check_pi_images.ps1" -ForegroundColor White
Write-Host "  Open web verifier:         " -NoNewline -ForegroundColor Cyan
Write-Host "http://localhost:8080" -ForegroundColor White
Write-Host "  View blockchain explorer:  " -NoNewline -ForegroundColor Cyan
Write-Host "http://localhost:8545/api/v1/blockchain/status" -ForegroundColor White
Write-Host ""

if ($Detailed) {
    Write-Host ""
    Write-Host "Detailed Information" -ForegroundColor Yellow -BackgroundColor DarkGray
    Write-Host ""

    if ($chainStatus) {
        Write-Host "Blockchain Details:" -ForegroundColor Cyan
        Write-Host ($chainStatus | ConvertTo-Json -Depth 3)
        Write-Host ""
    }

    if ($verifierHealth) {
        Write-Host "Verifier Health:" -ForegroundColor Cyan
        Write-Host ($verifierHealth | ConvertTo-Json -Depth 3)
        Write-Host ""
    }
}

Write-Host "Run with -Detailed flag for more information" -ForegroundColor Gray
Write-Host ""
