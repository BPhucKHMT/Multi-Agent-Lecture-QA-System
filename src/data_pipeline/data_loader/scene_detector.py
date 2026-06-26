import os
import json
import importlib.util
import numpy as np
import cv2
from pathlib import Path
from typing import List, Dict, Any

class SceneDetector:
    """Phát hiện scene boundaries bằng TransNetV2 hoặc fallback."""

    def __init__(self, output_root: str = "artifacts/data_extraction/SceneJSON"):
        self.output_root = Path(output_root)
        self.output_root.mkdir(parents=True, exist_ok=True)
        self.model = None

    def _load_model(self):
        """Lazy load TransNetV2 model."""
        if self.model is not None:
            return

        print("🧠 Đang load model TransNetV2...")

        transnet_path = Path(os.getenv("TRANSNET_V2_PATH", "artifacts/data_extraction/TransNetV2"))
        if not transnet_path.exists():
            print(f"⚠️ Không tìm thấy TRANSNET_V2_PATH: {transnet_path}")
            self.model = "fallback"
            return

        tf_inference_path = transnet_path / "inference" / "transnetv2.py"
        tf_weights_path = transnet_path / "inference" / "transnetv2-weights"
        if not tf_inference_path.exists() or not tf_weights_path.exists():
            print(f"⚠️ Không tìm thấy TransNetV2 TensorFlow artifact trong {transnet_path}")
            print("   Sử dụng fallback OpenCV.")
            self.model = "fallback"
            return

        try:
            spec = importlib.util.spec_from_file_location("artifact_transnetv2", tf_inference_path)
            if spec is None or spec.loader is None:
                raise ImportError(f"Cannot import {tf_inference_path}")
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            self.model = module.TransNetV2(model_dir=str(tf_weights_path))
            print(f"✅ Đã load TransNetV2 TensorFlow từ {tf_weights_path}")
        except Exception as e:
            print(f"⚠️ Không load được TransNetV2 TensorFlow: {e}")
            print("   Sử dụng fallback OpenCV.")
            self.model = "fallback"

    def _extract_all_frames(self, video_path: str) -> np.ndarray:
        """Đọc toàn bộ frame video ở kích thước TransNetV2 yêu cầu."""
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise ValueError(f"Cannot open video: {video_path}")

        frames = []
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            frame = cv2.resize(frame, (48, 27))
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            frames.append(frame)

        cap.release()
        if not frames:
            raise ValueError("Video has no frames")
        return np.stack(frames, axis=0).astype(np.uint8)

    def detect_scenes(self, video_path: str) -> List[List[int]]:
        """
        Detect scene boundaries cho 1 video.
        Return: List các cặp [start_frame, end_frame]
        """
        self._load_model()

        if self.model == "fallback":
            return self._simple_opencv_detection(video_path)

        # TransNet V2 inference
        try:
            frames = self._extract_all_frames(video_path)
            single_frame_pred, _ = self.model.predict_frames(frames)
            return self.model.predictions_to_scenes(single_frame_pred).tolist()

        except Exception as e:
            print(f"❌ Lỗi khi chạy TransNet V2: {e}")
            import traceback
            traceback.print_exc()
            return self._simple_opencv_detection(video_path)

    def _simple_opencv_detection(self, video_path: str) -> List[List[int]]:
        """Fallback đơn giản dùng OpenCV: Cắt mỗi 60 giây nếu không có AI model."""
        cap = cv2.VideoCapture(video_path)
        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        cap.release()

        interval_sec = 60
        interval_frames = int(interval_sec * fps)

        scenes = []
        for start in range(0, frame_count, interval_frames):
            end = min(start + interval_frames - 1, frame_count - 1)
            scenes.append([start, end])
        return scenes

    def process_playlist(self, video_dir: str, folder_name: str) -> Dict[str, Any]:
        """Process tất cả video mp4 trong thư mục."""
        video_dir = Path(video_dir)
        output_dir = self.output_root / folder_name
        output_dir.mkdir(parents=True, exist_ok=True)

        video_files = list(video_dir.glob("*.mp4"))
        results = {"processed": 0, "skipped": 0}

        for v_path in video_files:
            video_id = v_path.stem
            out_json = output_dir / f"{video_id}.json"

            if out_json.exists():
                results["skipped"] += 1
                continue

            print(f"🎬 Detect scenes cho: {v_path.name}")
            try:
                scenes = self.detect_scenes(str(v_path))

                payload = {
                    "video_filename": v_path.name,
                    "total_scenes": len(scenes),
                    "scenes": scenes,
                }
                with open(out_json, "w", encoding="utf-8") as f:
                    json.dump(payload, f, ensure_ascii=False, indent=2)
                results["processed"] += 1
            except Exception as e:
                print(f"❌ Lỗi xử lý {v_path.name}: {e}")
                results["skipped"] += 1

        return results
