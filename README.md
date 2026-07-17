# AICG — Enterprise AI Compliance & Poisoning Guardrail

A middleware pipeline that sits between an enterprise data lake and a
training environment, protecting against the three ways a training
dataset actually goes wrong:

1. **Tampering after approval** — caught deterministically by a signed
   Merkle tree over the dataset.
2. **Poisoning baked in from the start** — caught statistically by a
   real published defense (spectral signature analysis), not a heuristic.
3. **"This specific record needs to come out of the model"** (GDPR
   erasure, or poisoning discovered after training) — handled by
   targeted machine unlearning instead of an expensive full retrain.

Built from an initial architecture blueprint and extended with a real,
tested poisoning detector, stability fixes for the unlearning engine,
an event-driven audit trail, and a working live-attack simulation in
the dashboard.

## Verified, not just written

Every core algorithm here was actually run and tested before being
packaged, not just written and assumed correct:

- **Merkle attestation**: exhaustively tested across 11 different
  dataset sizes (odd, even, powers of two) — every inclusion proof
  verifies correctly. A live HTTP simulation of an actual poisoning
  attack (attest clean data, inject a poisoned record, attempt to
  re-verify) was run end-to-end and correctly blocked.
- **Poisoning detector**: tested against a synthetic injected backdoor
  trigger cluster — the spectral signature method catches ≥80% of
  planted poison samples in the test suite.
- **Unlearning controller**: tests memorize a forget set first (so
  there's something real to unlearn), then confirm forget-set
  confidence drops while retain-set accuracy is preserved within 15
  points — not runnable in the environment this was built in (no GPU
  toolchain available), but the logic and test are complete; run
  `pytest` yourself to confirm before deploying.

## Architecture

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the full reasoning
behind each design decision.

```
Raw data ──> Attestation Gateway (Merkle + Ed25519 signing)
                    │
                    ▼
             Poisoning Detector (spectral signatures + loss outliers)
                    │
          [ events flow through Kafka ]
                    │
                    ▼
             Event Relay (Go) ──> Postgres audit log

Unlearning Controller (PyTorch, NegGrad + stability safeguards)
                    │
                    ▼
             Compliance Dashboard (React/TypeScript)
```

## Repo layout

```
services/
  attestation-gateway-python/   Merkle tree, Ed25519 signing, FastAPI — tested
    merkle.py                    Tree construction + inclusion proofs
    signing.py                   Ed25519 sign/verify
    attestation_api.py           /attest, /verify endpoints
    tests/test_merkle.py         Adversarial tamper-detection tests
  poisoning-detector-python/     Spectral signature + loss-based detection — tested
    detector.py
    api.py
    tests/test_detector.py       Synthetic backdoor injection test
  unlearning-controller-python/  PyTorch NegGrad unlearning, stability-hardened
    model.py
    unlearning.py
    api.py
    tests/test_unlearning.py
  event-relay-go/                Kafka consumer -> Postgres audit log
dashboard/                       React/TS compliance console + live attack simulator
db/postgres/                     Audit log + erasure request schema
infra/kafka/                     Event bus topic notes
docs/ARCHITECTURE.md             Full design rationale
```

## Running it

```bash
docker compose up --build
```

Or run each Python service standalone for development:

```bash
cd services/attestation-gateway-python
pip install -r requirements.txt
pytest tests/ -v          # confirm tamper detection works
uvicorn attestation_api:app --port 8100
```

Try the actual attack scenario the blueprint asked for:

```bash
# Attest a clean dataset
curl -X POST http://localhost:8100/attest -H "Content-Type: application/json" \
  -d '{"dataset_id":"batch-1","chunks":["a","b","c"]}'

# Verify with a poisoned record swapped in — gets blocked
curl -X POST http://localhost:8100/verify -H "Content-Type: application/json" \
  -d '{"dataset_id":"batch-1","chunks":["a","POISONED","c"]}'
```

Dashboard: `http://localhost:3200` — includes a one-click version of
this exact simulation.

## Status

Attestation gateway and poisoning detector: fully implemented, tested,
and verified end-to-end (real HTTP calls, real crypto, real synthetic
attack injection) in the environment this was built in. Unlearning
controller: complete implementation with stability fixes over the
original blueprint's naive approach, tests written but not run here
(no PyTorch/GPU toolchain in this sandbox) — verify with `pytest`
before relying on it. Event relay (Go) and dashboard (React) are
complete; the dashboard's build and tests were run and pass.

## License

MIT — see [LICENSE](LICENSE).
