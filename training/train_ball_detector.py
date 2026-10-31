"""Train a ball detector with a fixed recipe so that architectures can be compared.

Run it on a machine with a GPU (for example a Colab or Kaggle notebook) after
downloading the dataset with the training notebook; only the weights and the image
size vary between the compared runs.

    python training/train_ball_detector.py --weights yolo11l.pt --data <data.yaml> --name yolo11l_640
    python training/train_ball_detector.py --weights yolo26l.pt --data <data.yaml> --name yolo26l_640
    python training/train_ball_detector.py --weights yolo11l.pt --data <data.yaml> --imgsz 1280 --batch 8 --name yolo11l_1280

The recipe matches the notebook that produced the published checkpoint (100
epochs, batch 16, seed 0, deterministic). Different image sizes may need a smaller
batch; that change must be recorded with the results.
"""

import argparse
import hashlib
from pathlib import Path


def sha256(path):
    hasher = hashlib.sha256()
    with Path(path).open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--weights", required=True, help="Starting checkpoint, e.g. yolo11l.pt.")
    parser.add_argument("--data", required=True, help="Dataset data.yaml.")
    parser.add_argument("--name", required=True, help="Run name under runs/ball.")
    parser.add_argument("--epochs", type=int, default=100)
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--batch", type=int, default=16)
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args(argv)

    from ultralytics import YOLO  # imported here: heavy and optional
    import ultralytics

    model = YOLO(args.weights)
    model.train(
        data=args.data,
        epochs=args.epochs,
        imgsz=args.imgsz,
        batch=args.batch,
        seed=args.seed,
        deterministic=True,
        project="runs/ball",
        name=args.name,
    )

    best = Path(model.trainer.best)
    print(f"Ultralytics version: {ultralytics.__version__}")
    print(f"Best checkpoint: {best}")
    print(f"SHA-256: {sha256(best)}")


if __name__ == "__main__":
    main()
