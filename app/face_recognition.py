"""OpenCV DNN Face Detection (YuNet) and Recognition (SFace) Engine."""

import base64
import math
import os
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple

import cv2
import numpy as np

# Model constants
BASE_DIR = Path(__file__).resolve().parent.parent
MODEL_DIR = BASE_DIR / "ml_models"

YUNET_FILENAME = "face_detection_yunet_2023mar.onnx"
SFACE_FILENAME = "face_recognition_sface_2021dec.onnx"

# Typical SFace cosine similarity threshold is 0.363 on clean benchmarks; 0.30 provides optimal real-world webcam recall
DEFAULT_COSINE_THRESHOLD = 0.30
MIN_FACE_SIZE = 40  # Minimum face width/height in pixels


@dataclass
class FaceBox:
    x: int
    y: int
    width: int
    height: int
    confidence: float
    landmarks: List[Tuple[int, int]]

    def to_dict(self) -> dict:
        return {
            "x": self.x,
            "y": self.y,
            "width": self.width,
            "height": self.height,
            "confidence": round(self.confidence, 3),
            "landmarks": self.landmarks,
        }


class FaceEngine:
    """Thread-safe Face Recognition Engine using OpenCV YuNet & SFace ONNX models."""

    _instance: Optional["FaceEngine"] = None
    _lock = threading.Lock()

    def __init__(self, model_dir: Path = MODEL_DIR):
        self.model_dir = model_dir
        self.yunet_path = model_dir / YUNET_FILENAME
        self.sface_path = model_dir / SFACE_FILENAME
        self.detector = None
        self.recognizer = None
        self._init_models()

    def _init_models(self) -> None:
        """Load ONNX models into memory to bypass Windows path character limitations."""
        if not self.yunet_path.exists() or not self.sface_path.exists():
            print(f"[FaceEngine] WARNING: Models not found in {self.model_dir}. Run download script or check paths.")
            return

        try:
            # Read bytes to memory to avoid Windows non-ASCII / special character path bugs
            yunet_bytes = np.frombuffer(self.yunet_path.read_bytes(), dtype=np.uint8)
            sface_bytes = np.frombuffer(self.sface_path.read_bytes(), dtype=np.uint8)
            empty = np.empty(0, dtype=np.uint8)

            # YuNet Detector: input_size (320, 320), conf_threshold 0.6, nms_threshold 0.3, top_k 5000
            self.detector = cv2.FaceDetectorYN.create(
                "onnx", yunet_bytes, empty, (320, 320), 0.6, 0.3, 5000
            )

            # SFace Recognizer: 128-d feature extractor
            self.recognizer = cv2.FaceRecognizerSF.create("onnx", sface_bytes, empty)
            print("[FaceEngine] Successfully initialized YuNet & SFace models.")
        except Exception as e:
            print(f"[FaceEngine] Error loading models: {e}")

    @classmethod
    def get_instance(cls) -> "FaceEngine":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    @staticmethod
    def decode_image(image_data: str | bytes) -> Optional[np.ndarray]:
        """Convert base64 data-URL or raw bytes to OpenCV BGR numpy array."""
        try:
            if isinstance(image_data, str):
                if "," in image_data:
                    image_data = image_data.split(",", 1)[1]
                raw_bytes = base64.b64decode(image_data)
            else:
                raw_bytes = image_data

            nparr = np.frombuffer(raw_bytes, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            return img
        except Exception as e:
            print(f"[FaceEngine] Error decoding image: {e}")
            return None

    def assess_quality(self, img: np.ndarray, box: FaceBox) -> Tuple[float, str]:
        """Assess face image quality: blur (Laplacian), brightness, and resolution."""
        # 1. Size check
        if box.width < MIN_FACE_SIZE or box.height < MIN_FACE_SIZE:
            return 0.3, "Face too small / too far"

        # Crop face region
        h, w = img.shape[:2]
        x1 = max(0, box.x)
        y1 = max(0, box.y)
        x2 = min(w, box.x + box.width)
        y2 = min(h, box.y + box.height)

        if x2 <= x1 or y2 <= y1:
            return 0.2, "Invalid face boundary"

        face_roi = img[y1:y2, x1:x2]
        gray = cv2.cvtColor(face_roi, cv2.COLOR_BGR2GRAY)

        # 2. Blur assessment using Laplacian variance
        blur_score = cv2.Laplacian(gray, cv2.CV_64F).var()
        if blur_score < 40.0:
            return 0.4, "Image is blurry"

        # 3. Brightness assessment
        mean_brightness = float(np.mean(gray))
        if mean_brightness < 40:
            return 0.4, "Too dark, increase lighting"
        if mean_brightness > 220:
            return 0.4, "Too bright / overexposed"

        quality = min(1.0, (blur_score / 200.0) * 0.5 + 0.5)
        return round(quality, 2), "Good quality"

    def detect_faces(self, img: np.ndarray) -> List[Tuple[FaceBox, np.ndarray]]:
        """
        Detect all faces in the frame.
        Returns list of (FaceBox, raw_yunet_row).
        """
        if self.detector is None:
            return []

        h, w = img.shape[:2]
        # Resize dynamically for performance if image is huge
        max_dim = 1024
        scale = min(1.0, max_dim / max(h, w))
        if scale < 1.0:
            proc_img = cv2.resize(img, (int(w * scale), int(h * scale)))
        else:
            proc_img = img

        ph, pw = proc_img.shape[:2]

        with self._lock:
            self.detector.setInputSize((pw, ph))
            _, faces = self.detector.detect(proc_img)

        if faces is None:
            return []

        results = []
        for face_row in faces:
            # Rescale back to original image size
            coords = face_row[:14] / scale
            score = float(face_row[14])

            fx, fy, fw, fh = int(coords[0]), int(coords[1]), int(coords[2]), int(coords[3])
            # Filter border outliers
            if not (0 <= fx + fw / 2 < w and 0 <= fy + fh / 2 < h):
                continue

            landmarks = [
                (int(coords[4]), int(coords[5])),    # right eye
                (int(coords[6]), int(coords[7])),    # left eye
                (int(coords[8]), int(coords[9])),    # nose tip
                (int(coords[10]), int(coords[11])),  # right mouth corner
                (int(coords[12]), int(coords[13])),  # left mouth corner
            ]

            box = FaceBox(
                x=fx,
                y=fy,
                width=fw,
                height=fh,
                confidence=score,
                landmarks=landmarks,
            )
            # Ensure face_row coordinates match the original unscaled image for alignCrop
            rescaled_row = face_row.copy()
            rescaled_row[:14] = coords
            results.append((box, rescaled_row))

        return results

    def extract_embedding(self, img: np.ndarray, raw_face_row: np.ndarray) -> Optional[List[float]]:
        """Extract aligned 128-d face embedding from SFace."""
        if self.recognizer is None:
            return None

        try:
            with self._lock:
                # Align and crop face
                aligned_face = self.recognizer.alignCrop(img, raw_face_row)
                # Feature extraction
                feature = self.recognizer.feature(aligned_face)
            
            # Normalize embedding
            feature_norm = feature / np.linalg.norm(feature)
            return feature_norm.flatten().tolist()
        except Exception as e:
            print(f"[FaceEngine] Error extracting embedding: {e}")
            return None

    @staticmethod
    def cosine_similarity(vec_a: List[float], vec_b: List[float]) -> float:
        """Calculate cosine similarity between two 128-d vectors."""
        a = np.array(vec_a, dtype=np.float32)
        b = np.array(vec_b, dtype=np.float32)
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return float(np.dot(a, b) / (norm_a * norm_b))

    def match_against_gallery(
        self,
        query_embedding: List[float],
        gallery: List[Tuple[int, List[float]]],  # List of (employee_id, vector)
        threshold: float = DEFAULT_COSINE_THRESHOLD,
    ) -> Tuple[Optional[int], float]:
        """
        Compare query embedding against registered employee gallery.
        Returns (best_employee_id, best_score).
        """
        best_emp_id = None
        best_score = -1.0

        for emp_id, emb in gallery:
            score = self.cosine_similarity(query_embedding, emb)
            if score > best_score:
                best_score = score
                best_emp_id = emp_id

        if best_score >= threshold and best_emp_id is not None:
            return best_emp_id, round(best_score, 3)

        return None, round(max(0.0, best_score), 3)


# Singleton accessor
def get_face_engine() -> FaceEngine:
    return FaceEngine.get_instance()

