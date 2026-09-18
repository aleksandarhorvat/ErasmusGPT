"""Bake every model into the image at build time. Run during `docker build`.

Reads the model list from app.core.config so it can never drift from the runtime.
After this runs, HF_HUB_OFFLINE=1 is set and nothing touches the network again.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from huggingface_hub import snapshot_download  # noqa: E402

from app.core.config import MODELS_TO_BAKE  # noqa: E402

IGNORE = ["*.onnx", "*.onnx_data", "openvino*", "*.h5", "*.msgpack", "*tf_model*"]


def main() -> int:
    for repo_id in MODELS_TO_BAKE:
        print(f"--> downloading {repo_id}", flush=True)
        path = snapshot_download(repo_id=repo_id, ignore_patterns=IGNORE)
        print(f"    cached at {path}", flush=True)
    print(f"done: {len(MODELS_TO_BAKE)} models baked into the image")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
