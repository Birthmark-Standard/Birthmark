"""Merkle tree generation and verification for batch processing."""

import hashlib
from typing import List, Dict, Tuple


def generate_merkle_tree(image_hashes: List[str]) -> Tuple[str, Dict[str, List[Dict]]]:
    """
    Generate Merkle tree from image hashes.

    Args:
        image_hashes: List of SHA-256 hashes (hex strings)

    Returns:
        Tuple of (merkle_root, proofs)
        - merkle_root: Root hash (hex string)
        - proofs: Dict mapping image_hash -> proof_path
          where proof_path is list of {"hash": hex_string, "position": "left"|"right"}
    """
    if not image_hashes:
        raise ValueError("Cannot generate Merkle tree from empty list")

    # Convert to bytes
    leaves = [bytes.fromhex(h) for h in image_hashes]
    n = len(leaves)

    # Calculate tree depth and pad to power of 2
    depth = (n - 1).bit_length() if n > 0 else 0
    padded_size = 2**depth
    padding = [b"\x00" * 32] * (padded_size - n)
    leaves.extend(padding)

    # Build tree bottom-up
    tree = [leaves]  # Level 0 (leaves)

    current_level = leaves
    while len(current_level) > 1:
        next_level = []
        for i in range(0, len(current_level), 2):
            left = current_level[i]
            right = current_level[i + 1]
            parent = hashlib.sha256(left + right).digest()
            next_level.append(parent)
        tree.append(next_level)
        current_level = next_level

    merkle_root = tree[-1][0].hex()

    # Generate proofs for each original image (not padding)
    proofs = {}
    for idx in range(n):
        proof_path = []
        current_idx = idx

        for level in range(depth):
            sibling_idx = current_idx ^ 1  # XOR flips last bit
            if sibling_idx < len(tree[level]):
                sibling = tree[level][sibling_idx]
                proof_path.append(
                    {
                        "hash": sibling.hex(),
                        "position": "right" if current_idx % 2 == 0 else "left",
                    }
                )
            current_idx //= 2

        proofs[image_hashes[idx]] = proof_path

    return merkle_root, proofs


def verify_merkle_proof(image_hash: str, proof_path: List[Dict], merkle_root: str) -> bool:
    """
    Verify that image_hash is included in tree with given merkle_root.

    Args:
        image_hash: SHA-256 hash to verify (hex string)
        proof_path: List of {"hash": hex_string, "position": "left"|"right"}
        merkle_root: Expected root hash (hex string)

    Returns:
        True if proof is valid, False otherwise
    """
    current_hash = bytes.fromhex(image_hash)

    for step in proof_path:
        sibling = bytes.fromhex(step["hash"])
        if step["position"] == "left":
            current_hash = hashlib.sha256(sibling + current_hash).digest()
        else:
            current_hash = hashlib.sha256(current_hash + sibling).digest()

    return current_hash.hex() == merkle_root


def calculate_tree_depth(image_count: int) -> int:
    """Calculate Merkle tree depth for given number of images."""
    import math

    if image_count <= 0:
        return 0
    return math.ceil(math.log2(image_count))
