"""
AICG — poisoning detector API.

Accepts a batch of feature vectors (or per-sample losses) and returns
which indices look poisoned. Called by the pipeline orchestrator after
attestation passes but before a dataset is handed to training — integrity
(layer 1) and content anomaly (layer 2) are separate, complementary
checks: a dataset can be internally consistent (nothing tampered with
after signing) and still contain poison that was there from the start.
"""
from typing import List, Optional

import numpy as np
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from detector import compute_spectral_signatures, loss_based_outliers

app = FastAPI(title="aicg-poisoning-detector")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class SpectralRequest(BaseModel):
    features: List[List[float]]
    removal_fraction: float = 0.05


class LossRequest(BaseModel):
    losses: List[float]
    z_threshold: float = 3.0


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/detect/spectral")
def detect_spectral(req: SpectralRequest):
    features = np.array(req.features)
    result = compute_spectral_signatures(features, removal_fraction=req.removal_fraction)
    return {
        "flagged_indices": result.flagged_indices,
        "threshold": result.threshold,
        "outlier_scores": result.outlier_scores.tolist(),
    }


@app.post("/detect/loss-outliers")
def detect_loss_outliers(req: LossRequest):
    losses = np.array(req.losses)
    flagged = loss_based_outliers(losses, z_threshold=req.z_threshold)
    return {"flagged_indices": flagged}
