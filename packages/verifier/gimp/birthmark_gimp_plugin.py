#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Birthmark GIMP Plugin - Manual Modification Level Tracker
Proof of Concept for Phase 3 Partnership Demonstrations

Place this file in GIMP's plug-ins directory:
  Windows: %APPDATA%\GIMP\2.10\plug-ins\
  Linux: ~/.config/GIMP/2.10/plug-ins\
  macOS: ~/Library/Application Support/GIMP/2.10/plug-ins/

Make executable on Linux/macOS: chmod +x birthmark_gimp_plugin.py
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
AGGREGATION_SERVER_URL = os.environ.get("BIRTHMARK_AGG_URL", "http://localhost:8545")
SSA_SERVER_URL = os.environ.get("BIRTHMARK_SSA_URL", "http://localhost:8002")
CERT_PATH = os.path.expanduser("~/.birthmark/software_certificate.pem")
KEY_PATH = os.path.expanduser("~/.birthmark/software_private_key.pem")

# Parasite names
PARASITE_TRACKING = "birthmark-tracking"


def compute_file_hash(filepath):
    """Compute SHA-256 hash of file"""
    hasher = hashlib.sha256()
    with open(filepath, "rb") as f:
        while True:
            chunk = f.read(8192)
            if not chunk:
                break
            hasher.update(chunk)
    return hasher.hexdigest()


def compute_image_hash(image):
    """
    Compute hash of image pixel data

    Note: This is simplified for POC. In production, would use more
    sophisticated hashing that's consistent across saves/loads.
    """
    hasher = hashlib.sha256()

    # Hash image metadata
    hasher.update(str(image.width).encode())
    hasher.update(str(image.height).encode())
    hasher.update(str(len(image.layers)).encode())

    # Hash each layer's pixel data
    for layer in image.layers:
        # Get pixel region
        region = layer.get_pixel_rgn(0, 0, layer.width, layer.height, False, False)
        # Sample pixels (full hash would be too slow for large images)
        # In production: use more efficient hashing method
        pixel_data = region[0:layer.width, 0:layer.height]
        hasher.update(str(pixel_data))

    return hasher.hexdigest()


def check_authentication(image_hash):
    """Query aggregation server for image authentication"""
    try:
        import urllib2
        url = "{}/api/v1/verify/{}".format(AGGREGATION_SERVER_URL, image_hash)
        response = urllib2.urlopen(url, timeout=10)
        data = json.loads(response.read())
        return data.get("verified", False)
    except Exception as e:
        gimp.message("Authentication check failed: {}\n\nMake sure blockchain node is running on {}".format(
            str(e), AGGREGATION_SERVER_URL))
        return False


def validate_software():
    """Validate this plugin installation against SSA"""
    try:
        import urllib2

        # Check if certificates exist
        if not os.path.exists(CERT_PATH):
            gimp.message("ERROR: Software certificate not found at:\n{}\n\n"
                        "Please provision this plugin with SSA first.".format(CERT_PATH))
            return None

        # Compute baseline hash of this plugin file
        plugin_path = os.path.realpath(__file__)
        baseline_hash = compute_file_hash(plugin_path)

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
            gimp.message("ERROR: Plugin validation failed\n\n"
                        "Reason: {}\n\n"
                        "Make sure SSA server is running on {}".format(
                            data.get("reason", "Unknown"), SSA_SERVER_URL))
            return None

    except Exception as e:
        gimp.message("Software validation failed: {}\n\n"
                    "Make sure SSA server is running on {}".format(
                        str(e), SSA_SERVER_URL))
        return None


def get_tracking_data(image):
    """Retrieve tracking data from image parasite"""
    try:
        parasite = image.parasite_find(PARASITE_TRACKING)
        if parasite:
            return json.loads(parasite.data)
    except:
        pass
    return None


def set_tracking_data(image, data):
    """Store tracking data in image parasite"""
    json_data = json.dumps(data)
    parasite = gimp.Parasite(
        PARASITE_TRACKING,
        PARASITE_PERSISTENT,  # Survives save/load in XCF
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
        gimp.message("Tracking already initialized for this image.\n\n"
                    "Current level: {}\n"
                    "Software ID: {}\n"
                    "Initialized: {}".format(
                        existing.get("modification_level", 0),
                        existing.get("software_id", "Unknown"),
                        existing.get("initialized_at", "Unknown")))
        return

    # Validate software certificate
    gimp.progress_update(0.2)
    software_id = validate_software()
    if not software_id:
        return

    # Compute current image hash
    gimp.progress_update(0.4)
    gimp.message("Computing image hash... this may take a moment...")
    image_hash = compute_image_hash(image)

    # Check if image is authenticated
    gimp.progress_update(0.6)
    authenticated = check_authentication(image_hash)

    # Initialize tracking data
    gimp.progress_update(0.8)
    tracking_data = {
        "original_hash": image_hash,
        "modification_level": 0,
        "software_id": software_id,
        "plugin_version": PLUGIN_VERSION,
        "initialized_at": datetime.utcnow().isoformat(),
        "original_dimensions": [image.width, image.height],
        "authenticated": authenticated
    }

    set_tracking_data(image, tracking_data)

    gimp.progress_update(1.0)

    if authenticated:
        gimp.message("Birthmark tracking initialized!\n\n"
                    "Image authenticated: YES\n"
                    "Current modification level: 0 (unmodified)\n\n"
                    "Use 'Log Level 1 Operation' or 'Log Level 2 Operation' "
                    "after making edits.")
    else:
        gimp.message("Tracking initialized (but image NOT authenticated)\n\n"
                    "Image authenticated: NO\n"
                    "Current modification level: 0\n\n"
                    "This image was not found in the Birthmark blockchain.\n"
                    "Tracking will work, but the image is not verified as authentic.")


def log_level_1_operation(image, drawable):
    """
    Log that a Level 1 (minor) operation was performed.

    Examples: exposure, white balance, crop, rotation
    """
    tracking = get_tracking_data(image)
    if not tracking:
        gimp.message("Tracking not initialized.\n\n"
                    "Run 'Birthmark -> Initialize Tracking' first.")
        return

    current_level = tracking.get("modification_level", 0)

    if current_level == 0:
        tracking["modification_level"] = 1
        tracking["level_1_timestamp"] = datetime.utcnow().isoformat()
        set_tracking_data(image, tracking)
        gimp.message("Modification level updated: 0 -> 1\n\n"
                    "Image now marked as having minor modifications.")
    elif current_level == 1:
        gimp.message("Modification level remains: 1\n\n"
                    "Already at Level 1 (minor modifications).")
    else:  # level == 2
        gimp.message("Modification level remains: 2\n\n"
                    "Cannot reduce from Level 2.\n"
                    "(Modification levels only go up, never down)")


def log_level_2_operation(image, drawable):
    """
    Log that a Level 2 (heavy) operation was performed.

    Examples: clone stamp, content-aware fill, compositing
    """
    tracking = get_tracking_data(image)
    if not tracking:
        gimp.message("Tracking not initialized.\n\n"
                    "Run 'Birthmark -> Initialize Tracking' first.")
        return

    current_level = tracking.get("modification_level", 0)

    if current_level < 2:
        tracking["modification_level"] = 2
        tracking["level_2_timestamp"] = datetime.utcnow().isoformat()
        set_tracking_data(image, tracking)
        gimp.message("Modification level updated: {} -> 2\n\n"
                    "Image now marked as having heavy modifications.".format(current_level))
    else:
        gimp.message("Modification level remains: 2\n\n"
                    "Already at Level 2 (heavy modifications).")


def show_tracking_status(image, drawable):
    """Display current tracking status for the image"""
    tracking = get_tracking_data(image)

    if not tracking:
        gimp.message("Birthmark Tracking Status\n"
                    "==========================\n\n"
                    "Status: NOT INITIALIZED\n\n"
                    "Run 'Birthmark -> Initialize Tracking' to begin.")
        return

    level_desc = {
        0: "Unmodified",
        1: "Minor Modifications",
        2: "Heavy Modifications"
    }

    status = ("Birthmark Tracking Status\n"
             "==========================\n\n"
             "Status: ACTIVE\n"
             "Authenticated: {}\n"
             "Modification Level: {} ({})\n"
             "Software ID: {}\n"
             "Plugin Version: {}\n"
             "Original Hash: {}...\n"
             "Initialized: {}\n"
             "Original Size: {}x{}\n").format(
                 "YES" if tracking.get("authenticated", False) else "NO",
                 tracking.get("modification_level", 0),
                 level_desc.get(tracking.get("modification_level", 0), "Unknown"),
                 tracking.get("software_id", "Unknown"),
                 tracking.get("plugin_version", "Unknown"),
                 tracking.get("original_hash", "")[:16],
                 tracking.get("initialized_at", "Unknown"),
                 tracking.get("original_dimensions", [0, 0])[0],
                 tracking.get("original_dimensions", [0, 0])[1]
             )

    gimp.message(status)


def export_with_birthmark(image, drawable):
    """
    Export image with Birthmark modification record.
    Creates sidecar JSON file and attempts to submit to aggregation server.

    Note: This creates the sidecar file next to the current XCF file.
    Make sure to save your XCF first!
    """
    tracking = get_tracking_data(image)

    if not tracking:
        gimp.message("Tracking not initialized.\n\n"
                    "Cannot export with Birthmark record.\n\n"
                    "Run 'Birthmark -> Initialize Tracking' first.")
        return

    # Check if image has been saved
    if not image.filename:
        gimp.message("ERROR: Image has not been saved yet.\n\n"
                    "Please save your image as XCF first, then run this command.\n\n"
                    "The sidecar file will be created next to your XCF file.")
        return

    gimp.progress_init("Exporting with Birthmark record...")

    # Compute final image hash
    gimp.progress_update(0.3)
    final_hash = compute_image_hash(image)

    # Create modification record
    gimp.progress_update(0.5)
    modification_record = {
        "original_image_hash": tracking.get("original_hash"),
        "final_image_hash": final_hash,
        "modification_level": tracking.get("modification_level", 0),
        "authenticated": tracking.get("authenticated", False),
        "original_dimensions": tracking.get("original_dimensions"),
        "final_dimensions": [image.width, image.height],
        "software_id": tracking.get("software_id"),
        "plugin_version": tracking.get("plugin_version"),
        "initialized_at": tracking.get("initialized_at"),
        "exported_at": datetime.utcnow().isoformat(),
        "authority_type": "software"
    }

    # Save sidecar file
    gimp.progress_update(0.7)
    sidecar_path = image.filename + ".birthmark.json"
    with open(sidecar_path, "w") as f:
        json.dump(modification_record, f, indent=2)

    # Attempt to submit to aggregation server (optional - may be offline)
    gimp.progress_update(0.9)
    submission_status = "not attempted"
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
        submission_status = "success"

        gimp.progress_update(1.0)
        gimp.message("Birthmark Export Complete!\n"
                    "==========================\n\n"
                    "Modification Level: {}\n"
                    "Authenticated: {}\n"
                    "Sidecar File: {}\n"
                    "Server Status: {}\n\n"
                    "The modification record has been saved and submitted.".format(
                        modification_record["modification_level"],
                        "YES" if modification_record["authenticated"] else "NO",
                        sidecar_path,
                        server_response.get("status", "unknown")))
    except Exception as e:
        gimp.progress_update(1.0)
        gimp.message("Birthmark Export Complete (Offline)\n"
                    "====================================\n\n"
                    "Modification Level: {}\n"
                    "Authenticated: {}\n"
                    "Sidecar File: {}\n\n"
                    "WARNING: Could not submit to server:\n{}\n\n"
                    "Record saved locally. Submit it later when server is online.".format(
                        modification_record["modification_level"],
                        "YES" if modification_record["authenticated"] else "NO",
                        sidecar_path,
                        str(e)))


# Register plugin procedures
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
    "Export with Birthmark modification record",
    "Save modification record to sidecar file and submit to aggregation server",
    "Birthmark Standard Foundation",
    "Birthmark Standard Foundation",
    "2025",
    "<Image>/Birthmark/Export with Record",
    "*",
    [],
    [],
    export_with_birthmark
)

main()
