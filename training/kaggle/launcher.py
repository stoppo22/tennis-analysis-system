"""Kaggle entry point: clone the repository, install Ultralytics and run the training.

The run itself is described by ``training/kaggle_run.json`` at the cloned commit, so every
run can be traced to a commit. Push this file as a Kaggle script with the TrackNet
dataset attached (see ``training/kaggle/kernel-metadata.json``; push with ``kaggle kernels push -p training/kaggle``).
"""

import subprocess
import sys

REPOSITORY = "https://github.com/stoppo22/tennis-analysis-system.git"
BRANCH = "v1.21-ball-training"

subprocess.run(["git", "clone", "--depth", "1", "--branch", BRANCH, REPOSITORY, "repo"], check=True)
subprocess.run([sys.executable, "-m", "pip", "install", "-q", "ultralytics==8.4.123"], check=True)
subprocess.run(
    [
        sys.executable,
        "training/kaggle_train.py",
        "--config", "training/kaggle_run.json",
        "--source", "/kaggle/input/tracknet-tennis/Dataset",
        "--work", "/kaggle/working",
    ],
    check=True,
    cwd="repo",
)
