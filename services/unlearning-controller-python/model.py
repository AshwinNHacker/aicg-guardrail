"""AICG — target model representation for the unlearning controller."""
import torch.nn as nn


class EnterpriseModelGuard(nn.Module):
    """Stand-in for whatever production model this pipeline protects.
    Swap for a real model class (loaded from a checkpoint) in production —
    the unlearning controller only needs standard nn.Module semantics
    (forward pass, parameters(), state_dict())."""

    def __init__(self, input_dim: int, hidden_dim: int, output_dim: int):
        super().__init__()
        self.network = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, output_dim),
        )

    def forward(self, x):
        return self.network(x)
