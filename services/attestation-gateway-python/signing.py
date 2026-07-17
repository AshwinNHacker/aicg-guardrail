"""
AICG — root signing.

The Merkle root alone proves internal consistency of a dataset snapshot;
signing it with a private key held by the attestation gateway proves *who*
attested to it and *when* — anyone with the public key can later verify a
claimed root was genuinely issued by this pipeline and hasn't been
substituted for a different (poisoned) dataset's root.
"""
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)
from cryptography.hazmat.primitives import serialization
from cryptography.exceptions import InvalidSignature


def generate_keypair():
    private_key = Ed25519PrivateKey.generate()
    public_key = private_key.public_key()
    return private_key, public_key


def sign_root(private_key: Ed25519PrivateKey, root_hash: str) -> bytes:
    return private_key.sign(root_hash.encode("utf-8"))


def verify_signature(public_key: Ed25519PublicKey, root_hash: str, signature: bytes) -> bool:
    try:
        public_key.verify(signature, root_hash.encode("utf-8"))
        return True
    except InvalidSignature:
        return False


def serialize_public_key(public_key: Ed25519PublicKey) -> str:
    return public_key.public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    ).hex()


def load_public_key(hex_bytes: str) -> Ed25519PublicKey:
    return Ed25519PublicKey.from_public_bytes(bytes.fromhex(hex_bytes))


def serialize_private_key(private_key: Ed25519PrivateKey) -> str:
    return private_key.private_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PrivateFormat.Raw,
        encryption_algorithm=serialization.NoEncryption(),
    ).hex()


def load_private_key(hex_bytes: str) -> Ed25519PrivateKey:
    return Ed25519PrivateKey.from_private_bytes(bytes.fromhex(hex_bytes))
