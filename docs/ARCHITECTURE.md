# Architecture

## The three layers, and what each one actually protects against

A model trained on compromised data has three distinct failure points,
and AICG addresses each one separately rather than trying to catch
everything with one mechanism:

1. **Data was tampered with after it was approved.** Solved by
   cryptographic attestation (Merkle tree + signature) — deterministic,
   catches even a single-byte change.
2. **The data was poisoned from the start, before anyone signed off on
   it.** Solved by spectral signature / loss-based anomaly detection —
   statistical, catches patterns a human review would miss at scale.
3. **A specific record needs to be removed from an already-trained
   model** (GDPR erasure request, discovered poisoning after the fact).
   Solved by targeted unlearning — surgical, avoids a full retrain.

## Data flow

```
Raw enterprise data
        │
Attestation gateway (Python, FastAPI)
  builds a Merkle tree, signs the root (Ed25519)
        │  event: "attested"
        ▼
Poisoning detector (Python, FastAPI)
  spectral signature analysis on feature vectors,
  loss-based outlier detection
        │  event: "poisoning_detected"
        ▼
[ Training proceeds only if both layers pass ]

Both events flow through Kafka to:

Event relay (Go)
  consumes Kafka events, writes compliance audit log
        │
        ▼
Postgres (audit_log, erasure_requests)

Separately, on demand:
Unlearning controller (Python, PyTorch)
  interleaved NegGrad forget/retain steps,
  returns before/after accuracy report
        │  event: "unlearning_completed"
        ▼
Compliance dashboard (React/TS)
  service health, lineage table, live poisoning-attack simulator
```

## Why each piece, not just a language list

**Merkle tree + Ed25519, not just a flat hash.** A single SHA-256 over
the whole dataset would catch tampering too, but a Merkle tree gives you
inclusion proofs — you can prove one specific record was part of an
attested dataset without re-hashing everything, which matters when a
compliance request asks "was record X part of the training set attested
on this date." The signature (not just the hash) is what proves *this
pipeline* attested it, not an attacker who recomputed a new root after
tampering — the tests in `attestation-gateway-python/tests/` verify a
stale signature explicitly fails against a tampered root, not just that
the hashes differ.

**Spectral signatures, a real published defense, not a heuristic.**
Tran, Li & Madry (2018) showed that backdoor-poisoned samples distort
the covariance structure of a class's feature representations in a
detectable way. This project implements that method directly (see
`poisoning-detector-python/detector.py`), tested against a synthetic
injected trigger cluster to confirm it actually catches the intended
attack pattern, not just clean statistical noise.

**Interleaved forget/retain steps, not block-sequential.** The original
NegGrad idea (ascend loss on the forget set) is a real technique, but
naive unbounded ascent for a full epoch is a known failure mode — it can
diverge and damage general model utility, not just the targeted memory.
This implementation interleaves a retain-set step after every forget
batch and clips gradients, specifically to keep the "surgical" property
the compliance use case actually needs. The unlearning report returns
before/after accuracy on both sets — an auditor needs numbers, not a log
line saying "unlearning ran."

**Go for the event relay, not another Python service.** This is a
narrow, high-throughput consume-and-write loop with no business logic —
exactly the shape Go's concurrency model handles well, and keeping it
separate from the three ML-heavy Python services means it can restart
or scale independently without touching them.

**Kafka as the spine, not direct service-to-service calls.** Every
pipeline event (attested, poisoning detected, unlearning completed) is
independently useful to more than one consumer — the audit log today,
potentially a real-time compliance alerting service tomorrow. Publishing
to a topic instead of calling the audit service directly means adding
that second consumer never touches the services that produce the events.
