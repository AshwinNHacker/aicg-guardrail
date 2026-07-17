"""Unit tests for Merkle attestation."""

from src.attestation import DataAttestationPipeline, IngestionGate


def test_root_stable_for_same_chunks():
    p = DataAttestationPipeline()
    chunks = [b"a", b"b", b"c", b"d"]
    assert p.root_hash(chunks) == p.root_hash(chunks)


def test_root_changes_when_chunk_mutates():
    p = DataAttestationPipeline()
    chunks = [b"a", b"b", b"c", b"d"]
    root = p.root_hash(chunks)
    chunks[1] = b"b-poisoned"
    assert p.root_hash(chunks) != root


def test_validate_root_true_and_false():
    p = DataAttestationPipeline()
    chunks = [b"x", b"y"]
    root = p.root_hash(chunks)
    assert p.validate_root(chunks, root) is True
    assert p.validate_root([b"x", b"z"], root) is False


def test_empty_raises():
    p = DataAttestationPipeline()
    try:
        p.build_merkle_tree([])
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_ingestion_gate_accepts_clean_batch():
    gate = IngestionGate()
    chunks = [b"doc1", b"doc2", b"doc3"]
    signed = gate.pipeline.root_hash(chunks)
    result = gate.evaluate(chunks, signed)
    assert result["status"] == "accepted"
    assert result["alert"] is None
