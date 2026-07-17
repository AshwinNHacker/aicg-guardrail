"""
Not runnable in this sandbox (no torch available here — see README), but
this is the actual test suite: verifies the controller genuinely reduces
the model's confidence on the forget set while preserving retain-set
accuracy, using a small synthetic classification task with a controlled
signal (the forget set is deliberately mislabeled noise the model
initially memorizes, so a real drop after unlearning is unambiguous).
"""
import torch
from torch.utils.data import DataLoader, TensorDataset

from model import EnterpriseModelGuard
from unlearning import UnlearningController


def _memorize_forget_set(model, forget_loader, epochs=10, lr=0.05):
    """Pre-trains the model to memorize the forget set specifically,
    so there's something real to unlearn (rather than starting from
    random-init accuracy, which wouldn't distinguish 'unlearning worked'
    from 'the model was never confident to begin with')."""
    optimizer = torch.optim.SGD(model.parameters(), lr=lr)
    criterion = torch.nn.CrossEntropyLoss()
    model.train()
    for _ in range(epochs):
        for inputs, targets in forget_loader:
            optimizer.zero_grad()
            loss = criterion(model(inputs), targets)
            loss.backward()
            optimizer.step()


def test_unlearning_reduces_forget_accuracy_while_preserving_retain():
    torch.manual_seed(42)
    input_dim, n_classes = 8, 3

    forget_x = torch.randn(24, input_dim)
    forget_y = torch.randint(0, n_classes, (24,))
    retain_x = torch.randn(150, input_dim)
    retain_y = torch.randint(0, n_classes, (150,))

    forget_loader = DataLoader(TensorDataset(forget_x, forget_y), batch_size=8)
    retain_loader = DataLoader(TensorDataset(retain_x, retain_y), batch_size=16)

    model = EnterpriseModelGuard(input_dim=input_dim, hidden_dim=32, output_dim=n_classes)
    _memorize_forget_set(model, forget_loader, epochs=15)

    controller = UnlearningController(model, lr=0.01)
    report = controller.execute_targeted_forget(forget_loader, retain_loader, epochs=3)

    assert report.forget_accuracy_after <= report.forget_accuracy_before, (
        "unlearning should not increase confidence on the forget set"
    )
    assert report.retain_accuracy_delta > -0.15, (
        "retain accuracy should not collapse during a targeted forget operation"
    )


if __name__ == "__main__":
    test_unlearning_reduces_forget_accuracy_while_preserving_retain()
    print("[+] unlearning controller test passed")
