"""
AICG — machine unlearning engine, layer 3 (GDPR / "right to erasure" compliance).

Extends the NegGrad approach from the original blueprint with two things
a production deployment actually needs:

1. Gradient clipping and interleaved (not block-sequential) forget/retain
   steps. Naive "just negate the loss and ascend" on the forget set alone
   for a full epoch is a known failure mode — unbounded ascent can diverge
   and destroy general model utility, not just the targeted memorization.
   Interleaving a retain-set step after every forget-set batch keeps the
   model anchored while it forgets.

2. Verifiable before/after metrics. "We ran the unlearning procedure" is
   not something a compliance audit accepts — it needs numbers: forget-set
   accuracy should drop toward chance, retain-set accuracy should barely
   move. This controller returns both, so the audit log has evidence, not
   just a log line saying it happened.
"""
from dataclasses import dataclass

import torch
import torch.nn as nn
import torch.optim as optim


@dataclass
class UnlearningReport:
    forget_accuracy_before: float
    forget_accuracy_after: float
    retain_accuracy_before: float
    retain_accuracy_after: float
    epochs_run: int

    @property
    def retain_accuracy_delta(self) -> float:
        return self.retain_accuracy_after - self.retain_accuracy_before

    @property
    def looks_successful(self) -> bool:
        """A rough automated pass/fail signal for the audit log — a human
        reviewer should still sign off, this just flags obviously-bad runs
        (e.g. retain accuracy collapsed, meaning the model was damaged
        rather than surgically edited)."""
        retain_preserved = self.retain_accuracy_delta > -0.05  # allow <5pt drop
        forget_reduced = self.forget_accuracy_after < self.forget_accuracy_before
        return retain_preserved and forget_reduced


class UnlearningController:
    """Executes a targeted forget operation against a subset of training
    data without a full model retrain."""

    def __init__(self, model: nn.Module, lr: float = 0.005, max_grad_norm: float = 1.0):
        self.model = model
        self.criterion = nn.CrossEntropyLoss()
        self.optimizer = optim.SGD(self.model.parameters(), lr=lr)
        self.max_grad_norm = max_grad_norm

    @torch.no_grad()
    def _accuracy(self, loader) -> float:
        self.model.eval()
        correct, total = 0, 0
        for inputs, targets in loader:
            outputs = self.model(inputs)
            preds = outputs.argmax(dim=1)
            correct += (preds == targets).sum().item()
            total += targets.size(0)
        return correct / total if total else 0.0

    def execute_targeted_forget(
        self,
        forget_loader: torch.utils.data.DataLoader,
        retain_loader: torch.utils.data.DataLoader,
        epochs: int = 2,
    ) -> UnlearningReport:
        forget_acc_before = self._accuracy(forget_loader)
        retain_acc_before = self._accuracy(retain_loader)

        self.model.train()
        retain_iter = iter(retain_loader)

        for _epoch in range(epochs):
            for inputs, targets in forget_loader:
                # Step A: ascend the loss on the forget batch (push the
                # model away from confidently predicting these labels).
                self.optimizer.zero_grad()
                outputs = self.model(inputs)
                forget_loss = -self.criterion(outputs, targets)
                forget_loss.backward()
                torch.nn.utils.clip_grad_norm_(self.model.parameters(), self.max_grad_norm)
                self.optimizer.step()

                # Step B: immediately re-anchor on a retain batch, so the
                # model doesn't drift on everything else while forgetting
                # this one thing. Interleaved per-batch, not saved for
                # the end of the epoch — that's what keeps this stable.
                try:
                    retain_inputs, retain_targets = next(retain_iter)
                except StopIteration:
                    retain_iter = iter(retain_loader)
                    retain_inputs, retain_targets = next(retain_iter)

                self.optimizer.zero_grad()
                retain_outputs = self.model(retain_inputs)
                retain_loss = self.criterion(retain_outputs, retain_targets)
                retain_loss.backward()
                torch.nn.utils.clip_grad_norm_(self.model.parameters(), self.max_grad_norm)
                self.optimizer.step()

        forget_acc_after = self._accuracy(forget_loader)
        retain_acc_after = self._accuracy(retain_loader)

        return UnlearningReport(
            forget_accuracy_before=forget_acc_before,
            forget_accuracy_after=forget_acc_after,
            retain_accuracy_before=retain_acc_before,
            retain_accuracy_after=retain_acc_after,
            epochs_run=epochs,
        )
