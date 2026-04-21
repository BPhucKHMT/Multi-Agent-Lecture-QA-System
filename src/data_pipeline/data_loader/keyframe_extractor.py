import cv2
import os
import json
from pathlib import Path
from typing import List, Dict, Any

class KeyframeExtractor:
    """Extract keyframes từ video dựa trên scene boundaries."""
    
    def __init__(self, output_root: str = "artifacts/data_extraction/Keyframes"):
        self.output_root = Path(output_root)
        self.output_root.mkdir(parents=True, exist_ok=True)

    def sample_frames_from_shot(self, start_idx: int, end_idx: int) -> List[int]:
        """
        Adaptive sampling: Lấy frame ở giữa hoặc nhiều frame nếu shot dài.
        """
        length = end_idx - start_idx
        if length <= 0: return []
        
        # Công thức: Lấy frame ở mức 20%, 50%, 80% nếu shot > 60 frames (2s)
        if length > 90:
            return [
                start_idx + int(length * 0.2),
                start_idx + int(length * 0.5),
                start_idx + int(length * 0.8)
            ]
        else:
            return [start_idx + (length // 2)]

    def extract_keyframes(self, video_path: str, scenes: List[List[int]], 
                         output_dir: Path) -> int:
        """Extract keyframes cho 1 video."""
        output_dir.mkdir(parents=True, exist_ok=True)
        cap = cv2.VideoCapture(video_path)
        count = 0
        
        for scene in scenes:
            frames_to_save = self.sample_frames_from_shot(scene[0], scene[1])
            for f_idx in frames_to_save:
                cap.set(cv2.CAP_PROP_POS_FRAMES, f_idx)
                ret, frame = cap.read()
                if ret:
                    out_path = output_dir / f"{f_idx:06d}.webp"
                    # OpenCV imwrite has issues with Unicode paths on Windows
                    # Workaround: imencode then write to file
                    import numpy as np
                    ret_enc, buffer = cv2.imencode(".webp", frame, [cv2.IMWRITE_WEBP_QUALITY, 80])
                    if ret_enc:
                        with open(out_path, "wb") as f:
                            f.write(buffer)
                        count += 1
        
        cap.release()
        return count

    def process_playlist(self, video_dir: str, scene_root: str, folder_name: str) -> Dict[str, Any]:
        """Process playlist."""
        video_dir = Path(video_dir)
        scene_dir = Path(scene_root) / folder_name
        output_root = self.output_root / folder_name
        
        results = {"total_keyframes": 0, "processed_videos": 0}
        
        video_files = list(video_dir.glob("*.mp4"))
        for v_path in video_files:
            video_id = v_path.stem
            v_output_dir = output_root / video_id
            
            # Skip nếu folder đã có ảnh (đã xử lý)
            if v_output_dir.exists() and any(v_output_dir.iterdir()):
                continue
                
            scene_json = scene_dir / f"{video_id}.json"
            if not scene_json.exists():
                print(f"⚠️ Không tìm thấy scene JSON cho: {video_id}")
                continue
                
            with open(scene_json, "r") as f:
                scenes = json.load(f)
                
            print(f"🖼️ Đang trích xuất keyframes: {v_path.name}")
            num = self.extract_keyframes(str(v_path), scenes, v_output_dir)
            results["total_keyframes"] += num
            results["processed_videos"] += 1
            
        return results
