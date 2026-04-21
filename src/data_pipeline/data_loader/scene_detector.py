import os
import sys
import json
import torch
from pathlib import Path
from typing import List, Dict, Any

class SceneDetector:
    """Phát hiện scene boundaries bằng TransNetV2 hoặc fallback."""
    
    def __init__(self, output_root: str = "artifacts/data_extraction/SceneJSON"):
        self.output_root = Path(output_root)
        self.output_root.mkdir(parents=True, exist_ok=True)
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model = None

    def _load_model(self):
        """Lazy load TransNetV2 model."""
        if self.model is None:
            print(f"🧠 Đang load model TransNetV2 trên {self.device}...")
            
            # Lấy path từ environment
            transnet_path = os.getenv("TRANSNET_V2_PATH")
            if transnet_path:
                pytorch_inference_path = Path(transnet_path) / "inference-pytorch"
                if pytorch_inference_path.exists():
                    sys.path.append(str(pytorch_inference_path))
                    print(f"✅ Đã thêm {pytorch_inference_path} vào sys.path")
            
            try:
                # Thử import từ pytorch version
                from transnetv2_pytorch import TransNetV2
                self.model = TransNetV2()
                
                # Load weights nếu cần (giả định default hoặc cần path cụ thể)
                # Pytorch version thường cần check point path
                # self.model.load_state_dict(torch.load(checkpoint_path))
                
                if self.device == "cuda":
                    self.model.cuda()
            except ImportError as e:
                print(f"⚠️ Không tìm thấy package transnetv2 hoặc lỗi import: {e}")
                print("Sử dụng mô phỏng (cần cài đặt transnetv2).")
                self.model = "fallback"

    def detect_scenes(self, video_path: str) -> List[List[int]]:
        """
        Detect scene boundaries cho 1 video.
        Return: List các cặp [start_frame, end_frame]
        """
        self._load_model()
        
        # Logic thực tế của TransNetV2 sẽ ở đây
        # Vì đây là code tích hợp, tôi giả định transnetv2 được sử dụng qua CLI hoặc API
        # Nếu transnetv2 chưa cài, chúng ta có thể dùng OpenCV Simple Threshold làm fallback
        
        if self.model == "fallback":
            return self._simple_opencv_detection(video_path)
            
        # Giả định model.predict_video trả về (single_frame_predictions, all_frame_predictions)
        # và convert sang scenes
        # return model.predictions_to_scenes(single_frame_predictions)
        return []

    def _simple_opencv_detection(self, video_path: str) -> List[List[int]]:
        """Fallback đơn giản dùng OpenCV: Cắt mỗi 60 giây nếu không có AI model."""
        import cv2
        cap = cv2.VideoCapture(video_path)
        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration = frame_count / fps
        
        interval_sec = 60 # Cắt mỗi phút cho test
        interval_frames = int(interval_sec * fps)
        
        scenes = []
        for start in range(0, frame_count, interval_frames):
            end = min(start + interval_frames, frame_count)
            scenes.append([start, end])
            
        cap.release()
        return scenes

    def process_playlist(self, video_dir: str, folder_name: str) -> Dict[str, Any]:
        """Process tất cả video mp4 trong thư mục."""
        video_dir = Path(video_dir)
        output_dir = self.output_root / folder_name
        output_dir.mkdir(parents=True, exist_ok=True)
        
        video_files = list(video_dir.glob("*.mp4"))
        results = {"processed": 0, "skipped": 0}

        for v_path in video_files:
            video_id = v_path.stem # Dùng tên file làm ID tạm thời
            out_json = output_dir / f"{video_id}.json"
            
            if out_json.exists():
                results["skipped"] += 1
                continue
                
            print(f"🎬 Detect scenes cho: {v_path.name}")
            scenes = self.detect_scenes(str(v_path))
            
            with open(out_json, "w", encoding="utf-8") as f:
                json.dump(scenes, f)
            results["processed"] += 1
            
        return results
