"""
Service tóm tắt video bằng LLM (GPT-4o-mini).
Refactored cho backend structure mới, sẵn sàng cho Redis cache.
"""
import logging
from pathlib import Path
from typing import Dict, Optional
import os

from langchain_core.messages import HumanMessage

from src.generation.llm_model import get_llm
from backend.app.core.config import settings

logger = logging.getLogger(__name__)

# Cache in-memory (Dự phòng cho Redis)
_summary_cache_local: Dict[str, str] = {}

SUMMARY_PROMPT = """\
Bạn là trợ lý giáo dục chuyên tóm tắt bài giảng video.
Hãy đọc transcript sau và tạo tóm tắt theo đúng cấu trúc bên dưới.
QUAN TRỌNG: Chỉ dùng thông tin có trong transcript, không tự thêm thông tin bên ngoài.

Transcript:
{transcript_text}

Trả về đúng cấu trúc Markdown sau (dùng ## cho heading, - cho bullet, **bold** cho term chính, tối đa 600 từ):

## 🎯 Mục tiêu bài giảng
[1-2 câu mô tả bài học muốn đạt được gì]

## 📚 Các khái niệm chính
- **[Khái niệm 1]**: [Giải thích ngắn, 1 câu]
- **[Khái niệm 2]**: [Giải thích ngắn, 1 câu]
- **[Khái niệm 3]**: [Giải thích ngắn, 1 câu]

## ✅ Kết luận
[2-3 câu tóm tắt điểm mấu chốt học viên cần nhớ]

## 💬 Gợi ý câu hỏi thảo luận
- [Câu hỏi 1]
- [Câu hỏi 2]
- [Câu hỏi 3]\
"""


def _build_transcript_index() -> Dict[str, str]:
    """Map video_id -> đường dẫn transcript từ artifacts/data."""
    # Lấy path từ ENV hoặc default
    data_dir = os.getenv("PUQ_DATA_DIR", "artifacts/data")
    data_root = Path(data_dir)
    index: Dict[str, str] = {}
    
    if not data_root.exists() or not data_root.is_dir():
        logger.warning(f"Data root không tồn tại: {data_root}")
        return index

    for course_dir in data_root.iterdir():
        if not course_dir.is_dir():
            continue
        for sub_dir_name in ("processed_transcripts", "transcripts"):
            transcript_dir = course_dir / sub_dir_name
            if not transcript_dir.exists() or not transcript_dir.is_dir():
                continue
            for transcript_file in transcript_dir.glob("*.txt"):
                video_id = transcript_file.stem
                if video_id not in index or sub_dir_name == "processed_transcripts":
                    index[video_id] = str(transcript_file)
    return index


def _load_transcript(video_id: str) -> str:
    """Đọc transcript text từ artifacts/data theo video_id."""
    transcript_map = _build_transcript_index()
    transcript_path = transcript_map.get(video_id)
    if not transcript_path:
        return ""
    try:
        return Path(transcript_path).read_text(encoding="utf-8", errors="ignore")
    except Exception as e:
        logger.warning(f"Không đọc được transcript cho video_id={video_id}: {e}")
        return ""


async def summarize_video(video_id: str, redis_client=None) -> Dict[str, str]:
    """
    Entry point: tóm tắt video theo video_id.
    - Hỗ trợ Redis cache (HIT/MISS).
    """
    video_id = video_id.strip()
    if not video_id:
        return {"video_id": "", "summary": "Thiếu video_id."}

    # 1. Kiểm tra Cache (Redis -> Local)
    cache_key = f"summary:{video_id}"
    if redis_client:
        cached = redis_client.get(cache_key)
        if cached:
            logger.info(f"Summary cache HIT (Redis) cho {video_id}")
            return {"video_id": video_id, "summary": cached.decode("utf-8") if isinstance(cached, bytes) else cached}
    
    if video_id in _summary_cache_local:
        logger.info(f"Summary cache HIT (Local) cho {video_id}")
        return {"video_id": video_id, "summary": _summary_cache_local[video_id]}

    # 2. Load Transcript
    transcript_text = _load_transcript(video_id)
    if not transcript_text:
        return {"video_id": video_id, "summary": "Không tìm thấy transcript."}

    # 3. Gọi LLM
    llm = get_llm()
    # Trim transcript nếu quá dài (bcrypt limit 72 ko liên quan ở đây, nhưng LLM có context limit)
    trimmed = transcript_text[:24000] 
    prompt = SUMMARY_PROMPT.format(transcript_text=trimmed)
    
    try:
        response = await llm.ainvoke([HumanMessage(content=prompt)])
        summary = response.content.strip()
        
        # 4. Lưu Cache
        if redis_client:
            redis_client.setex(cache_key, 86400 * 7, summary) # Cache 7 ngày
        _summary_cache_local[video_id] = summary
        
        return {"video_id": video_id, "summary": summary}
    except Exception as e:
        logger.error(f"LLM summary error: {e}")
        return {"video_id": video_id, "summary": "Lỗi khi tạo tóm tắt."}
