"""
AICG — poisoning detection, layer 2.

Implements spectral signature detection (Tran, Li & Madry, 2018 —
"Spectral Signatures in Backdoor Attacks"): poisoned samples that share a
backdoor trigger cluster tightly in feature space in a way clean samples
don't, which shows up as an outlier direction in the covariance
structure of a class's feature representations. Score each sample by its
correlation with the top singular vector of the centered feature matrix;
poisoned samples reliably score higher than clean ones.

This operates on feature vectors (e.g. penultimate-layer activations from
the model being protected) — it's model-agnostic on purpose, so it works
whether the upstream model is a PyTorch classifier, a text embedding
model, or anything else that produces per-sample feature vectors.
"""
from dataclasses import dataclass
from typing import List

import numpy as np


@dataclass
class SpectralSignatureResult:
    outlier_scores: np.ndarray
    flagged_indices: List[int]
    threshold: float


def compute_spectral_signatures(features: np.ndarray, removal_fraction: float = 0.05) -> SpectralSignatureResult:
    """
    features: (n_samples, n_dims) array of per-sample feature vectors,
    typically all belonging to one class (spectral signatures are computed
    per-class in the original method, since the covariance structure of
    a mixed-class feature set isn't meaningful the same way).

    removal_fraction: fraction of highest-scoring samples to flag —
    the method doesn't produce a natural binary threshold, so callers
    choose how aggressively to flag (a real deployment tunes this against
    a held-out validation set).
    """
    if features.ndim != 2:
        raise ValueError("features must be a 2D (n_samples, n_dims) array")

    centered = features - features.mean(axis=0, keepdims=True)

    # Top right-singular vector of the centered feature matrix — the
    # dominant direction of variance, which a backdoor trigger cluster
    # distorts disproportionately.
    _, _, vt = np.linalg.svd(centered, full_matrices=False)
    top_singular_vector = vt[0]

    # Outlier score: squared correlation with the top singular direction.
    scores = (centered @ top_singular_vector) ** 2

    n_flag = max(1, int(len(scores) * removal_fraction))
    flagged = np.argsort(scores)[-n_flag:].tolist()
    threshold = float(np.sort(scores)[-n_flag])

    return SpectralSignatureResult(outlier_scores=scores, flagged_indices=flagged, threshold=threshold)


def loss_based_outliers(per_sample_loss: np.ndarray, z_threshold: float = 3.0) -> List[int]:
    """
    Complementary, cheaper signal: poisoned/mislabeled samples often sit
    at the tail of the per-sample training loss distribution (a clean
    model fits them poorly because their label doesn't match their
    content). Flags samples more than `z_threshold` standard deviations
    above the mean loss.
    """
    mean, std = per_sample_loss.mean(), per_sample_loss.std()
    if std == 0:
        return []
    z_scores = (per_sample_loss - mean) / std
    return np.where(z_scores > z_threshold)[0].tolist()
