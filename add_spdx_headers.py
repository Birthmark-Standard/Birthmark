#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2024-2026 The Birthmark Standard Foundation

"""
Script to add SPDX license identifiers to all Python source files.
"""

import os
from pathlib import Path
from typing import Dict, List, Tuple

# License mapping based on directory
LICENSE_MAP = {
    'packages/blockchain/': 'AGPL-3.0-or-later',
    'packages/registry/': 'AGPL-3.0-or-later',
    'packages/camera-pi/': 'Apache-2.0',
    'packages/sma/': 'Apache-2.0',
    'packages/verifier/': 'Apache-2.0',
    'shared/': 'Apache-2.0',
    'scripts/': 'Apache-2.0',
    '': 'Apache-2.0',  # Root directory
}

COPYRIGHT_LINE = "# Copyright (C) 2024-2026 The Birthmark Standard Foundation"


def get_license_for_file(file_path: Path, repo_root: Path) -> str:
    """Determine which license applies to a file based on its path."""
    relative_path = file_path.relative_to(repo_root)
    path_str = str(relative_path)

    # Check each license mapping
    for prefix, license_id in LICENSE_MAP.items():
        if prefix == '':
            # Root directory - only match files directly in root
            if '/' not in path_str:
                return license_id
        elif path_str.startswith(prefix):
            return license_id

    # Default to Apache-2.0
    return 'Apache-2.0'


def has_spdx_identifier(content: str) -> bool:
    """Check if file already has SPDX identifier."""
    lines = content.split('\n')
    # Check first 5 lines for SPDX
    for line in lines[:5]:
        if 'SPDX-License-Identifier:' in line:
            return True
    return False


def add_spdx_header(content: str, license_id: str) -> str:
    """Add SPDX header to file content."""
    lines = content.split('\n')

    spdx_line = f"# SPDX-License-Identifier: {license_id}"
    header_lines = [spdx_line, COPYRIGHT_LINE]

    # Check if file starts with shebang
    if lines and lines[0].startswith('#!'):
        # Insert after shebang
        new_lines = [lines[0]] + header_lines + [''] + lines[1:]
    else:
        # Insert at beginning
        new_lines = header_lines + [''] + lines

    return '\n'.join(new_lines)


def process_file(file_path: Path, repo_root: Path, dry_run: bool = False) -> Tuple[bool, str]:
    """
    Process a single Python file.

    Returns:
        (modified: bool, license_id: str)
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return False, "error"

    # Check if already has SPDX
    if has_spdx_identifier(content):
        license_id = get_license_for_file(file_path, repo_root)
        return False, license_id

    # Determine license
    license_id = get_license_for_file(file_path, repo_root)

    # Add header
    new_content = add_spdx_header(content, license_id)

    if not dry_run:
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
        except Exception as e:
            print(f"Error writing {file_path}: {e}")
            return False, "error"

    return True, license_id


def main():
    repo_root = Path('/home/user/Birthmark')

    # Find all Python files
    python_files = list(repo_root.rglob('*.py'))

    # Exclude venv, .git, etc.
    python_files = [
        f for f in python_files
        if not any(part.startswith('.') or part in ['venv', 'env', '__pycache__', 'node_modules']
                   for part in f.parts)
    ]

    # Statistics
    stats: Dict[str, Dict[str, int]] = {
        'AGPL-3.0-or-later': {'modified': 0, 'skipped': 0},
        'Apache-2.0': {'modified': 0, 'skipped': 0},
    }

    modified_files: List[Path] = []

    print(f"Processing {len(python_files)} Python files...")
    print()

    for file_path in sorted(python_files):
        modified, license_id = process_file(file_path, repo_root, dry_run=False)

        if license_id == "error":
            continue

        if modified:
            stats[license_id]['modified'] += 1
            modified_files.append(file_path)
            relative_path = file_path.relative_to(repo_root)
            print(f"✓ Added {license_id}: {relative_path}")
        else:
            stats[license_id]['skipped'] += 1

    # Print summary
    print()
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print()

    for license_id in ['AGPL-3.0-or-later', 'Apache-2.0']:
        modified = stats[license_id]['modified']
        skipped = stats[license_id]['skipped']
        total = modified + skipped
        print(f"{license_id}:")
        print(f"  Modified: {modified}")
        print(f"  Already had SPDX: {skipped}")
        print(f"  Total: {total}")
        print()

    total_modified = sum(s['modified'] for s in stats.values())
    total_files = len(python_files)

    print(f"Total files processed: {total_files}")
    print(f"Total files modified: {total_modified}")
    print(f"Total files skipped: {total_files - total_modified}")


if __name__ == '__main__':
    main()
