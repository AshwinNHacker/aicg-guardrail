"""Lightweight anomaly / poison scoring helpers (demo-grade)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Sequence


@dataclass
class PoisonFlag:
    doc_id: str
    score: float
    signal: str
    layer: str


def spectral_score(vector: Sequence[float]) -> float:
    """
    Toy spectral-style score: energy of high-frequency differences.
    Replace with real spectral / influence estimators in production.
    """
    if len(vector) < 2:
        return 0.0
    diffs = [abs(vector[i] - vector[i - 1]) for i in range(1, len(vector))]
    energy = sum(d * d for d in diffs) / len(diffs)
    # squash into (0, 1)
    return min(1.0, energy / (1.0 + energy))


def flag_documents(
    doc_ids: List[str],
    vectors: List[Sequence[float]],
    threshold: float = 0.72,
) -> List[PoisonFlag]:
    flags: List[PoisonFlag] = []
    for doc_id, vec in zip(doc_ids, vectors):
        score = spectral_score(vec)
        if score >= threshold:
            flags.append(
                PoisonFlag(
                    doc_id=doc_id,
                    score=round(score, 4),
                    signal="Spectral spike",
                    layer="L2·demo",
                )
            )
    return flags
