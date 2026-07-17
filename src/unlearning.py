"""Machine unlearning engine — NegGrad-style targeted forget (GDPR / compliance)."""

from __future__ import annotations

from typing import Optional

import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader


class EnterpriseModelGuard(nn.Module):
    """Simulated production model representation for demo / unit tests."""

    def __init__(self, input_dim: int, hidden_dim: int, output_dim: int) -> None:
        super().__init__()
        self.network = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, output_dim),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.network(x)


class UnlearningController:
    """
    Localized Negative Gradient (NegGrad) step to reduce influence of a forget set
    without a full multi-million-dollar retrain cycle.
    """

    def __init__(self, model: nn.Module, lr: float = 0.005) -> None:
        self.model = model
        self.criterion = nn.CrossEntropyLoss()
        self.optimizer = optim.SGD(self.model.parameters(), lr=lr)

    def execute_targeted_forget(
        self,
        forget_loader: DataLoader,
        retain_loader: DataLoader,
        epochs: int = 2,
        max_retain_batches: Optional[int] = 4,
    ) -> dict:
        self.model.train()
        history = []

        for epoch in range(epochs):
            forget_loss_sum = 0.0
            forget_steps = 0

            for inputs, targets in forget_loader:
                self.optimizer.zero_grad()
                outputs = self.model(inputs)
                # Ascend loss on forget set (maximize loss → unlearn)
                loss = -self.criterion(outputs, targets)
                loss.backward()
                self.optimizer.step()
                forget_loss_sum += float(-loss.item())
                forget_steps += 1

            retain_loss_sum = 0.0
            retain_steps = 0
            for batch_idx, (inputs, targets) in enumerate(retain_loader):
                if max_retain_batches is not None and batch_idx >= max_retain_batches:
                    break
                self.optimizer.zero_grad()
                outputs = self.model(inputs)
                loss = self.criterion(outputs, targets)
                loss.backward()
                self.optimizer.step()
                retain_loss_sum += float(loss.item())
                retain_steps += 1

            history.append(
                {
                    "epoch": epoch + 1,
                    "forget_loss_mean": forget_loss_sum / max(forget_steps, 1),
                    "retain_loss_mean": retain_loss_sum / max(retain_steps, 1),
                }
            )

        return {
            "status": "complete",
            "epochs": epochs,
            "history": history,
        }
