"""Cryptographic attestation engine — SHA-256 Merkle trees for data lineage."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class MerkleNode:
    left: Optional["MerkleNode"]
    right: Optional["MerkleNode"]
    hash_val: str


class DataAttestationPipeline:
    """Ensures data lineage integrity before model training ingestion."""

    @staticmethod
    def compute_sha256(data: bytes) -> str:
        return hashlib.sha256(data).hexdigest()

    def build_merkle_tree(self, data_chunks: List[bytes]) -> MerkleNode:
        if not data_chunks:
            raise ValueError("Data pipeline received empty ingestion stream.")

        leaves = [
            MerkleNode(None, None, self.compute_sha256(chunk)) for chunk in data_chunks
        ]

        while len(leaves) > 1:
            next_level: List[MerkleNode] = []
            for i in range(0, len(leaves), 2):
                left = leaves[i]
                right = leaves[i + 1] if i + 1 < len(leaves) else leaves[i]
                combined = self.compute_sha256(
                    (left.hash_val + right.hash_val).encode("utf-8")
                )
                next_level.append(MerkleNode(left, right, combined))
            leaves = next_level

        return leaves[0]

    def root_hash(self, data_chunks: List[bytes]) -> str:
        return self.build_merkle_tree(data_chunks).hash_val

    def validate_root(self, data_chunks: List[bytes], expected_root: str) -> bool:
        return self.root_hash(data_chunks) == expected_root


class IngestionGate:
    """Blocks batches whose Merkle root no longer matches the signed root."""

    def __init__(self, pipeline: Optional[DataAttestationPipeline] = None) -> None:
        self.pipeline = pipeline or DataAttestationPipeline()

    def evaluate(
        self, data_chunks: List[bytes], signed_root: str
    ) -> dict:
        recomputed = self.pipeline.root_hash(data_chunks)
        valid = recomputed == signed_root
        if valid:
            return {
                "status": "accepted",
                "signed_root": signed_root,
                "recomputed_root": recomputed,
                "alert": None,
            }
        return {
            "status": "blocked",
            "signed_root": signed_root,
            "recomputed_root": recomputed,
            "alert": "aicg.poison.merkle_fail",
        }
