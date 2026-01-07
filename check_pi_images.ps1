# Check for image files on Raspberry Pi
# The camera may have saved JPG/PNG files alongside the JSON metadata

Write-Host "`nChecking for image files on Raspberry Pi..." -ForegroundColor Cyan
Write-Host "=" * 60

$piHost = "birthmark@192.168.50.161"
$captureDir = "~/Birthmark/packages/camera-pi/data/captures"

# Check if plink or ssh is available
$sshCmd = if (Get-Command plink -ErrorAction SilentlyContinue) { "plink -batch" } else { "ssh" }

Write-Host "`nLooking for image files (JPG, PNG, DNG)..." -ForegroundColor Yellow

# Check for different image file types
$imageTypes = @("*.jpg", "*.jpeg", "*.png", "*.dng", "*.raw")

foreach ($type in $imageTypes) {
    Write-Host "`nSearching for $type files..." -ForegroundColor Gray
    try {
        $files = & $sshCmd $piHost "find $captureDir -name '$type' -type f 2>/dev/null"

        if ($files) {
            Write-Host "  ✓ Found $type files:" -ForegroundColor Green
            $files -split "`n" | ForEach-Object {
                if ($_) {
                    # Get file size
                    $fileInfo = & $sshCmd $piHost "ls -lh '$_' 2>/dev/null"
                    Write-Host "    - $_" -ForegroundColor Cyan
                    Write-Host "      $fileInfo" -ForegroundColor Gray
                }
            }
        }
    } catch {
        Write-Host "  (No $type files found)" -ForegroundColor Gray
    }
}

# Check what files DO exist
Write-Host "`n" -NoNewline
Write-Host "All files in captures directory:" -ForegroundColor Yellow
try {
    $allFiles = & $sshCmd $piHost "ls -lh $captureDir/ 2>/dev/null"
    Write-Host $allFiles -ForegroundColor Gray
} catch {
    Write-Host "  Could not list directory" -ForegroundColor Red
}

Write-Host "`n" -NoNewline
Write-Host "=" * 60
Write-Host "`nNOTE:" -ForegroundColor Yellow
Write-Host "If no image files found, the camera may be saving only metadata." -ForegroundColor White
Write-Host "You can still verify by hash using the JSON files." -ForegroundColor White
Write-Host "`nTo enable image saving, check the camera capture configuration." -ForegroundColor Cyan
Write-Host ""
