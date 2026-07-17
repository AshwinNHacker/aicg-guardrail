"""
The test the project blueprint specifically asked for: inject a tampered/
poisoned chunk into an already-attested dataset and prove the pipeline
catches it deterministically, before it ever reaches training.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from merkle import DataAttestationPipeline
from signing import generate_keypair, sign_root, verify_signature


def test_merkle_root_is_deterministic():
    pipeline = DataAttestationPipeline()
    chunks = [b"sample_1", b"sample_2", b"sample_3", b"sample_4"]

    root_a = pipeline.build_merkle_tree(chunks).hash_val
    root_b = pipeline.build_merkle_tree(chunks).hash_val

    assert root_a == root_b, "identical data must produce identical roots"


def test_tampering_a_single_chunk_changes_the_root():
    pipeline = DataAttestationPipeline()
    original_chunks = [b"training_sample_1", b"training_sample_2", b"training_sample_3"]
    original_root = pipeline.build_merkle_tree(original_chunks).hash_val

    # Simulate a data poisoning attack: one training sample is swapped for
    # an attacker-controlled payload after the dataset was attested.
    poisoned_chunks = list(original_chunks)
    poisoned_chunks[1] = b"<script>malicious_payload</script>"
    poisoned_root = pipeline.build_merkle_tree(poisoned_chunks).hash_val

    assert original_root != poisoned_root, "tampering must be detectable via root mismatch"


def test_full_attestation_and_tamper_detection_flow():
    """End-to-end: attest a dataset, sign the root, then simulate the
    ingestion layer receiving a tampered dataset and rejecting it."""
    pipeline = DataAttestationPipeline()
    private_key, public_key = generate_keypair()

    clean_dataset = [f"record_{i}".encode() for i in range(50)]
    attested_root = pipeline.build_merkle_tree(clean_dataset).hash_val
    signature = sign_root(private_key, attested_root)

    # Signature itself is valid for the attested root.
    assert verify_signature(public_key, attested_root, signature)

    # Attacker injects a poisoned record before training ingestion.
    tampered_dataset = list(clean_dataset)
    tampered_dataset[25] = b"POISONED_RECORD_INJECTED_BY_ATTACKER"
    recomputed_root = pipeline.build_merkle_tree(tampered_dataset).hash_val

    # The ingestion layer's job: recompute the root and compare to the
    # signed one. A mismatch means block ingestion, full stop.
    ingestion_should_block = recomputed_root != attested_root
    assert ingestion_should_block, "poisoned dataset must fail root verification"

    # Critically: the old signature must NOT validate against the new
    # (tampered) root — an attacker can't just recompute and re-sign
    # without the private key.
    assert not verify_signature(public_key, recomputed_root, signature)


def test_inclusion_proof_verifies_for_genuine_chunk():
    pipeline = DataAttestationPipeline()
    chunks = [f"chunk_{i}".encode() for i in range(7)]  # odd count exercises duplication path
    root = pipeline.build_merkle_tree(chunks).hash_val

    proof = pipeline.build_proof(chunks, target_index=3)
    assert pipeline.verify_proof(proof, root)


def test_inclusion_proof_fails_for_wrong_root():
    pipeline = DataAttestationPipeline()
    chunks = [f"chunk_{i}".encode() for i in range(7)]
    pipeline.build_merkle_tree(chunks)

    proof = pipeline.build_proof(chunks, target_index=3)
    assert not pipeline.verify_proof(proof, "0" * 64)


if __name__ == "__main__":
    test_merkle_root_is_deterministic()
    test_tampering_a_single_chunk_changes_the_root()
    test_full_attestation_and_tamper_detection_flow()
    test_inclusion_proof_verifies_for_genuine_chunk()
    test_inclusion_proof_fails_for_wrong_root()
    print("[+] all attestation tests passed — tamper detection confirmed working")
