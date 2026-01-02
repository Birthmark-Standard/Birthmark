"""
Birthmark Substrate Integration Library

Python client for interacting with the Birthmark Substrate blockchain.
Provides high-level API for submitting and querying image authentication records.
"""

from typing import Optional, Dict, List, Any
from substrateinterface import SubstrateInterface, Keypair, ExtrinsicReceipt
from substrateinterface.exceptions import SubstrateRequestException
import logging

logger = logging.getLogger(__name__)


class BirthmarkSubstrate:
    """
    Client for interacting with Birthmark Substrate node.

    Example:
        >>> client = BirthmarkSubstrate("ws://localhost:9944")
        >>> client.connect()
        >>> result = client.submit_image_record(
        ...     image_hash="a1b2c3d4...",
        ...     submission_type="Camera",
        ...     modification_level=0,
        ...     authority_id="CANON_EOS_R5"
        ... )
        >>> print(f"Submitted in block: {result['block_hash']}")
    """

    def __init__(self, node_url: str = "ws://127.0.0.1:9944", keypair_uri: str = "//Alice"):
        """
        Initialize Birthmark Substrate client.

        Args:
            node_url: WebSocket URL of Substrate node
            keypair_uri: Secret URI for signing transactions (Dev: //Alice, //Bob, etc.)
        """
        self.node_url = node_url
        self.keypair_uri = keypair_uri
        self.substrate: Optional[SubstrateInterface] = None
        self.keypair: Optional[Keypair] = None

    def connect(self) -> None:
        """Connect to Substrate node and load keypair."""
        try:
            self.substrate = SubstrateInterface(
                url=self.node_url,
                ss58_format=42,  # Generic Substrate format
                type_registry_preset='substrate-node-template'
            )
            self.keypair = Keypair.create_from_uri(self.keypair_uri)
            logger.info(f"Connected to {self.node_url}")
            logger.info(f"Using account: {self.keypair.ss58_address}")
        except Exception as e:
            logger.error(f"Failed to connect: {e}")
            raise

    def submit_image_record(
        self,
        image_hash: str,
        submission_type: str,
        modification_level: int,
        authority_id: str,
        parent_image_hash: Optional[str] = None,
        wait_for_inclusion: bool = True,
    ) -> Dict[str, Any]:
        """
        Submit a single image authentication record to the blockchain.

        Args:
            image_hash: SHA-256 hash of image (64 hex characters)
            submission_type: "Camera" or "Software"
            modification_level: 0 (raw), 1 (validated), or 2 (modified)
            authority_id: Manufacturer or software developer identifier
            parent_image_hash: Optional parent hash for provenance chain
            wait_for_inclusion: Wait for block inclusion before returning

        Returns:
            Dictionary with submission result:
            {
                'success': bool,
                'block_hash': str,
                'extrinsic_hash': str,
                'block_number': int,
                'error': Optional[str]
            }
        """
        if not self.substrate or not self.keypair:
            raise RuntimeError("Not connected. Call connect() first.")

        # Validate inputs
        if len(image_hash) != 64:
            raise ValueError("image_hash must be 64 hex characters")
        if modification_level not in (0, 1, 2):
            raise ValueError("modification_level must be 0, 1, or 2")
        if submission_type not in ("Camera", "Software"):
            raise ValueError("submission_type must be 'Camera' or 'Software'")

        # Convert to bytes for Substrate
        image_hash_bytes = bytes.fromhex(image_hash)
        authority_id_bytes = authority_id.encode('utf-8')
        parent_hash_bytes = bytes.fromhex(parent_image_hash) if parent_image_hash else None

        # Create call
        call = self.substrate.compose_call(
            call_module='Birthmark',
            call_function='submit_image_record',
            call_params={
                'image_hash': image_hash_bytes,
                'submission_type': submission_type,
                'modification_level': modification_level,
                'parent_image_hash': parent_hash_bytes,
                'authority_id': authority_id_bytes,
            }
        )

        # Create and submit signed extrinsic
        try:
            extrinsic = self.substrate.create_signed_extrinsic(
                call=call,
                keypair=self.keypair
            )

            receipt: ExtrinsicReceipt = self.substrate.submit_extrinsic(
                extrinsic,
                wait_for_inclusion=wait_for_inclusion
            )

            if receipt.is_success:
                return {
                    'success': True,
                    'block_hash': receipt.block_hash,
                    'extrinsic_hash': receipt.extrinsic_hash,
                    'block_number': receipt.block_number,
                    'error': None,
                }
            else:
                return {
                    'success': False,
                    'block_hash': None,
                    'extrinsic_hash': receipt.extrinsic_hash,
                    'block_number': None,
                    'error': receipt.error_message,
                }
        except SubstrateRequestException as e:
            logger.error(f"Submission failed: {e}")
            return {
                'success': False,
                'block_hash': None,
                'extrinsic_hash': None,
                'block_number': None,
                'error': str(e),
            }

    def submit_image_batch(
        self,
        records: List[Dict[str, Any]],
        wait_for_inclusion: bool = True,
    ) -> Dict[str, Any]:
        """
        Submit multiple image records in a single transaction (more efficient).

        Args:
            records: List of record dictionaries, each with:
                - image_hash: str (64 hex chars)
                - submission_type: str ("Camera" or "Software")
                - modification_level: int (0-2)
                - authority_id: str
                - parent_image_hash: Optional[str]
            wait_for_inclusion: Wait for block inclusion

        Returns:
            Dictionary with submission result (same format as submit_image_record)
        """
        if not self.substrate or not self.keypair:
            raise RuntimeError("Not connected. Call connect() first.")

        if not records or len(records) > 100:
            raise ValueError("Batch must contain 1-100 records")

        # Convert records to Substrate format
        formatted_records = []
        for rec in records:
            formatted_records.append((
                bytes.fromhex(rec['image_hash']),
                rec['submission_type'],
                rec['modification_level'],
                bytes.fromhex(rec['parent_image_hash']) if rec.get('parent_image_hash') else None,
                rec['authority_id'].encode('utf-8'),
            ))

        call = self.substrate.compose_call(
            call_module='Birthmark',
            call_function='submit_image_batch',
            call_params={'records': formatted_records}
        )

        try:
            extrinsic = self.substrate.create_signed_extrinsic(call=call, keypair=self.keypair)
            receipt = self.substrate.submit_extrinsic(extrinsic, wait_for_inclusion=wait_for_inclusion)

            if receipt.is_success:
                return {
                    'success': True,
                    'block_hash': receipt.block_hash,
                    'extrinsic_hash': receipt.extrinsic_hash,
                    'block_number': receipt.block_number,
                    'count': len(records),
                    'error': None,
                }
            else:
                return {
                    'success': False,
                    'error': receipt.error_message,
                }
        except SubstrateRequestException as e:
            logger.error(f"Batch submission failed: {e}")
            return {'success': False, 'error': str(e)}

    def get_image_record(self, image_hash: str) -> Optional[Dict[str, Any]]:
        """
        Query an image record by its hash.

        Args:
            image_hash: SHA-256 hash (64 hex characters)

        Returns:
            Dictionary with record data if found:
            {
                'image_hash': str,
                'submission_type': str,
                'modification_level': int,
                'parent_image_hash': Optional[str],
                'authority_id': str,
                'timestamp': int,
                'block_number': int,
            }

            Returns None if not found.
        """
        if not self.substrate:
            raise RuntimeError("Not connected. Call connect() first.")

        if len(image_hash) != 64:
            raise ValueError("image_hash must be 64 hex characters")

        # Query storage
        result = self.substrate.query(
            module='Birthmark',
            storage_function='ImageRecords',
            params=[bytes.fromhex(image_hash)]
        )

        if result.value:
            rec = result.value
            return {
                'image_hash': rec['image_hash'].hex(),
                'submission_type': 'Camera' if 'Camera' in str(rec['submission_type']) else 'Software',
                'modification_level': rec['modification_level'],
                'parent_image_hash': rec['parent_image_hash'].hex() if rec['parent_image_hash'] else None,
                'authority_id': rec['authority_id'].decode('utf-8'),
                'timestamp': rec['timestamp'],
                'block_number': rec['block_number'],
            }
        return None

    def image_exists(self, image_hash: str) -> bool:
        """
        Check if an image hash exists in the registry.

        Args:
            image_hash: SHA-256 hash (64 hex characters)

        Returns:
            True if image is authenticated, False otherwise
        """
        return self.get_image_record(image_hash) is not None

    def get_total_records(self) -> int:
        """
        Get total number of authenticated images in registry.

        Returns:
            Total record count
        """
        if not self.substrate:
            raise RuntimeError("Not connected. Call connect() first.")

        result = self.substrate.query(
            module='Birthmark',
            storage_function='TotalRecords',
            params=[]
        )

        return result.value if result.value else 0

    def get_block_info(self) -> Dict[str, Any]:
        """
        Get current blockchain state.

        Returns:
            {
                'block_number': int,
                'finalized_number': int,
                'peers': int,
                'is_syncing': bool,
            }
        """
        if not self.substrate:
            raise RuntimeError("Not connected. Call connect() first.")

        block_number = self.substrate.get_block_number(None)
        finalized_hash = self.substrate.get_chain_finalised_head()
        finalized_block = self.substrate.get_block(finalized_hash)
        finalized_number = finalized_block['header']['number']

        health = self.substrate.rpc_request('system_health', [])

        return {
            'block_number': block_number,
            'finalized_number': finalized_number,
            'peers': health['result']['peers'],
            'is_syncing': health['result']['isSyncing'],
        }

    def disconnect(self) -> None:
        """Close connection to node."""
        if self.substrate:
            self.substrate.close()
            logger.info("Disconnected from node")


# Example usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    # Connect to local dev node
    client = BirthmarkSubstrate("ws://localhost:9944", "//Alice")
    client.connect()

    # Submit test record
    result = client.submit_image_record(
        image_hash="a" * 64,  # Test hash
        submission_type="Camera",
        modification_level=0,
        authority_id="TEST_CAMERA_001"
    )

    print(f"Submission result: {result}")

    if result['success']:
        # Query it back
        record = client.get_image_record("a" * 64)
        print(f"Retrieved record: {record}")

    # Get blockchain state
    info = client.get_block_info()
    print(f"Blockchain state: {info}")

    # Get total records
    total = client.get_total_records()
    print(f"Total authenticated images: {total}")

    client.disconnect()
