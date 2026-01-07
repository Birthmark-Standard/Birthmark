# PowerShell script to get the latest image hash from Raspberry Pi
# Usage: .\get_pi_hash.ps1

$piHost = "birthmark@192.168.50.161"
$captureDir = "~/Birthmark/packages/camera-pi/data/captures"

Write-Host "Fetching latest capture from Raspberry Pi..." -ForegroundColor Cyan

# Get the latest JSON file
$latestFile = plink -batch $piHost "ls -t $captureDir/IMG_*.json | head -1"

if ($LASTEXITCODE -eq 0) {
    Write-Host "Latest capture: $latestFile" -ForegroundColor Green

    # Get the processed hash from the file
    $captureData = plink -batch $piHost "cat $latestFile"

    # Parse the JSON (Windows PowerShell compatible)
    $capture = $captureData | ConvertFrom-Json

    Write-Host "`n=== Capture Information ===" -ForegroundColor Yellow
    Write-Host "Submission ID: $($capture.submission_id)"
    Write-Host "Timestamp: $($capture.timestamp)"
    Write-Host "Raw Hash: $($capture.raw_hash)"
    Write-Host "Processed Hash: $($capture.processed_hash)"

    if ($capture.owner_hash) {
        Write-Host "Owner: $($capture.owner_name)"
        Write-Host "Owner Hash: $($capture.owner_hash)"
    }

    Write-Host "`n=== Verification ===" -ForegroundColor Yellow
    Write-Host "Verifying processed hash on blockchain..." -ForegroundColor Cyan

    # Verify the hash
    python /home/user/Birthmark/verify_hash.py $capture.processed_hash

} else {
    Write-Host "Error: Could not connect to Raspberry Pi" -ForegroundColor Red
    Write-Host "Make sure plink is installed and the Pi is accessible at $piHost" -ForegroundColor Yellow
}
