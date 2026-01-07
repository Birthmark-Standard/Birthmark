# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2024-2026 The Birthmark Standard Foundation

"""
Main entry point for running camera_pi as a module.

Allows running:
    python -m camera_pi capture --use-certificates --mock
"""

from .main import main

if __name__ == "__main__":
    main()
