"""
AICG — cryptographic attestation engine, layer 1.

Builds a Merkle tree over ingested data chunks and detects tampering: if a
single byte of a single chunk changes after the root hash was signed, the
recomputed root won't match, and verification fails deterministically —
this is the same construction Git and blockchain ledgers use for exactly
this property.
"""
import hashlib
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class MerkleNode:
    left: Optional["MerkleNode"]
    right: Optional["MerkleNode"]
    hash_val: str


@dataclass
class MerkleProof:
    """A path of sibling hashes proving a specific chunk is included under
    a given root, without needing the whole dataset to verify it."""
    leaf_hash: str
    siblings: List[str] = field(default_factory=list)
    directions: List[str] = field(default_factory=list)  # "left" or "right" per level


class DataAttestationPipeline:
    """Ensures data lineage integrity before model training ingestion."""

    @staticmethod
    def compute_sha256(data: bytes) -> str:
        return hashlib.sha256(data).hexdigest()

    def build_merkle_tree(self, data_chunks: List[bytes]) -> MerkleNode:
        if not data_chunks:
            raise ValueError("Data pipeline received empty ingestion stream.")

        level = [MerkleNode(None, None, self.compute_sha256(chunk)) for chunk in data_chunks]

        while len(level) > 1:
            next_level = []
            for i in range(0, len(level), 2):
                left = level[i]
                right = level[i + 1] if i + 1 < len(level) else level[i]
                combined = self.compute_sha256((left.hash_val + right.hash_val).encode("utf-8"))
                next_level.append(MerkleNode(left, right, combined))
            level = next_level

        return level[0]

    def build_proof(self, data_chunks: List[bytes], target_index: int) -> MerkleProof:
        """Builds an inclusion proof for one chunk without re-walking the
        whole tree at verification time — only the proof path is needed."""
        hashes = [self.compute_sha256(c) for c in data_chunks]
        leaf_hash = hashes[target_index]
        siblings, directions = [], []
        idx = target_index

        while len(hashes) > 1:
            next_level = []
            pair_idx = idx ^ 1  # sibling index at this level
            if pair_idx < len(hashes):
                siblings.append(hashes[pair_idx])
                directions.append("right" if pair_idx > idx else "left")
            else:
                siblings.append(hashes[idx])  # duplicated node case
                directions.append("right")

            for i in range(0, len(hashes), 2):
                left = hashes[i]
                right = hashes[i + 1] if i + 1 < len(hashes) else hashes[i]
                next_level.append(self.compute_sha256((left + right).encode("utf-8")))

            idx //= 2
            hashes = next_level

        return MerkleProof(leaf_hash=leaf_hash, siblings=siblings, directions=directions)

    @staticmethod
    def verify_proof(proof: MerkleProof, expected_root: str) -> bool:
        current = proof.leaf_hash
        for sibling, direction in zip(proof.siblings, proof.directions):
            pair = (current, sibling) if direction == "right" else (sibling, current)
            current = DataAttestationPipeline.compute_sha256((pair[0] + pair[1]).encode("utf-8"))
        return current == expected_root
