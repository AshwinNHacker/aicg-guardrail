"""
AICG — unlearning controller API.

Triggers a targeted forget operation on request (e.g. from a GDPR
erasure request logged in the compliance dashboard) and returns a report
with before/after metrics for the audit trail.

This is a scaffold endpoint: a real deployment loads a checkpointed
production model and real forget/retain DataLoaders built from the
specific records named in the erasure request, rather than the
synthetic data used here to keep the service runnable standalone.
"""
import torch
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from torch.utils.data import DataLoader, TensorDataset

from model import EnterpriseModelGuard
from unlearning import UnlearningController

app = FastAPI(title="aicg-unlearning-controller")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class ForgetRequest(BaseModel):
    request_id: str
    epochs: int = 2
    # In production: a list of record IDs to forget, resolved to actual
    # tensors by looking them up in the training data store. Kept out of
    # this scaffold's request shape since that lookup is deployment-specific.


def _build_demo_loaders():
    """Synthetic data standing in for real forget/retain sets, so this
    endpoint is runnable and testable standalone."""
    torch.manual_seed(0)
    input_dim, n_classes = 16, 4

    forget_x = torch.randn(32, input_dim)
    forget_y = torch.randint(0, n_classes, (32,))
    retain_x = torch.randn(200, input_dim)
    retain_y = torch.randint(0, n_classes, (200,))

    forget_loader = DataLoader(TensorDataset(forget_x, forget_y), batch_size=8)
    retain_loader = DataLoader(TensorDataset(retain_x, retain_y), batch_size=16)
    return forget_loader, retain_loader, input_dim, n_classes


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/forget")
def forget(req: ForgetRequest):
    forget_loader, retain_loader, input_dim, n_classes = _build_demo_loaders()
    model = EnterpriseModelGuard(input_dim=input_dim, hidden_dim=32, output_dim=n_classes)

    controller = UnlearningController(model)
    report = controller.execute_targeted_forget(forget_loader, retain_loader, epochs=req.epochs)

    return {
        "request_id": req.request_id,
        "forget_accuracy_before": report.forget_accuracy_before,
        "forget_accuracy_after": report.forget_accuracy_after,
        "retain_accuracy_before": report.retain_accuracy_before,
        "retain_accuracy_after": report.retain_accuracy_after,
        "retain_accuracy_delta": report.retain_accuracy_delta,
        "looks_successful": report.looks_successful,
    }
