# Birthmark Camera - Raspberry Pi Installer

Complete installation package for deploying the Birthmark camera authentication system on a Raspberry Pi.

## Hardware Requirements

| Component | Specification | Approx. Cost |
|-----------|--------------|--------------|
| Raspberry Pi 4 | 4GB RAM (or Pi 5) | $55-75 |
| Raspberry Pi HQ Camera | Sony IMX477, 12.3MP | $50 |
| C/CS-Mount Lens | 6mm or 16mm | $25-50 |
| MicroSD Card | 64GB, A2 rated | $15 |
| Power Supply | Official 5V/3A USB-C | $10 |
| **Total** | | **$155-200** |

### Optional Components

- **LetsTrust TPM** (SLB 9670) - $20 - Hardware security module (Phase 2)
- **GPS Module** (Neo-6M) - $15 - Location tagging
- **RTC Module** (DS3231) - $5 - Accurate timestamps offline
- **Case** - $10-30 - Protection

## Quick Start

### 1. Prepare Your SD Card

Download and flash Raspberry Pi OS (64-bit recommended):
- Use [Raspberry Pi Imager](https://www.raspberrypi.com/software/)
- Select "Raspberry Pi OS (64-bit)"
- Enable SSH and configure WiFi in imager settings

### 2. Connect Camera Hardware

1. Power off the Pi
2. Connect HQ Camera to CSI port (ribbon cable, contacts toward HDMI)
3. Attach lens to camera
4. Power on and verify camera detected:
   ```bash
   libcamera-hello --list-cameras
   ```

### 3. Install Birthmark

SSH into your Pi and run:

```bash
# Clone repository (or copy installer directory)
git clone https://github.com/Birthmark-Standard/Birthmark.git
cd Birthmark/packages/camera-pi/installer

# Run setup script (takes 5-10 minutes)
chmod +x setup_pi.sh
sudo ./setup_pi.sh
```

### 4. Get Provisioning Data

On your SMA server, provision a device for this Pi:

```bash
# On SMA server
cd packages/sma
python scripts/provision_device.py --serial PI-001 --family "Raspberry Pi"
```

Copy the provisioning file to your Pi:

```bash
# From SMA server
scp provisioned_devices/provisioning_PI-001.json pi@raspberrypi:/tmp/
```

### 5. Install Provisioning

On the Pi:

```bash
cd ~/birthmark/installer
chmod +x install_provisioning.sh
./install_provisioning.sh /tmp/provisioning_PI-001.json
```

### 6. Configure Server URLs

```bash
cd ~/birthmark/data
cp config.json.template config.json
nano config.json
```

Set your aggregator server URL:
```json
{
    "aggregator_url": "http://your-server:8545",
    "sma_url": "http://your-server:8001",
    ...
}
```

### 7. Test Installation

```bash
source ~/birthmark/activate.sh
python installer/test_installation.py --full
```

### 8. Take Your First Photo

```bash
python -m camera_pi.main capture
```

## Directory Structure

After installation:

```
/home/pi/birthmark/
├── venv/                  # Python virtual environment
├── camera-pi/             # Birthmark camera package
├── data/
│   ├── provisioning.json  # Device credentials (sensitive!)
│   └── config.json        # Server configuration
├── logs/                  # Application logs
├── captures/              # Saved images (if enabled)
├── activate.sh            # Environment activation script
└── installer/             # Installation scripts
```

## Files in This Package

| File | Description |
|------|-------------|
| `setup_pi.sh` | Main system setup script (run with sudo) |
| `install_provisioning.sh` | Install provisioning data from SMA |
| `install_service.sh` | Install systemd auto-start service |
| `test_installation.py` | Verify installation is working |
| `birthmark-camera.service` | Systemd service definition |

## Running as a Service

To run Birthmark automatically on boot:

```bash
sudo ./install_service.sh
```

Service commands:
```bash
sudo systemctl start birthmark-camera    # Start now
sudo systemctl stop birthmark-camera     # Stop
sudo systemctl status birthmark-camera   # Check status
sudo systemctl disable birthmark-camera  # Disable auto-start
journalctl -u birthmark-camera -f        # View logs
```

## Manual Operation

### Activate Environment
```bash
source ~/birthmark/activate.sh
```

### Single Capture
```bash
python -m camera_pi.main capture
```

### Timelapse Mode
```bash
# Capture every 60 seconds
python -m camera_pi.main timelapse --interval 60

# Capture 100 photos, 30 seconds apart
python -m camera_pi.main timelapse --interval 30 --count 100
```

### Test Connection to Server
```bash
python -m camera_pi.main test-connection
```

### Show Device Info
```bash
python -m camera_pi.main info
```

## Troubleshooting

### Camera Not Detected

```bash
# Check camera connection
libcamera-hello --list-cameras

# If "No cameras available", check:
# 1. Ribbon cable seated correctly (contacts toward HDMI)
# 2. Camera enabled in raspi-config
sudo raspi-config
# Interface Options > Camera > Enable
```

### Import Errors

```bash
# Ensure virtual environment is active
source ~/birthmark/activate.sh

# Reinstall package
pip install -e ~/birthmark/camera-pi
```

### Provisioning Not Found

```bash
# Check file exists
ls -la ~/birthmark/data/provisioning.json

# Verify permissions (should be 600)
stat ~/birthmark/data/provisioning.json

# Re-run provisioning installation
./install_provisioning.sh /path/to/provisioning.json
```

### Server Connection Failed

```bash
# Check network connectivity
ping your-server-ip

# Test aggregator endpoint
curl http://your-server:8545/health

# Check config file
cat ~/birthmark/data/config.json
```

### Service Won't Start

```bash
# Check service status
sudo systemctl status birthmark-camera

# View detailed logs
journalctl -u birthmark-camera -n 50

# Check for missing dependencies
source ~/birthmark/activate.sh
python installer/test_installation.py
```

## Security Notes

1. **Provisioning file contains private keys** - Never share or commit
2. **File permissions** - Provisioning should be mode 600
3. **Network security** - Use HTTPS in production
4. **Physical security** - Secure the Pi if in public location

## Performance Targets

| Metric | Target | Typical |
|--------|--------|---------|
| Raw capture | <300ms | 250ms |
| Hash computation | <150ms | 100ms |
| ISP validation | <200ms | 150ms |
| **Total user latency** | <700ms | 500ms |

## Support

- Documentation: `docs/phase-plans/Birthmark_Phase_1_Plan_Simulated_Camera.md`
- Issues: https://github.com/Birthmark-Standard/Birthmark/issues
- Architecture: `docs/specs/Birthmark_Camera_Security_Architecture.md`

## License

Open source (license TBD) - The Birthmark Standard Foundation
