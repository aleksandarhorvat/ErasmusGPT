"""Bake every model into the image at build time. Run during `docker build`.

Reads the model list from app.core.config so it can never drift from the runtime.
After this runs, HF_HUB_OFFLINE=1 is set and nothing touches the network again.

Prints the size of each model, because the project has a budget: nothing over ~200 MB
on its own, under 400 MB in total (AGENTS.md). Exits non-zero if that is broken, so the
build fails instead of the image quietly doubling in size.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from huggingface_hub import HfApi, snapshot_download  # noqa: E402

from app.core.config import MODELS_TO_BAKE  # noqa: E402

# Weights for runtimes we do not ship: ONNX, OpenVINO, TensorFlow, Flax, Rust.
IGNORE = ["*.onnx", "*.onnx_data", "openvino*", "*.h5", "*.msgpack", "*tf_model*", "*.ot"]
# Most repositories ship the same weights twice, as .bin and as .safetensors. Downloading
# both doubles the model's footprint for nothing: bge-small is 268 MB that way and 134 MB
# with one copy. torch loads either, so keep safetensors where the repository has it.
DUPLICATE_WEIGHTS = ["*.bin", "*.pt", "*.pth", "*.ckpt"]

PER_MODEL_BUDGET_MB = 200
TOTAL_BUDGET_MB = 400


def ignore_patterns_for(repo_id: str) -> list[str]:
    files = HfApi().list_repo_files(repo_id)
    if any(name.endswith(".safetensors") for name in files):
        return IGNORE + DUPLICATE_WEIGHTS
    return IGNORE


def size_mb(path: Path) -> float:
    return sum(f.stat().st_size for f in path.rglob("*") if f.is_file()) / 1e6


def main() -> int:
    total = 0.0
    oversized = []
    for repo_id in MODELS_TO_BAKE:
        print(f"--> downloading {repo_id}", flush=True)
        path = Path(snapshot_download(repo_id=repo_id,
                                      ignore_patterns=ignore_patterns_for(repo_id)))
        megabytes = size_mb(path)
        total += megabytes
        print(f"    cached at {path} ({megabytes:.0f} MB)", flush=True)
        if megabytes > PER_MODEL_BUDGET_MB:
            oversized.append(f"{repo_id} is {megabytes:.0f} MB, over {PER_MODEL_BUDGET_MB} MB")

    print(f"done: {len(MODELS_TO_BAKE)} models, {total:.0f} MB in total")
    if total > TOTAL_BUDGET_MB:
        oversized.append(f"total is {total:.0f} MB, over {TOTAL_BUDGET_MB} MB")
    for problem in oversized:
        print(f"OVER BUDGET: {problem}", file=sys.stderr)
    return 1 if oversized else 0


if __name__ == "__main__":
    raise SystemExit(main())
