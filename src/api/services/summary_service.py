"""
Service tóm tắt video bằng LLM (GPT-4o-mini).
Thay thế _extractive_summary bằng tóm tắt có cấu trúc, cache in-memory theo video_id.
"""
import logging
from pathlib import Path
from typing import Dict
from functools import lru_cache

from langchain_core.messages import HumanMessage

from src.generation.llm_model import get_llm
from src.shared.config import get_path

logger = logging.getLogger(__name__)

# Cache in-memory: video_id -> summary text (sống trong suốt vòng đời process)
# Upgrade: thay bằng Redis khi deploy production với nhiều workers
_summary_cache: Dict[str, str] = {}

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


@lru_cache(maxsize=1)
def _build_transcript_index() -> Dict[str, str]:
    """Map video_id -> đường dẫn transcript từ artifacts/data. Tái dùng logic từ chat_service."""
    data_root = Path(get_path("data_dir"))
    index: Dict[str, str] = {}
    if not data_root.exists() or not data_root.is_dir():
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
                # Ưu tiên processed_transcripts nếu cùng video_id
                if video_id not in index or sub_dir_name == "processed_transcripts":
                    index[video_id] = str(transcript_file)

    return index


def _trim_transcript(text: str, max_chars: int = 24000) -> str:
    """Cắt transcript dài: lấy đầu + cuối để bao quát mở đầu và kết luận."""
    if len(text) <= max_chars:
        return text
    half = max_chars // 2
    return text[:half] + "\n\n[...]\n\n" + text[-half:]


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


async def _call_llm_summary(transcript_text: str) -> str:
    """Gọi GPT-4o-mini để tóm tắt transcript có cấu trúc."""
    llm = get_llm()
    trimmed = _trim_transcript(transcript_text)
    prompt = SUMMARY_PROMPT.format(transcript_text=trimmed)
    try:
        response = await llm.ainvoke([HumanMessage(content=prompt)])
        return response.content.strip()
    except Exception as e:
        logger.error(f"LLM summary error: {e}")
        return (
            "## ⚠️ Tóm tắt không khả dụng\n\n"
            "Không thể tạo tóm tắt lúc này. Vui lòng thử lại sau."
        )


async def summarize_with_llm(video_id: str) -> Dict[str, str]:
    """
    Entry point: tóm tắt video theo video_id.
    - Cache HIT: trả về ngay, không gọi LLM.
    - Cache MISS: gọi GPT-4o-mini, lưu cache, trả về.
    """
    cleaned_id = (video_id or "").strip()
    if not cleaned_id:
        return {"video_id": "", "summary": "Thiếu video_id để tóm tắt."}

    # Cache hit
    if cleaned_id in _summary_cache:
        logger.info(f"Summary cache HIT cho video_id={cleaned_id}")
        return {"video_id": cleaned_id, "summary": _summary_cache[cleaned_id]}

    # Load transcript
    transcript_text = _load_transcript(cleaned_id)
    if not transcript_text.strip():
        return {
            "video_id": cleaned_id,
            "summary": "Không tìm thấy transcript cho video này. Vui lòng chọn video khác.",
        }

    # Gọi LLM
    logger.info(f"Summary cache MISS — gọi LLM cho video_id={cleaned_id}")
    summary = await _call_llm_summary(transcript_text)

    # Lưu cache
    _summary_cache[cleaned_id] = summary
    return {"video_id": cleaned_id, "summary": summary}
