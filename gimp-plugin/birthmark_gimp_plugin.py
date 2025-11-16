#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Birthmark GIMP Plugin - Manual Modification Level Tracker
Proof of Concept for Phase 3 Partnership Demonstrations

Place this file in GIMP's plug-ins directory:
  Windows: %APPDATA%\GIMP\2.10\plug-ins\
  Linux: ~/.config/GIMP/2.10/plug-ins/

Make executable on Linux: chmod +x birthmark_gimp_plugin.py

Requirements:
- GIMP 2.10 with Python-Fu support
- Birthmark aggregation server running (or accessible)
- SSA validation server running (or accessible)
- Software certificate in ~/.birthmark/ directory
"""

from gimpfu import *
import gimp
import json
import hashlib
import os
from datetime import datetime

# Plugin version - must match SSA valid versions
PLUGIN_VERSION = "1.0.0"

# Configuration
AGGREGATION_SERVER_URL = "http://localhost:8000"
SSA_SERVER_URL = "http://localhost:8001"
CERT_DIR = os.path.expanduser("~/.birthmark")
CERT_PATH = os.path.join(CERT_DIR, "software_certificate.pem")
KEY_PATH = os.path.join(CERT_DIR, "software_private_key.pem")

# Parasite name for tracking data
PARASITE_TRACKING = "birthmark-tracking"


def compute_file_hash(filepath):
    """Compute SHA-256 hash of file"""
    hasher = hashlib.sha256()
    try:
        with open(filepath, "rb") as f:
            while True:
                chunk = f.read(8192)
                if not chunk:
                    break
                hasher.update(chunk)
        return hasher.hexdigest()
    except Exception as e:
        gimp.message("Error computing file hash: {}".format(str(e)))
        return None


def compute_image_hash(image):
    """Compute hash of image pixel data"""
    # This is simplified - production would be more sophisticated
    # We hash the flattened pixel data from all layers
    hasher = hashlib.sha256()
    try:
        for layer in image.layers:
            region = layer.get_pixel_rgn(0, 0, layer.width, layer.height, False, False)
            # Get pixel data as string and hash it
            pixel_data = region[0:layer.width, 0:layer.height]
            hasher.update(str(pixel_data))
        return hasher.hexdigest()
    except Exception as e:
        gimp.message("Error computing image hash: {}".format(str(e)))
        return None


def check_authentication(image_hash):
    """Query aggregation server for image authentication"""
    try:
        import urllib2
        url = "{}/api/v1/verify/{}".format(AGGREGATION_SERVER_URL, image_hash)
        response = urllib2.urlopen(url, timeout=10)
        data = json.loads(response.read())
        return data.get("verified", False) or data.get("authenticated", False)
    except Exception as e:
        gimp.message("Authentication check failed: {}\n\nMake sure the aggregation server is running at {}".format(
            str(e), AGGREGATION_SERVER_URL))
        return False


def validate_software():
    """Validate this plugin installation against SSA"""
    try:
        import urllib2

        # Compute baseline hash of this plugin file (without version string)
        plugin_path = os.path.realpath(__file__)
        # Remove .pyc if it's the compiled version
        if plugin_path.endswith('.pyc'):
            plugin_path = plugin_path[:-1]  # Remove 'c' to get .py

        baseline_hash = compute_file_hash(plugin_path)
        if not baseline_hash:
            return None

        # Check if certificate exists
        if not os.path.exists(CERT_PATH):
            gimp.message("ERROR: Certificate not found at {}\n\nPlease provision the plugin with SSA first.".format(CERT_PATH))
            return None

        # Load certificate
        with open(CERT_PATH, "r") as f:
            cert_pem = f.read()

        # Prepare validation request
        request_data = json.dumps({
            "software_certificate": cert_pem,
            "current_wrapper_hash": baseline_hash,
            "version": PLUGIN_VERSION
        })

        req = urllib2.Request(
            "{}/api/v1/validate/software".format(SSA_SERVER_URL),
            data=request_data,
            headers={"Content-Type": "application/json"}
        )

        response = urllib2.urlopen(req, timeout=10)
        data = json.loads(response.read())

        if data.get("validation_result") == "PASS":
            return data.get("software_id", "Unknown")
        else:
            gimp.message("Software validation FAILED: {}\n\nReason: {}".format(
                data.get("validation_result", "Unknown"),
                data.get("reason", "No reason provided")
            ))
            return None

    except Exception as e:
        gimp.message("Software validation failed: {}\n\nMake sure SSA server is running at {}".format(
            str(e), SSA_SERVER_URL))
        return None


def get_tracking_data(image):
    """Retrieve tracking data from image parasite"""
    try:
        parasite = image.parasite_find(PARASITE_TRACKING)
        if parasite:
            return json.loads(parasite.data)
    except Exception as e:
        # Silently fail - no tracking data is okay
        pass
    return None


def set_tracking_data(image, data):
    """Store tracking data in image parasite"""
    json_data = json.dumps(data)
    parasite = gimp.Parasite(
        PARASITE_TRACKING,
        gimp.PARASITE_PERSISTENT,  # Survives save/load in XCF
        json_data
    )
    image.parasite_attach(parasite)


def initialize_tracking(image, drawable):
    """
    Initialize Birthmark tracking for current image.
    Checks authentication and attaches tracking parasite.
    """
    gimp.progress_init("Initializing Birthmark tracking...")

    # Check if already tracking
    existing = get_tracking_data(image)
    if existing:
        gimp.message("Tracking already initialized for this image.\n\nCurrent level: {}".format(
            existing.get("modification_level", 0)))
        return

    # Validate software certificate
    gimp.progress_update(0.2)
    software_id = validate_software()
    if not software_id:
        gimp.message("ERROR: Plugin failed SSA validation.\n\nCannot initialize tracking without valid certificate.")
        return

    # Compute current image hash
    gimp.progress_update(0.4)
    image_hash = compute_image_hash(image)
    if not image_hash:
        gimp.message("ERROR: Failed to compute image hash.")
        return

    # Check if image is authenticated
    gimp.progress_update(0.6)
    if not check_authentication(image_hash):
        gimp.message("Image is NOT authenticated.\n\nTracking will remain dormant.\n\nOnly Birthmark-authenticated images can be tracked.")
        return

    # Initialize tracking data
    gimp.progress_update(0.8)
    tracking_data = {
        "original_hash": image_hash,
        "modification_level": 0,
        "software_id": software_id,
        "initialized_at": datetime.utcnow().isoformat(),
        "original_dimensions": [image.width, image.height]
    }

    set_tracking_data(image, tracking_data)

    gimp.progress_update(1.0)
    gimp.message("Birthmark tracking initialized!\n\nImage authenticated: YES\nCurrent modification level: 0 (unmodified)\n\nUse 'Log Level 1 Operation' or 'Log Level 2 Operation' after making edits.")


def log_level_1_operation(image, drawable):
    """
    Log that a Level 1 (minor) operation was performed.
    Examples: exposure, white balance, crop, rotation
    """
    tracking = get_tracking_data(image)
    if not tracking:
        gimp.message("Tracking not initialized.\n\nRun 'Initialize Tracking' first.")
        return

    current_level = tracking.get("modification_level", 0)

    if current_level == 0:
        tracking["modification_level"] = 1
        set_tracking_data(image, tracking)
        gimp.message("Modification level updated: 0 -> 1\n\nImage now marked as having minor modifications.")
    elif current_level == 1:
        gimp.message("Modification level remains: 1\n\nAlready at Level 1 (minor modifications).")
    else:  # level == 2
        gimp.message("Modification level remains: 2\n\nCannot reduce from Level 2.")


def log_level_2_operation(image, drawable):
    """
    Log that a Level 2 (heavy) operation was performed.
    Examples: clone stamp, content-aware fill, compositing
    """
    tracking = get_tracking_data(image)
    if not tracking:
        gimp.message("Tracking not initialized.\n\nRun 'Initialize Tracking' first.")
        return

    current_level = tracking.get("modification_level", 0)

    if current_level < 2:
        tracking["modification_level"] = 2
        set_tracking_data(image, tracking)
        gimp.message("Modification level updated: {} -> 2\n\nImage now marked as having heavy modifications.".format(current_level))
    else:
        gimp.message("Modification level remains: 2\n\nAlready at Level 2 (heavy modifications).")


def show_tracking_status(image, drawable):
    """Display current tracking status for the image"""
    tracking = get_tracking_data(image)

    if not tracking:
        gimp.message("Birthmark Tracking Status\n==========================\n\nStatus: NOT INITIALIZED\n\nRun 'Initialize Tracking' to begin.")
        return

    level_desc = {
        0: "Unmodified",
        1: "Minor Modifications",
        2: "Heavy Modifications"
    }

    status = ("Birthmark Tracking Status\n"
             "==========================\n\n"
             "Status: ACTIVE\n"
             "Modification Level: {} ({})\n"
             "Software ID: {}\n"
             "Original Hash: {}...\n"
             "Initialized: {}\n"
             "Original Size: {}x{}").format(
                 tracking.get("modification_level", 0),
                 level_desc.get(tracking.get("modification_level", 0), "Unknown"),
                 tracking.get("software_id", "Unknown"),
                 tracking.get("original_hash", "")[:16],
                 tracking.get("initialized_at", "Unknown"),
                 tracking.get("original_dimensions", [0, 0])[0],
                 tracking.get("original_dimensions", [0, 0])[1]
             )

    gimp.message(status)


def export_with_birthmark(image, drawable, filepath):
    """
    Export image with Birthmark modification record.
    Creates sidecar JSON file and submits to aggregation server.
    """
    tracking = get_tracking_data(image)

    if not tracking:
        gimp.message("Tracking not initialized.\n\nCannot export with Birthmark record.")
        return

    # Use default filepath if not provided
    if not filepath or filepath == "":
        # Try to get current filename
        if image.filename:
            filepath = image.filename
        else:
            gimp.message("Please save the image first, then use Export with Record.\n\nOr provide a filepath.")
            return

    gimp.progress_init("Exporting with Birthmark record...")

    # Compute final image hash
    gimp.progress_update(0.3)
    final_hash = compute_image_hash(image)
    if not final_hash:
        gimp.message("ERROR: Failed to compute final image hash.")
        return

    # Create modification record
    gimp.progress_update(0.5)
    modification_record = {
        "original_image_hash": tracking.get("original_hash"),
        "final_image_hash": final_hash,
        "modification_level": tracking.get("modification_level", 0),
        "original_dimensions": tracking.get("original_dimensions"),
        "final_dimensions": [image.width, image.height],
        "software_id": tracking.get("software_id"),
        "timestamp": datetime.utcnow().isoformat(),
        "authority_type": "software",
        "plugin_version": PLUGIN_VERSION
    }

    # Save sidecar file
    gimp.progress_update(0.7)
    sidecar_path = filepath + ".birthmark.json"
    try:
        with open(sidecar_path, "w") as f:
            json.dump(modification_record, f, indent=2)
    except Exception as e:
        gimp.message("ERROR: Failed to save sidecar file: {}".format(str(e)))
        return

    # Submit to aggregation server
    gimp.progress_update(0.9)
    try:
        import urllib2
        request_data = json.dumps(modification_record)
        req = urllib2.Request(
            "{}/api/v1/modifications".format(AGGREGATION_SERVER_URL),
            data=request_data,
            headers={"Content-Type": "application/json"}
        )
        response = urllib2.urlopen(req, timeout=10)
        server_response = json.loads(response.read())

        gimp.progress_update(1.0)
        gimp.message("Birthmark Export Complete!\n"
                    "==========================\n\n"
                    "Modification Level: {}\n"
                    "Sidecar File: {}\n"
                    "Server Status: {}\n"
                    "Chain ID: {}".format(
                        modification_record["modification_level"],
                        sidecar_path,
                        server_response.get("status", "unknown"),
                        server_response.get("chain_id", "N/A")
                    ))
    except Exception as e:
        gimp.progress_update(1.0)
        gimp.message("Birthmark Export Complete (Offline)\n"
                    "====================================\n\n"
                    "Modification Level: {}\n"
                    "Sidecar File: {}\n\n"
                    "WARNING: Could not submit to server: {}\n\n"
                    "Record saved locally only.".format(
                        modification_record["modification_level"],
                        sidecar_path,
                        str(e)
                    ))


# Register plugin procedures with GIMP
register(
    "birthmark_initialize_tracking",
    "Initialize Birthmark modification tracking for authenticated image",
    "Checks if image is Birthmark-authenticated and begins tracking modifications",
    "Birthmark Standard Foundation",
    "Birthmark Standard Foundation",
    "2025",
    "<Image>/Birthmark/Initialize Tracking",
    "*",
    [],
    [],
    initialize_tracking
)

register(
    "birthmark_log_level_1",
    "Log Level 1 (minor) modification",
    "Mark that a minor edit was performed (exposure, crop, rotation, etc.)",
    "Birthmark Standard Foundation",
    "Birthmark Standard Foundation",
    "2025",
    "<Image>/Birthmark/Log Level 1 Operation",
    "*",
    [],
    [],
    log_level_1_operation
)

register(
    "birthmark_log_level_2",
    "Log Level 2 (heavy) modification",
    "Mark that a heavy edit was performed (clone, composite, content-aware, etc.)",
    "Birthmark Standard Foundation",
    "Birthmark Standard Foundation",
    "2025",
    "<Image>/Birthmark/Log Level 2 Operation",
    "*",
    [],
    [],
    log_level_2_operation
)

register(
    "birthmark_status",
    "Show Birthmark tracking status",
    "Display current modification tracking status for the image",
    "Birthmark Standard Foundation",
    "Birthmark Standard Foundation",
    "2025",
    "<Image>/Birthmark/Show Status",
    "*",
    [],
    [],
    show_tracking_status
)

register(
    "birthmark_export",
    "Export image with Birthmark modification record",
    "Save modification record to sidecar file and submit to aggregation server",
    "Birthmark Standard Foundation",
    "Birthmark Standard Foundation",
    "2025",
    "<Image>/Birthmark/Export with Record",
    "*",
    [
        (PF_STRING, "filepath", "Export filepath (optional, uses current file if blank)", "")
    ],
    [],
    export_with_birthmark
)

main()
