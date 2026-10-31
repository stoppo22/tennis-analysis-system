# Model assets and training

Large model weights and videos are intentionally excluded from Git. Place these
three files at the exact paths below before running the pipeline:

| Local path | Purpose | Source and status |
| --- | --- | --- |
| `yolo11l.pt` | Player detection | Official [Ultralytics YOLO11](https://docs.ultralytics.com/models/yolo11/) pretrained checkpoint. Ultralytics documents AGPL-3.0 and Enterprise licensing options. |
| `models/yolov11best.pt` | Tennis-ball detection | Project-specific fine-tuned checkpoint, available as a [`v1.0` release asset](https://github.com/stoppo22/tennis-analysis-system/releases/download/v1.0/yolov11best.pt). See its [model card](ball-detector-model-card.md) for training metadata, metrics, licence, and limitations. |
| `models/keypoints_model.pth` | Court keypoint prediction | Download the [pretrained court model linked by the tutorial author](https://drive.google.com/file/d/1QrTOF1ToQ4plsSZbkBs3zOLkVt3MBlta/view?usp=sharing) and rename it exactly. Its redistribution licence has not been verified, so the file is kept local. |

Download the official player detector through the pinned Ultralytics package:

```bash
python -c 'from ultralytics import YOLO; YOLO("yolo11l.pt")'
```

Download the project-specific ball detector into its expected local path:

```bash
curl -L https://github.com/stoppo22/tennis-analysis-system/releases/download/v1.0/yolov11best.pt \
  -o models/yolov11best.pt
```

Reference SHA-256 checksums for the exact local weights used during development
and evaluation are:

```text
9ebd0e09d59811db4b1d61e2bc6730649608b1ac47f8dd01e2da6bca7c20023f  yolo11l.pt
1f74aea3f7e84ccfbf61d0633d3f0d9713b20f2a7709771b8f9afa426a315d8c  models/yolov11best.pt
fe166be4ebc9ca6fa1278cea252028fd242ef20bc593554c5fa2d98d82799962  models/keypoints_model.pth
```

On macOS, verify them with:

```bash
shasum -a 256 yolo11l.pt models/yolov11best.pt models/keypoints_model.pth
```

## Recreating the ball checkpoint

The ball-training notebook uses version 6 of Viren Dhanwani's
[Tennis Ball Detection dataset](https://universe.roboflow.com/viren-dhanwani/tennis-ball-detection/dataset/6),
published under CC BY 4.0. Open
`training/tennis_ball_detector_training.ipynb`, train the YOLO11 model, and copy
the resulting `best.pt` checkpoint to `models/yolov11best.pt`. The exact local
checkpoint used by the project is documented in its
[model card](ball-detector-model-card.md).

The notebook reads the Roboflow private API key from the `ROBOFLOW_API_KEY`
environment variable. Set it in the environment that starts Jupyter; never paste
it into the notebook, commit it, or use the publishable InferenceJS key in its
place. Training is separate from normal runtime setup and can require
substantially more time and compute than running the pipeline.

The cleaned notebook has been syntax-checked and its dataset validation logic
has been reviewed, but the complete dataset download and 100-epoch training run
have not yet been repeated from a fresh environment.

## Recreating the court-keypoint checkpoint

The tutorial author also provides the court-keypoint training dataset used by
`training/tennis_key_point_detector_training.ipynb`. The notebook downloads it
into the ignored `training/local_data/` directory, validates the annotations,
trains a ResNet-50 regressor, and saves the resulting checkpoint at
`models/keypoints_model.pth`.

The dataset's redistribution licence has not been verified, so neither the
archive nor its extracted files are committed. The cleaned notebook has been
syntax-checked, and its dataset loader, model output shape, and one-epoch
training/validation flow have been smoke-tested with synthetic data. The full
dataset download and 20-epoch training run have not yet been repeated.
