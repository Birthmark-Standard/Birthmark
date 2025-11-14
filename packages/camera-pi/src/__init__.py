"""
Birthmark Standard - Camera Pi Package

Raspberry Pi camera prototype for Phase 1 hardware validation.

This package implements:
    - Raw Bayer sensor data capture
    - SHA-256 hashing of sensor data
    - TPM-based secure element integration
    - Authentication bundle submission to aggregator

Modules:
    sensor_capture: Capture raw Bayer data from Raspberry Pi HQ Camera
    hash_pipeline: Compute SHA-256 hash of sensor data
    tpm_interface: Interface with LetsTrust TPM module
    submission: Submit authentication bundles to aggregator

Performance targets:
    - Capture + hash: <650ms
    - User latency: 0ms (parallel processing)
    - Sustained rate: 1 photo/second

Example:
    >>> from sensor_capture import capture_raw_bayer
    >>> from hash_pipeline import hash_sensor_data
    >>> from submission import submit_to_aggregator
    >>>
    >>> bayer_data = capture_raw_bayer()
    >>> image_hash = hash_sensor_data(bayer_data)
    >>> receipt = submit_to_aggregator(image_hash, ...)
"""

__version__ = "0.1.0"
__author__ = "The Birthmark Standard Foundation"
