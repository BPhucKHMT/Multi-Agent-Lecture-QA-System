import os
import json
import re
from pathlib import Path
from difflib import SequenceMatcher
from typing import List, Dict, Any, Optional

# Constants
SIMILARITY_THRESHOLD = 0.85
MIN_OCR_LENGTH = 2
NOISE_PATTERNS = [
    "Trường Đại học Công nghệ Thông tin",
    "ĐHQG-HCM",
    "đhqg-hcm",
    "HCMCity University of Technology",
    "VNU-HCM",
]

def timestamp_to_seconds(ts: str) -> float:
    """Chuyển 'H:MM:SS' hoặc 'MM:SS' hoặc 'H:MM:SS.ms' sang seconds."""
    if not ts:
        return 0.0
    try:
        parts = ts.split(':')
        if len(parts) == 3:
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])
        elif len(parts) == 2:
            return int(parts[0]) * 60 + float(parts[1])
        return float(ts)
    except (ValueError, TypeError):
        return 0.0

def clean_ocr_text(text: str) -> str:
    """Loại bỏ noise patterns, normalize và fix lỗi marker."""
    if not text:
        return ""
    
    # 1. Loại bỏ các noise patterns (watermark, footer)
    for pattern in NOISE_PATTERNS:
        text = re.sub(re.escape(pattern), "", text, flags=re.IGNORECASE)
    
    # 2. Normalize whitespace
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    
    # 3. Filter dòng quá ngắn (thường là rác OCR)
    filtered_lines = [l for l in lines if len(l) > 2]
    
    return '\n'.join(filtered_lines)

def is_subset_or_similar(text1: str, text2: str) -> bool:
    """
    Kiểm tra xem text2 có phải là bản mở rộng (subset) của text1 
    hoặc cực kỳ giống nhau không.
    """
    if text1 in text2:
        return True
    
    ratio = SequenceMatcher(None, text1, text2).ratio()
    return ratio >= SIMILARITY_THRESHOLD

def dedup_ocr_frames(frames: List[Dict[str, Any]]) -> List[str]:
    """
    Dedup các OCR frames đã sort theo timestamp.
    Chiến thuật: Ưu điểm cho frame sau nếu nó bao hàm frame trước (animation slide).
    """
    if not frames:
        return []

    processed_frames = []
    for f in frames:
        t = f.get("text", "")
        t = clean_ocr_text(t)
        if len(t) >= MIN_OCR_LENGTH:
            processed_frames.append(t)
            
    if not processed_frames:
        return []

    unique_texts = []
    last_kept = ""

    for current in processed_frames:
        if not last_kept:
            unique_texts.append(current)
            last_kept = current
            continue

        if is_subset_or_similar(last_kept, current):
            unique_texts[-1] = current
            last_kept = current
        elif is_subset_or_similar(current, last_kept):
            continue
        else:
            unique_texts.append(current)
            last_kept = current

    return unique_texts

class ContentCombiner:
    """Lớp điều phối việc gộp OCR vào transcript chunks."""

    def build_ocr_index(self, ocr_dir: str) -> Dict[str, List[Dict[str, Any]]]:
        """
        Đọc tất cả file OCR JSON trong thư mục và nhóm theo video_id.
        """
        ocr_index = {}
        ocr_path = Path(ocr_dir)
        
        if not ocr_path.exists():
            return {}

        for json_file in ocr_path.glob("*.json"):
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    frames = json.load(f)
                    
                # video_id chính là tên file JSON
                v_id = json_file.stem
                
                # Biến đổi frames về format chuẩn (text, timestamp_s)
                normalized_frames = []
                for fr in frames:
                    txt = fr.get("text") or fr.get("ocr_text", "")
                    ts = fr.get("timestamp_s")
                    if ts is None:
                        ts = fr.get("timestamp_seconds", 0)
                    
                    normalized_frames.append({
                        "timestamp_s": float(ts),
                        "text": txt
                    })
                
                ocr_index[v_id] = normalized_frames
                    
            except Exception as e:
                print(f"ERROR: Lỗi đọc file OCR {json_file}: {e}")

        # Sort mỗi video_id list theo timestamp_s
        for v_id in ocr_index:
            ocr_index[v_id].sort(key=lambda x: x.get("timestamp_s", 0))
            
        return ocr_index

    def combine_for_playlist(self, folder_name: str, ocr_dir: str, chunks_file: str) -> int:
        """Gộp OCR vào transcript chunks cho 1 playlist."""
        chunks_path = Path(chunks_file)
        if not chunks_path.exists():
            print(f"❌ Không thấy file chunks: {chunks_file}")
            return 0

        print(f"📦 Đang gộp nội dung OCR cho: {folder_name}")
        
        ocr_index = self.build_ocr_index(ocr_dir)
        if not ocr_index:
            print(f"⚠️ Không tìm thấy dữ liệu OCR tại: {ocr_dir}")
            return 0

        # Load metadata mapping if available
        meta_path = Path("artifacts/data") / folder_name / "metadata.json"
        video_mapping = {}
        if meta_path.exists():
            try:
                with open(meta_path, 'r', encoding='utf-8') as f:
                    meta = json.load(f)
                    for v in meta.get("videos", []):
                        video_mapping[v["video_id"]] = v["title"]
            except Exception as e:
                print(f"⚠️ Lỗi đọc metadata mapping: {e}")

        with open(chunks_path, 'r', encoding='utf-8') as f:
            chunks = json.load(f)

        enriched_count = 0
        
        # Utility để normalize title (bỏ dấu)
        import unicodedata
        def norm_title(s):
            if not s: return ""
            s = unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode('utf-8')
            return re.sub(r'[^\w]', '', s).lower()

        for chunk in chunks:
            metadata = chunk.get("metadata", {})
            v_id = metadata.get("filename") # video_id
            
            # Patch video_id nếu nó chứa path hoặc extension
            if v_id: v_id = Path(v_id).stem
            
            # Tìm ocr_frames tương ứng
            ocr_frames = None
            if v_id in ocr_index:
                ocr_frames = ocr_index[v_id]
            else:
                # Tìm theo title từ mapping
                v_title = video_mapping.get(v_id)
                if v_title:
                    v_title_norm = norm_title(v_title)
                    # Tìm key trong ocr_index có chứa title hoặc tương tự
                    for ocr_key in ocr_index:
                        ocr_key_norm = norm_title(ocr_key)
                        if v_title_norm == ocr_key_norm or v_title_norm in ocr_key_norm or ocr_key_norm in v_title_norm:
                            ocr_frames = ocr_index[ocr_key]
                            break
            
            if not ocr_frames:
                continue
                
            start_sec = timestamp_to_seconds(metadata.get("start_timestamp"))
            end_sec = timestamp_to_seconds(metadata.get("end_timestamp"))
            
            relevant_frames = [
                f for f in ocr_frames
                if start_sec <= f.get("timestamp_s", 0) <= end_sec
            ]
            
            if relevant_frames:
                unique_texts = dedup_ocr_frames(relevant_frames)
                if unique_texts:
                    chunk["metadata"]["ocr_content"] = "\n---\n".join(unique_texts)
                    enriched_count += 1

        if enriched_count > 0:
            with open(chunks_path, 'w', encoding='utf-8') as f:
                json.dump(chunks, f, ensure_ascii=False, indent=4)
                
        print(f"SUCCESS: Đã gộp thành công {enriched_count}/{len(chunks)} chunks cho {folder_name}")
        return enriched_count
