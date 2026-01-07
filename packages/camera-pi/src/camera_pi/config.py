# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2024-2026 The Birthmark Standard Foundation

"""
Camera configuration management for Birthmark Protocol.

Handles user settings including owner attribution preferences.
"""

import json
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional


@dataclass
class OwnerAttributionConfig:
    """Owner attribution settings."""
    enabled: bool = False
    owner_name: str = ""

    def is_configured(self) -> bool:
        """Check if owner attribution is properly configured."""
        return self.enabled and len(self.owner_name.strip()) > 0


@dataclass
class CameraConfig:
    """Camera configuration settings."""
    owner_attribution: OwnerAttributionConfig

    @classmethod
    def load(cls, config_path: Optional[Path] = None) -> 'CameraConfig':
        """
        Load configuration from file.

        Args:
            config_path: Path to config file (default: ./data/camera_config.json)

        Returns:
            CameraConfig instance with loaded settings
        """
        if config_path is None:
            config_path = Path("./data/camera_config.json")

        if not config_path.exists():
            # Return default configuration
            return cls(owner_attribution=OwnerAttributionConfig())

        try:
            with open(config_path, 'r') as f:
                data = json.load(f)

            owner_attr_data = data.get('owner_attribution', {})
            owner_attribution = OwnerAttributionConfig(
                enabled=owner_attr_data.get('enabled', False),
                owner_name=owner_attr_data.get('owner_name', '')
            )

            return cls(owner_attribution=owner_attribution)

        except Exception as e:
            print(f"⚠ Error loading config: {e}")
            print("  Using default configuration")
            return cls(owner_attribution=OwnerAttributionConfig())

    def save(self, config_path: Optional[Path] = None) -> None:
        """
        Save configuration to file.

        Args:
            config_path: Path to config file (default: ./data/camera_config.json)
        """
        if config_path is None:
            config_path = Path("./data/camera_config.json")

        # Ensure directory exists
        config_path.parent.mkdir(parents=True, exist_ok=True)

        # Convert to dict
        data = {
            'owner_attribution': asdict(self.owner_attribution)
        }

        # Write to file
        with open(config_path, 'w') as f:
            json.dump(data, f, indent=2)

    def print_summary(self) -> None:
        """Print configuration summary."""
        print("Camera Configuration:")
        print(f"  Owner Attribution: {'✓ Enabled' if self.owner_attribution.enabled else '✗ Disabled'}")
        if self.owner_attribution.enabled:
            print(f"  Owner Name: {self.owner_attribution.owner_name}")


def configure_owner_attribution(config_path: Optional[Path] = None) -> None:
    """
    Interactive configuration for owner attribution.

    Args:
        config_path: Path to config file (default: ./data/camera_config.json)
    """
    print("=== Owner Attribution Configuration ===\n")
    print("Owner attribution allows you to include verifiable attribution")
    print("in your photos using a hash-based system.")
    print()
    print("⚠ PRIVACY NOTE:")
    print("  - Owner name and random salt are stored in image EXIF")
    print("  - Only a hash of (name + salt) is stored on blockchain")
    print("  - Each photo gets a unique hash (even from same owner)")
    print("  - Blockchain records cannot be correlated without the image file")
    print()

    # Load existing config
    config = CameraConfig.load(config_path)

    # Ask if user wants to enable
    response = input("Enable owner attribution? (y/n): ").strip().lower()

    if response == 'y':
        config.owner_attribution.enabled = True

        # Get owner name
        print()
        print("Enter owner name/identifier. This can be:")
        print("  - Your name (e.g., 'Jane Smith')")
        print("  - Email (e.g., 'jane@example.com')")
        print("  - Organization + name (e.g., 'Jane Smith - Reuters')")
        print()

        owner_name = input("Owner name: ").strip()

        if not owner_name:
            print("❌ Owner name cannot be empty")
            return

        config.owner_attribution.owner_name = owner_name

        # Save configuration
        config.save(config_path)

        print()
        print("✓ Owner attribution enabled")
        print(f"  Owner name: {owner_name}")
        print()
        print("All future photos will include owner attribution.")
        print("You can change this anytime by running this configuration again.")

    else:
        config.owner_attribution.enabled = False
        config.owner_attribution.owner_name = ""
        config.save(config_path)

        print()
        print("✓ Owner attribution disabled")
        print("Photos will not include owner attribution.")


if __name__ == "__main__":
    # Interactive configuration
    configure_owner_attribution()
