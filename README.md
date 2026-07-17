# AICG — Enterprise AI Compliance & Poisoning Guardrail

Production-style **middleware pipeline** between an enterprise data lake (S3/GCS) and a training environment (PyTorch / Hugging Face).

This repo is a **portfolio-ready** demonstration of:

1. **Cryptographic attestation** — SHA-256 Merkle trees over data chunks  
2. **Poison / anomaly detection hooks** — influence-oriented validation surface  
3. **Machine unlearning** — NegGrad-style targeted forget without full retrain  
4. **Live compliance dashboard** — ops console for hiring-panel demos  

> Demo metrics in the UI are labelled as synthetic. Core crypto (Merkle) and unlearning loops are real Python code.

---

## Architecture

```
[ Raw Enterprise Data ]
         │
         ▼
 ┌───────────────┐      ┌───────────────────────────────┐
 │ Data Ingestion│ ───> │ Cryptographic Attestation     │ ──> [ Merkle Tree Store ]
 └───────────────┘      │ (SHA-256 + signed root)       │
                        └───────────────────────────────┘
                                       │
                                       ▼
                        ┌───────────────────────────────┐
                        │ Anomaly & Poisoning Detection │ <── [ Dynamic Influence Map ]
                        └───────────────────────────────┘
                                       │
                                       ▼
                        ┌───────────────────────────────┐
                        │ Model Unlearning Engine       │ ──> [ Compliant Target Model ]
                        │ (NegGrad / UAM-style)         │
                        └───────────────────────────────┘
```

### Microservices (logical)

| Service | Role |
|--------|------|
| **Attestation Gateway** | Chunk hashing, Merkle root, signature; post-sign tamper fails validation |
| **Influence Mapping Layer** | Gradient-attribution surface for suspect documents |
| **Unlearning Controller** | NegGrad forget + retain-set alignment |

For a full MNC-style deploy: split attestation and training into Docker services and wire them over **Kafka / RabbitMQ**.

---

## Quick start

### 1. Dashboard (no install)

Open in a browser:

```text
dashboard/aicg-compliance-dashboard.html
```

Try **Run attack sim** — injects a poison token after sign, recomputes the Merkle root, blocks ingestion.

Keyboard: `1`–`8` switch views · `R` refresh.

### 2. Python pipeline

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
# source .venv/bin/activate

pip install -r requirements.txt
python -m src.demo_pipeline
pytest -q
```

Optional: install PyTorch from [pytorch.org](https://pytorch.org) if `pip install torch` is slow on your platform.

---

## Repository layout

```text
aicg/
├── README.md
├── requirements.txt
├── LICENSE
├── .gitignore
├── dashboard/
│   └── aicg-compliance-dashboard.html   # Live compliance console
├── src/
│   ├── __init__.py
│   ├── attestation.py                   # Merkle tree + SHA-256
│   ├── unlearning.py                    # NegGrad controller (PyTorch)
│   ├── poison_detect.py                 # Spectral / score helpers
│   └── demo_pipeline.py                 # End-to-end CLI demo
└── tests/
    ├── test_attestation.py
    └── test_poison_injection.py         # Adversarial injection scenario
```

---

## Attack scenario (tests)

`tests/test_poison_injection.py` deliberately mutates a chunk **after** the root is signed and asserts:

- recomputed root ≠ signed root  
- ingestion gate returns `blocked`  
- alert payload is emitted  

This is the same story the dashboard’s **Attack sim** view walks through visually.

---

## Compliance dashboard features

- Lineage integrity (Merkle verification status)  
- Ingestion jobs / queue depth  
- Attestation tree visualization (browser Web Crypto SHA-256)  
- Poison flags + influence heatmap  
- Unlearning job runner (demo NegGrad console)  
- Immutable-style audit log + JSON export  

---

## How to put this on GitHub

1. Unzip this package.  
2. Create a new empty repository on GitHub (no README if you already have one here).  
3. From the unzipped folder:

```bash
git init
git add .
git commit -m "Initial commit: AICG compliance pipeline + dashboard"
git branch -M main
git remote add origin https://github.com/<your-user>/<your-repo>.git
git push -u origin main
```

4. In the repo **About** section, set description to something like:  
   `Enterprise AI compliance middleware — Merkle attestation, poison detection, NegGrad unlearning + live ops dashboard`

---

## License

MIT — see [LICENSE](LICENSE).
