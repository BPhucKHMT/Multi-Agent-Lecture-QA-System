import os
import json
import torch
import re
from pathlib import Path
from typing import List, Dict, Any
from .llm_utils import correct_ocr_text

class OCRProcessor:
    """OCR keyframes bằng EasyOCR + advanced cleaning."""
    
    def __init__(self, output_root: str = "artifacts/data_extraction/OCR/ocr_output_final", use_llm: bool = True):
        self.output_root = Path(output_root)
        self.output_root.mkdir(parents=True, exist_ok=True)
        self.reader = None
        self.use_llm = use_llm
        self.device = "cuda" if torch.cuda.is_available() else "cpu"

    def _load_reader(self):
        if self.reader is None:
            print(f"🔍 Đang khởi tạo EasyOCR trên {self.device}...")
            import easyocr
            # Mặc định dùng ['vi'] theo snippet thành công của user
            self.reader = easyocr.Reader(['vi'], gpu=(self.device == "cuda"))

    def clean_ocr_text(self, text: str) -> str:
        """Dọn dẹp text OCR."""
        # Loại bỏ các ký tự rác, giữ lại các ký tự Unicode tiếng Việt
        text = re.sub(r'[^\w\sÀ-ỹ.,?!:/-]', ' ', text, flags=re.UNICODE)
        # Loại bỏ nhiều khoảng trắng
        text = re.sub(r'\s+', ' ', text).strip()
        
        # Rule dọn dẹp cụ thể (UI noise)
        noise_patterns = [
            r"Trường Đại học Công nghệ Thông tin",
            r"ĐHQG-HCM",
            r"Website: .*",
            r"Email: .*"
        ]
        for p in noise_patterns:
            text = re.sub(p, "", text, flags=re.IGNORECASE)
            
        return text.strip()

    def process_image(self, img_path: str) -> str:
        """OCR một ảnh."""
        self._load_reader()
        # OCR with Unicode path support
        import numpy as np
        import cv2
        with open(img_path, "rb") as f:
            img_array = np.frombuffer(f.read(), np.uint8)
            img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
        
        if img is not None:
            results = self.reader.readtext(img)
        else:
            results = []
        texts = [res[1] for res in results if res[2] > 0.4]
        full_text = " ".join(texts)
        cleaned_text = self.clean_ocr_text(full_text)
        
        if self.use_llm and len(cleaned_text) > 5:
            print(f"   ✨ Đang làm đẹp văn bản OCR bằng LLM...")
            corrected_val = correct_ocr_text(cleaned_text)
            if corrected_val:
                corrected_str = str(corrected_val).strip()
                if len(corrected_str) > 2:
                    return corrected_str
            
        return cleaned_text

    def process_playlist(self, keyframe_root: str, folder_name: str, video_info: Dict[str, Any]) -> Dict[str, Any]:
        """Process playlist."""
        keyframe_dir = Path(keyframe_root) / folder_name
        output_dir = self.output_root / folder_name
        output_dir.mkdir(parents=True, exist_ok=True)
        
        results = {"total_ocr_files": 0, "processed_videos": 0}
        
        # Duyệt qua từng folder video ID
        for v_folder in keyframe_dir.iterdir():
            if not v_folder.is_dir(): continue
            
            video_id = v_folder.name
            out_json = output_dir / f"{video_id}.json"
            
            if out_json.exists():
                continue
                
            print(f"📖 Đang OCR video: {video_id}")
            ocr_data = []
            # Tìm tất cả định dạng ảnh phổ biến
            img_files = []
            for ext in ("*.webp", "*.jpg", "*.png", "*.jpeg"):
                img_files.extend(list(v_folder.glob(ext)))
            img_files = sorted(img_files)
            
            # Lấy FPS để tính timestamp
            # Cần map video_id với video_name trong video_info.json
            v_info = None
            for v_name, info in video_info.items():
                if video_id in v_name:
                    v_info = info
                    break
            
            fps = v_info["fps"] if v_info else 30.0 # fallback
            
            for img in img_files:
                try:
                    frame_idx = int(img.stem)
                except ValueError:
                    frame_idx = 0
                    
                text = self.process_image(str(img))
                if len(text) >= 2: # Giảm ngưỡng tối thiểu để không bỏ lỡ từ ngắn (ví dụ: Vũ Liz)
                    timestamp_sec = frame_idx / fps
                    ocr_data.append({
                        "frame_idx": frame_idx,
                        "timestamp": self._format_timestamp(timestamp_sec),
                        "timestamp_s": timestamp_sec,
                        "text": text
                    })
            
            with open(out_json, "w", encoding="utf-8") as f:
                json.dump(ocr_data, f, indent=2, ensure_ascii=False)
            
            results["total_ocr_files"] += 1
            results["processed_videos"] += 1
            
        return results

    def _format_timestamp(self, seconds: float) -> str:
        td = int(seconds)
        m, s = divmod(td, 60)
        h, m = divmod(m, 60)
        return f"{h:02d}:{m:02d}:{s:02d}"
