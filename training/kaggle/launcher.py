"""Kaggle entry point: clone the repository, install Ultralytics and run the training.

The run itself is described by ``training/kaggle_run.json`` at the cloned commit, so every
run can be traced to a commit. Push this file as a Kaggle script with the TrackNet
dataset attached (see ``training/kaggle/kernel-metadata.json``); from the repository root:
``kaggle kernels push -p training/kaggle``.
"""

import json
import subprocess
import sys
from pathlib import Path

REPOSITORY = "https://github.com/stoppo22/tennis-analysis-system.git"
BRANCH = "v1.21-ball-training"
CHECKOUT = "/tmp/repo"  # outside /kaggle/working, which is returned as the run output


def find_dataset_root():
    """The directory that contains ``game1`` ... ``game10`` under /kaggle/input."""
    for path in sorted(Path("/kaggle/input").glob("**/game1")):
        if path.is_dir():
            return path.parent
    listing = subprocess.run(
        ["find", "/kaggle/input", "-maxdepth", "3"], capture_output=True, text=True
    ).stdout
    raise SystemExit(f"TrackNet frames not found under /kaggle/input:\n{listing[:2000]}")


subprocess.run(["git", "clone", "--depth", "1", "--branch", BRANCH, REPOSITORY, CHECKOUT], check=True)
subprocess.run([sys.executable, "-m", "pip", "install", "-q", "ultralytics==8.4.123"], check=True)
source = find_dataset_root()
print(f"dataset found at {source}", flush=True)
stage = json.loads((Path(CHECKOUT) / "training/kaggle_run.json").read_text()).get("stage")
if stage == "test":
    command = [
        sys.executable, "training/kaggle_test.py",
        "--config", "training/kaggle_run.json",
        "--source", str(source),
        "--weights-root", "/kaggle/input",
        "--work", "/kaggle/working",
    ]
else:
    command = [
        sys.executable, "training/kaggle_train.py",
        "--config", "training/kaggle_run.json",
        "--source", str(source),
        "--work", "/kaggle/working",
    ]
subprocess.run(command, check=True, cwd=CHECKOUT)
