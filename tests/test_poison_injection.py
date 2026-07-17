"""
Adversarial attack scenario:

1. Sign Merkle root over clean chunks
2. Inject a poison token into a chunk post-sign
3. Recompute root → mismatch
4. Ingestion gate blocks + emits alert
"""

from src.attestation import DataAttestationPipeline, IngestionGate

POISON = b"{{POISON_TOKEN::override_label=1}}"


def test_poison_injection_blocks_ingestion():
    pipeline = DataAttestationPipeline()
    gate = IngestionGate(pipeline)

    chunks = [
        b"enterprise_doc_001::policy",
        b"enterprise_doc_002::email",
        b"enterprise_doc_003::ticket",
        b"enterprise_doc_004::chat",
        b"enterprise_doc_005::wiki",
        b"enterprise_doc_006::log",
        b"enterprise_doc_007::pdf",
        b"enterprise_doc_008::csv",
    ]

    signed_root = pipeline.root_hash(chunks)

    # Post-signature mutation (attacker)
    chunks[3] = chunks[3] + POISON

    decision = gate.evaluate(chunks, signed_root)

    assert decision["status"] == "blocked"
    assert decision["alert"] == "aicg.poison.merkle_fail"
    assert decision["recomputed_root"] != signed_root
    assert decision["signed_root"] == signed_root


def test_clean_batch_after_sign_is_accepted():
    pipeline = DataAttestationPipeline()
    gate = IngestionGate(pipeline)
    chunks = [b"clean-a", b"clean-b", b"clean-c"]
    signed = pipeline.root_hash(chunks)
    decision = gate.evaluate(chunks, signed)
    assert decision["status"] == "accepted"
