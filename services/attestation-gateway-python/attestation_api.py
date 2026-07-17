"""
AICG — attestation gateway API.

Exposes the Merkle attestation + signing pipeline as a service: ingest a
dataset snapshot, get back a signed root; later, submit a dataset for
verification and get a definitive block/allow decision before it's
allowed anywhere near a training job.
"""
import os
import time
from typing import List

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from merkle import DataAttestationPipeline
from signing import (
    generate_keypair,
    sign_root,
    verify_signature,
    serialize_public_key,
    serialize_private_key,
    load_private_key,
    load_public_key,
)

app = FastAPI(title="aicg-attestation-gateway")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten to the dashboard's real origin in production
    allow_methods=["*"],
    allow_headers=["*"],
)
pipeline = DataAttestationPipeline()

# In production the private key is pulled from a secrets manager (Vault,
# KMS) at startup, never generated fresh on every restart. Generating one
# here keeps the service self-contained for local dev / this scaffold.
_PRIVATE_KEY_HEX = os.environ.get("ATTESTATION_PRIVATE_KEY")
if _PRIVATE_KEY_HEX:
    private_key = load_private_key(_PRIVATE_KEY_HEX)
    public_key = private_key.public_key()
else:
    private_key, public_key = generate_keypair()

# In-memory attestation log for this scaffold; swap for the Postgres
# audit_log table (db/postgres/init.sql) in a real deployment.
_ATTESTATIONS = {}


class AttestRequest(BaseModel):
    dataset_id: str
    chunks: List[str]  # base64 or plain text chunks; hashed as UTF-8 bytes


class VerifyRequest(BaseModel):
    dataset_id: str
    chunks: List[str]


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/public-key")
def get_public_key():
    return {"public_key_hex": serialize_public_key(public_key)}


@app.post("/attest")
def attest(req: AttestRequest):
    chunk_bytes = [c.encode("utf-8") for c in req.chunks]
    root_node = pipeline.build_merkle_tree(chunk_bytes)
    signature = sign_root(private_key, root_node.hash_val)

    record = {
        "dataset_id": req.dataset_id,
        "root_hash": root_node.hash_val,
        "signature_hex": signature.hex(),
        "chunk_count": len(chunk_bytes),
        "attested_at": time.time(),
    }
    _ATTESTATIONS[req.dataset_id] = record
    return record


@app.post("/verify")
def verify(req: VerifyRequest):
    record = _ATTESTATIONS.get(req.dataset_id)
    if not record:
        return {"verified": False, "reason": "no attestation on file for this dataset_id"}

    chunk_bytes = [c.encode("utf-8") for c in req.chunks]
    recomputed_root = pipeline.build_merkle_tree(chunk_bytes).hash_val

    if recomputed_root != record["root_hash"]:
        return {
            "verified": False,
            "reason": "root hash mismatch — dataset has been modified since attestation",
            "expected_root": record["root_hash"],
            "actual_root": recomputed_root,
        }

    sig_valid = verify_signature(public_key, record["root_hash"], bytes.fromhex(record["signature_hex"]))
    return {"verified": sig_valid, "root_hash": recomputed_root}


@app.get("/attestations")
def list_attestations():
    return list(_ATTESTATIONS.values())
