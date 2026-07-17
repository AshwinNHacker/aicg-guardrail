import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
from detector import compute_spectral_signatures, loss_based_outliers


def test_clean_features_flag_roughly_removal_fraction():
    rng = np.random.default_rng(0)
    features = rng.normal(0, 1, size=(200, 32))

    result = compute_spectral_signatures(features, removal_fraction=0.05)
    assert len(result.flagged_indices) == 10  # 5% of 200


def test_injected_trigger_cluster_is_detected():
    """The actual adversarial scenario: a small cluster of poisoned
    samples sharing a synthetic 'backdoor trigger' — a consistent offset
    in feature space, which is what a real trigger pattern produces in a
    trained model's activations — should score as outliers."""
    rng = np.random.default_rng(1)
    n_clean, n_poisoned, dims = 190, 10, 32

    clean_features = rng.normal(0, 1, size=(n_clean, dims))

    # Poisoned samples cluster tightly around a shared offset vector —
    # the signature a backdoor trigger leaves in feature space.
    trigger_direction = np.zeros(dims)
    trigger_direction[0] = 8.0
    poisoned_features = trigger_direction + rng.normal(0, 0.3, size=(n_poisoned, dims))

    all_features = np.vstack([clean_features, poisoned_features])
    poisoned_indices = set(range(n_clean, n_clean + n_poisoned))

    result = compute_spectral_signatures(all_features, removal_fraction=0.05)  # flags top 10

    overlap = poisoned_indices & set(result.flagged_indices)
    detection_rate = len(overlap) / n_poisoned

    assert detection_rate >= 0.8, f"expected to catch most injected poison, caught {detection_rate:.0%}"


def test_loss_based_outliers_catches_mislabeled_samples():
    rng = np.random.default_rng(2)
    normal_losses = rng.normal(0.5, 0.1, size=95)
    # Mislabeled/poisoned samples the model fits poorly -> high loss tail.
    poisoned_losses = rng.normal(5.0, 0.2, size=5)

    losses = np.concatenate([normal_losses, poisoned_losses])
    flagged = loss_based_outliers(losses, z_threshold=3.0)

    poisoned_indices = set(range(95, 100))
    overlap = poisoned_indices & set(flagged)
    assert len(overlap) == 5, "all high-loss poisoned samples should be flagged"


if __name__ == "__main__":
    test_clean_features_flag_roughly_removal_fraction()
    test_injected_trigger_cluster_is_detected()
    test_loss_based_outliers_catches_mislabeled_samples()
    print("[+] all poisoning detector tests passed")
