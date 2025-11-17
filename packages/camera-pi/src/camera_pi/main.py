"""
Birthmark Camera - Main CLI Application

Raspberry Pi camera prototype for the Birthmark Protocol.
Demonstrates zero-latency photo authentication with hardware-backed security.
"""

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Optional

from .raw_capture import create_capture_manager, RawCaptureConfig
from .provisioning_client import ProvisioningClient
from .camera_token import create_token_generator_from_provisioning
from .tpm_interface import create_tpm_interface_from_provisioning
from .aggregation_client import (
    create_aggregation_client,
    AuthenticationBundle,
    SubmissionQueue
)
from .crypto.signing import sign_bundle


class BirthmarkCamera:
    """
    Main camera application orchestrating capture and authentication.
    """

    def __init__(
        self,
        provisioning_path: Optional[Path] = None,
        aggregation_url: str = "http://localhost:8545",
        output_dir: Optional[Path] = None,
        use_mock_camera: bool = False,
        use_certificates: bool = False
    ):
        """
        Initialize Birthmark camera.

        Args:
            provisioning_path: Path to provisioning data file
            aggregation_url: Birthmark blockchain node URL
            output_dir: Output directory for images
            use_mock_camera: Use mock camera for testing
            use_certificates: Use certificate-based authentication (new format)
        """
        # Set up output directory
        if output_dir is None:
            output_dir = Path("./data/captures")
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Store mode
        self.use_certificates = use_certificates

        # Load provisioning data
        print("Loading provisioning data...")
        self.provisioning_client = ProvisioningClient(provisioning_path)
        self.provisioning_data = self.provisioning_client.load_from_file()
        print(f"✓ Device: {self.provisioning_data.device_serial}")

        # Initialize components
        print("\nInitializing camera components...")

        self.capture_manager = create_capture_manager(use_mock=use_mock_camera)
        self.capture_manager.initialize()

        # Token generator only needed for legacy format
        if not use_certificates:
            self.token_generator = create_token_generator_from_provisioning(
                self.provisioning_data
            )
        else:
            print("✓ Using certificate-based authentication (token generator not needed)")
            self.token_generator = None

        self.tpm = create_tpm_interface_from_provisioning(
            self.provisioning_data
        )

        self.aggregation_client = create_aggregation_client(aggregation_url)

        # Initialize submission queue (pass private key for certificate signing)
        self.submission_queue = SubmissionQueue(
            self.aggregation_client,
            device_private_key=self.tpm._private_key
        )
        self.submission_queue.start_worker()

        # Statistics
        self.capture_count = 0

        print("✓ Camera initialized\n")

    def capture_photo(self, save_image: bool = True) -> dict:
        """
        Capture authenticated photo.

        Workflow (Certificate mode):
        1. Capture raw Bayer data
        2. Hash raw data
        3. Create certificate bundle
        4. Sign bundle
        5. Queue submission (background)
        6. Save image (if requested)

        Workflow (Legacy mode):
        1. Capture raw Bayer data
        2. Hash raw data
        3. Generate camera token
        4. Sign bundle
        5. Queue submission (background)
        6. Save image (if requested)

        Args:
            save_image: Whether to save processed image to disk

        Returns:
            Dictionary with capture results
        """
        print(f"=== Capture #{self.capture_count + 1} ===")

        start_time = time.time()

        # Step 1: Capture raw data and hash
        capture_result = self.capture_manager.capture_with_hash()

        if self.use_certificates:
            # Certificate mode: No token generation needed
            token_time = 0.0
            print(f"✓ Using embedded certificate (no token generation needed)")

            # Step 3: Create certificate bundle
            from .aggregation_client import CertificateBundle

            bundle = CertificateBundle(
                image_hash=capture_result.image_hash,
                camera_cert_pem=self.provisioning_data.device_certificate,
                timestamp=capture_result.timestamp,
                gps_hash=None,  # TODO: GPS integration
                bundle_signature=None  # Sign in to_json()
            )

            # Step 4: Sign bundle (happens in to_json())
            sign_start = time.time()
            # Bundle is signed when to_json() is called with private key
            sign_time = time.time() - sign_start
            print(f"✓ Certificate bundle created")

        else:
            # Legacy mode: Generate camera token
            # Step 2: Generate camera token
            token_start = time.time()
            camera_token = self.token_generator.generate_token()
            token_time = time.time() - token_start
            print(f"✓ Camera token: table={camera_token.table_id}, "
                  f"key_index={camera_token.key_index} ({token_time:.3f}s)")

            # Step 3: Create authentication bundle
            bundle = AuthenticationBundle(
                image_hash=capture_result.image_hash,
                camera_token=camera_token.to_dict(),
                timestamp=capture_result.timestamp,
                table_assignments=self.provisioning_data.table_assignments,
                gps_hash=None,  # TODO: GPS integration
                device_signature=None  # Sign below
            )

            # Step 4: Sign bundle
            sign_start = time.time()
            signature = sign_bundle(bundle.to_json(), self.tpm._private_key)
            bundle.device_signature = signature.hex()
            sign_time = time.time() - sign_start
            print(f"✓ Bundle signed ({sign_time:.3f}s)")

        # Step 5: Queue for submission (non-blocking)
        self.submission_queue.enqueue(bundle)

        # Step 6: Save image metadata
        if save_image:
            output_file = self.output_dir / f"IMG_{capture_result.timestamp}.json"
            with open(output_file, 'w') as f:
                json.dump({
                    'image_hash': capture_result.image_hash,
                    'timestamp': capture_result.timestamp,
                    'device_serial': self.provisioning_data.device_serial,
                    'bundle': bundle.to_json()
                }, f, indent=2)
            print(f"✓ Saved: {output_file.name}")

        total_time = time.time() - start_time
        self.capture_count += 1

        result = {
            'capture_number': self.capture_count,
            'image_hash': capture_result.image_hash,
            'timestamp': capture_result.timestamp,
            'capture_time': capture_result.capture_time,
            'hash_time': capture_result.hash_time,
            'token_time': token_time,
            'sign_time': sign_time,
            'total_time': total_time,
            'output_file': str(output_file) if save_image else None
        }

        print(f"✓ Total time: {total_time:.3f}s\n")
        return result

    def capture_timelapse(
        self,
        interval: int,
        count: int = 0
    ) -> None:
        """
        Capture timelapse sequence.

        Args:
            interval: Seconds between captures
            count: Number of captures (0 = infinite)
        """
        print(f"Starting timelapse:")
        print(f"  Interval: {interval}s")
        print(f"  Count: {count if count > 0 else 'infinite'}\n")

        capture_num = 0

        try:
            while True:
                if count > 0 and capture_num >= count:
                    break

                self.capture_photo()
                capture_num += 1

                if count > 0 and capture_num < count:
                    print(f"Waiting {interval}s...\n")
                    time.sleep(interval)
                elif count == 0:
                    time.sleep(interval)

        except KeyboardInterrupt:
            print(f"\n\nTimelapse stopped")

        print(f"Captured {capture_num} photos")

    def test_connection(self) -> bool:
        """
        Test connection to blockchain node.

        Returns:
            True if server is reachable
        """
        print("Testing blockchain node connection...")
        if self.aggregation_client.test_connection():
            print("✓ Blockchain node is reachable")
            return True
        else:
            print("✗ Blockchain node not reachable")
            return False

    def show_info(self) -> None:
        """Show device information."""
        print("=== Birthmark Camera Info ===\n")
        print(f"Device Serial: {self.provisioning_data.device_serial}")
        print(f"Device Family: {self.provisioning_data.device_family}")
        print(f"Table Assignments: {self.provisioning_data.table_assignments}")
        print(f"NUC Hash: {self.provisioning_data.nuc_hash[:16]}...")
        print(f"\nCaptures: {self.capture_count}")

        # Submission statistics
        stats = self.submission_queue.get_statistics()
        print(f"\nSubmission Queue:")
        print(f"  Queued: {stats['queued']}")
        print(f"  Submitted: {stats['submitted']}")
        print(f"  Failed: {stats['failed']}")

    def close(self) -> None:
        """Clean up resources."""
        print("\nShutting down...")

        # Stop submission worker
        self.submission_queue.stop_worker(wait=True)

        # Close camera
        self.capture_manager.close()

        print("✓ Shutdown complete")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Birthmark Protocol Camera (Raspberry Pi Prototype)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Single capture (legacy format)
  python -m camera_pi capture

  # Single capture (certificate format)
  python -m camera_pi capture --use-certificates

  # Timelapse (30 second interval, 100 photos)
  python -m camera_pi timelapse --interval 30 --count 100

  # Continuous timelapse with certificates
  python -m camera_pi timelapse --interval 10 --use-certificates

  # Test connection
  python -m camera_pi test

  # Show device info
  python -m camera_pi info
        """
    )

    parser.add_argument(
        'command',
        choices=['capture', 'timelapse', 'test', 'info'],
        help='Command to execute'
    )

    parser.add_argument(
        '--provisioning',
        type=Path,
        help='Path to provisioning data file (default: ./data/provisioning.json)'
    )

    parser.add_argument(
        '--aggregator',
        default='http://localhost:8545',
        help='Birthmark blockchain node URL (default: http://localhost:8545)'
    )

    parser.add_argument(
        '--output',
        type=Path,
        help='Output directory for captures (default: ./data/captures)'
    )

    parser.add_argument(
        '--interval',
        type=int,
        help='Timelapse interval in seconds'
    )

    parser.add_argument(
        '--count',
        type=int,
        default=0,
        help='Number of captures for timelapse (0 = infinite)'
    )

    parser.add_argument(
        '--mock',
        action='store_true',
        help='Use mock camera for testing'
    )

    parser.add_argument(
        '--use-certificates',
        action='store_true',
        help='Use certificate-based authentication (new format)'
    )

    args = parser.parse_args()

    try:
        # Initialize camera
        camera = BirthmarkCamera(
            provisioning_path=args.provisioning,
            aggregation_url=args.aggregator,
            output_dir=args.output,
            use_mock_camera=args.mock,
            use_certificates=args.use_certificates
        )

        # Execute command
        if args.command == 'capture':
            camera.capture_photo()

        elif args.command == 'timelapse':
            if not args.interval:
                print("Error: --interval required for timelapse")
                sys.exit(1)
            camera.capture_timelapse(args.interval, args.count)

        elif args.command == 'test':
            camera.test_connection()

        elif args.command == 'info':
            camera.show_info()

        # Cleanup
        camera.close()

    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        sys.exit(1)

    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
