# SMA Key Tables Data Directory

This directory contains generated key tables for the SMA.

**WARNING**: Key table files are ignored by git because they contain sensitive cryptographic material.

Generate key tables with:
- Phase 1: `python3 src/key_tables/generate.py`
- Phase 2: `python3 src/key_tables/generate.py --phase2`

The generated JSON files should be stored securely and never committed to version control.

