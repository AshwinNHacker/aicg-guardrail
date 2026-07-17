"""End-to-end CLI demo: attest → (optional) poison → gate → unlearn."""

from __future__ import annotations

import argparse

import torch
from torch.utils.data import DataLoader, TensorDataset

from src.attestation import DataAttestationPipeline, IngestionGate
from src.poison_detect import flag_documents
from src.unlearning import EnterpriseModelGuard, UnlearningController


def make_chunks(n: int = 8) -> list[bytes]:
    return [f"enterprise_doc_{i:03d}::payload".encode("utf-8") for i in range(n)]


def run_attestation(poison: bool) -> None:
    pipeline = DataAttestationPipeline()
    gate = IngestionGate(pipeline)
    chunks = make_chunks()

    signed_root = pipeline.root_hash(chunks)
    print(f"[attest] signed root: {signed_root[:16]}…{signed_root[-8:]}")

    if poison:
        chunks[3] = chunks[3] + b"{{POISON_TOKEN::override_label=1}}"
        print("[attack] injected poison token into chunk[3]")

    decision = gate.evaluate(chunks, signed_root)
    print(f"[gate] status={decision['status']} alert={decision['alert']}")
    if decision["status"] == "blocked":
        print(
            f"[gate] signed={decision['signed_root'][:12]}… "
            f"recomputed={decision['recomputed_root'][:12]}…"
        )


def run_unlearn() -> None:
    torch.manual_seed(0)
    model = EnterpriseModelGuard(input_dim=8, hidden_dim=16, output_dim=3)

    def loader(n: int, label: int) -> DataLoader:
        x = torch.randn(n, 8)
        y = torch.full((n,), label, dtype=torch.long)
        return DataLoader(TensorDataset(x, y), batch_size=4)

    controller = UnlearningController(model, lr=0.01)
    result = controller.execute_targeted_forget(
        forget_loader=loader(16, label=0),
        retain_loader=loader(32, label=1),
        epochs=2,
    )
    print(f"[unlearn] status={result['status']} epochs={result['epochs']}")
    for row in result["history"]:
        print(
            f"  epoch {row['epoch']}: "
            f"forget_loss={row['forget_loss_mean']:.4f} "
            f"retain_loss={row['retain_loss_mean']:.4f}"
        )


def run_poison_scan() -> None:
    docs = ["doc-a91f", "doc-clean", "doc-c02e"]
    vectors = [
        [0.1, 0.9, 0.05, 0.95, 0.0, 1.0],
        [0.4, 0.41, 0.42, 0.4, 0.39, 0.4],
        [0.2, 0.8, 0.1, 0.9, 0.05, 0.95],
    ]
    flags = flag_documents(docs, vectors, threshold=0.5)
    print(f"[detect] open flags: {len(flags)}")
    for f in flags:
        print(f"  {f.doc_id} score={f.score} signal={f.signal}")


def main() -> None:
    parser = argparse.ArgumentParser(description="AICG demo pipeline")
    parser.add_argument(
        "--poison",
        action="store_true",
        help="Mutate a chunk after signing (Merkle should fail)",
    )
    parser.add_argument(
        "--skip-unlearn",
        action="store_true",
        help="Skip NegGrad demo (no torch training step)",
    )
    args = parser.parse_args()

    print("=== AICG demo pipeline ===")
    run_attestation(poison=args.poison)
    run_poison_scan()
    if not args.skip_unlearn:
        run_unlearn()
    print("=== done ===")


if __name__ == "__main__":
    main()
