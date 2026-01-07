# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2024-2026 The Birthmark Standard Foundation

"""
Birthmark Image Verifier

Web application for verifying image authenticity against the Birthmark blockchain.
"""

from .hash_image import hash_image_file, hash_image_bytes, verify_hash_format

__version__ = "1.0.0"
__all__ = ["hash_image_file", "hash_image_bytes", "verify_hash_format"]
