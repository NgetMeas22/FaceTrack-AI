"""Download the face models from the official OpenCV Model Zoo and verify their SHA-256.

    .\\.venv\\Scripts\\python.exe download_models.py

YuNet (face detection, MIT) and SFace (face embedding, Apache-2.0). About 39 MB in total.
"""

import hashlib
import sys
import urllib.request
from pathlib import Path

MODEL_DIR = Path(__file__).resolve().parent / "ml_models"
ZOO = "https://github.com/opencv/opencv_zoo/raw/main/models"
MODELS = {
    "face_detection_yunet_2023mar.onnx": (
        f"{ZOO}/face_detection_yunet/face_detection_yunet_2023mar.onnx",
        "8f2383e4dd3cfbb4553ea8718107fc0423210dc964f9f4280604804ed2552fa4",
    ),
    "face_recognition_sface_2021dec.onnx": (
        f"{ZOO}/face_recognition_sface/face_recognition_sface_2021dec.onnx",
        "0ba9fbfa01b5270c96627c4ef784da859931e02f04419c829e83484087c34e79",
    ),
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    for name, (url, expected) in MODELS.items():
        target = MODEL_DIR / name
        if target.exists() and sha256(target) == expected:
            print(f"ok       {name}")
            continue
        print(f"download {name} ...")
        tmp = target.with_suffix(".part")
        urllib.request.urlretrieve(url, tmp)
        actual = sha256(tmp)
        if actual != expected:
            tmp.unlink(missing_ok=True)
            print(f"ERROR: checksum mismatch for {name}\n  expected {expected}\n  got      {actual}", file=sys.stderr)
            return 1
        tmp.replace(target)
        print(f"ok       {name}")
    print(f"Models are in {MODEL_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
