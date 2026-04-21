"""
File: preprocess.py
Chức năng:
- Duyệt qua tất cả transcript trong data/<playlist>/transcripts/
- Phát hiện file transcript bị lỗi (rỗng, ký tự lạ, hallucination, lặp, language switching, timestamp)
- Sửa chính tả bằng Gemini API (free)
- Refetch lại transcript bị lỗi bằng Whisper (thử nhiều model)
- Lưu TẤT CẢ file đã xử lý vào data/<playlist>/processed_transcripts/
- GIỮ NGUYÊN file gốc trong transcripts/

Cách dùng:
    python -m data_loader.preprocess                    # Kiểm tra tất cả
    python -m data_loader.preprocess --force-refetch    # Refetch file lỗi
    python -m data_loader.preprocess --playlist <n>  # Chỉ xử lý 1 playlist
"""

from __future__ import annotations
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
import json
import argparse
import re
import os
from dotenv import load_dotenv

try:
    import google.generativeai as genai
except ImportError:
    print("⚠️ Cần cài đặt: pip install google-generativeai")
    genai = None

from .youtube_fetchers import (
    TranscriptWhisperFetcher,
    normalize_whisper_segments,
    segments_to_txt_with_timestamp,
    save_json,
)
from .llm_utils import correct_transcript_spelling

# =====================================================================
# Đường dẫn
# =====================================================================
ROOT_DIR = Path(__file__).resolve().parents[3]
DATA_ROOT = ROOT_DIR / "data"

# Load env
load_dotenv()


# =====================================================================
# TranscriptValidator - Phát hiện lỗi (IMPROVED)
# =====================================================================
class TranscriptValidator:
    """Phát hiện transcript bị lỗi - Version nâng cao"""

    @staticmethod
    def is_corrupted(text: str) -> Tuple[bool, str]:
        """
        Kiểm tra transcript có bị lỗi không
        Returns: (is_corrupted: bool, reason: str)
        """
        if not text or len(text.strip()) < 50:
            return True, "empty_or_too_short"

        # Tỷ lệ ký tự lạ
        weird_chars = sum(
            1 for c in text if not c.isalnum() and c not in " .,!?-\n'\"()[]:"
        )
        if len(text) > 0 and weird_chars / len(text) > 0.3:
            return True, "too_many_weird_chars"

        # 1. Phát hiện hallucination của Whisper
        hallucination_patterns = [
            "thank you for watching",
            "subscribe to my channel",
            "like and subscribe",
            "cảm ơn các bạn đã xem",
            "đăng ký kênh",
            "nhấn like",
            "nhấn subscribe",
            "don't forget to subscribe",
            "thanks for watching",
        ]
        text_lower = text.lower()
        repeated_count = sum(text_lower.count(p) for p in hallucination_patterns)
        if repeated_count > 5:
            return True, "whisper_hallucination"

        # 2. Phát hiện lặp lại câu/đoạn (Repetition)
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        if len(lines) > 5:
            # Kiểm tra câu lặp liên tiếp
            consecutive_repeats = 0
            for i in range(len(lines) - 1):
                # Lấy phần text (bỏ timestamp)
                text1 = re.sub(r"^\d+:\d+:\d+ - \d+:\d+:\d+,\s*", "", lines[i])
                text2 = re.sub(r"^\d+:\d+:\d+ - \d+:\d+:\d+,\s*", "", lines[i + 1])

                if text1 == text2:
                    consecutive_repeats += 1
                    if consecutive_repeats >= 3:  # 3 câu giống nhau liên tiếp
                        return True, "excessive_line_repetition"
                else:
                    consecutive_repeats = 0

        # 3. Phát hiện lặp từ quá nhiều
        words = text.split()
        if len(words) > 10:
            unique_ratio = len(set(words)) / len(words)
            if unique_ratio < 0.1:  # Quá 90% từ lặp lại
                return True, "excessive_word_repetition"

        # 4. Phát hiện language switching (chuyển ngôn ngữ đột ngột)
        # Đếm tỷ lệ chữ Latin vs chữ Việt
        latin_chars = sum(1 for c in text if c.isalpha() and ord(c) < 128)
        vietnamese_chars = sum(1 for c in text if c.isalpha() and ord(c) >= 128)
        total_chars = latin_chars + vietnamese_chars

        if total_chars > 100:
            # Nếu >80% là Latin → có thể bị dịch sang tiếng Anh
            if latin_chars / total_chars > 0.8:
                # Kiểm tra có phải tiếng Anh thật không (có nhiều từ tiếng Anh phổ biến)
                english_words = [
                    "the",
                    "and",
                    "is",
                    "are",
                    "was",
                    "were",
                    "have",
                    "has",
                    "will",
                    "can",
                ]
                english_count = sum(1 for word in english_words if word in text_lower)
                if english_count >= 5:
                    return True, "language_switched_to_english"

        # 5. Kiểm tra timestamp không liên tục
        timestamp_pattern = r"(\d+):(\d+):(\d+) - (\d+):(\d+):(\d+)"
        timestamps = re.findall(timestamp_pattern, text)

        if len(timestamps) > 2:
            gaps = []
            for i in range(len(timestamps) - 1):
                # End time của dòng hiện tại
                h1, m1, s1 = (
                    int(timestamps[i][3]),
                    int(timestamps[i][4]),
                    int(timestamps[i][5]),
                )
                end_time1 = h1 * 3600 + m1 * 60 + s1

                # Start time của dòng tiếp theo
                h2, m2, s2 = (
                    int(timestamps[i + 1][0]),
                    int(timestamps[i + 1][1]),
                    int(timestamps[i + 1][2]),
                )
                start_time2 = h2 * 3600 + m2 * 60 + s2

                gap = start_time2 - end_time1
                gaps.append(gap)

            # Nếu có khoảng cách >60s giữa các dòng → có vấn đề
            if any(gap > 60 for gap in gaps):
                return True, "timestamp_discontinuous"

        return False, "ok"


# =====================================================================
# LLMSpellChecker - Sửa chính tả bằng LLM
# =====================================================================
class LLMSpellChecker:
    """Sửa chính tả bằng LLM."""

    def __init__(self):
        print("✅ LLM spell checker đã sẵn sàng")

    def correct_text(self, text: str, language: str = "vi") -> Optional[str]:
        """Sửa chính tả theo từng batch để tránh bị LLM cắt cụt văn bản."""
        if not text: return text
        
        lines = text.split('\n')
        batch_size = 20 # Sửa 20 dòng một lần
        corrected_lines = []
        
        print(f"   (Batching: {len(lines)} dòng -> {len(lines)//batch_size + 1} đợt)")
        
        for i in range(0, len(lines), batch_size):
            batch = "\n".join(lines[i:i + batch_size])
            if not batch.strip(): continue
            
            corrected_batch = correct_transcript_spelling(batch)
            if corrected_batch:
                corrected_lines.append(corrected_batch)
            else:
                # Nếu API lỗi, lấy lại bản gốc của batch đó để không mất dữ liệu
                corrected_lines.append(batch)
                
        return "\n".join(corrected_lines)


# =====================================================================
# TranscriptPreprocessor - Main
# =====================================================================
class TranscriptPreprocessor:
    """Module preprocess chính"""

    def __init__(self, use_llm: bool = True):
        self.validator = TranscriptValidator()

        if use_llm:
            self.spell_checker = LLMSpellChecker()
        else:
            self.spell_checker = None

        self.whisper_fetcher = None

    def process_all_playlists(self, force_refetch: bool = False):
        """Duyệt tất cả playlist trong data/"""
        if not DATA_ROOT.exists():
            print(f"⚠️ Không tìm thấy thư mục data: {DATA_ROOT}")
            return

        for playlist_folder in DATA_ROOT.iterdir():
            if not playlist_folder.is_dir():
                continue
            if playlist_folder.name in ["logs"]:
                continue

            print(f"\n{'=' * 70}")
            print(f"📂 Playlist: {playlist_folder.name}")
            print(f"{'=' * 70}")
            self.process_playlist(playlist_folder, force_refetch)

    def process_playlist(self, playlist_folder: Path, force_refetch: bool = False):
        """Xử lý một playlist"""
        transcripts_dir = playlist_folder / "transcripts"
        if not transcripts_dir.exists():
            print(f"⏭️ Không có thư mục transcripts, bỏ qua")
            return

        # Tạo thư mục processed_transcripts
        processed_dir = playlist_folder / "processed_transcripts"
        processed_dir.mkdir(exist_ok=True)
        print(f"📁 Output folder: {processed_dir.resolve()}\n")

        # Load metadata để lấy video titles và index
        metadata_file = playlist_folder / "metadata.json"
        video_info = {}  # {video_id: {"title": ..., "index": ...}}
        if metadata_file.exists():
            try:
                metadata = json.loads(metadata_file.read_text(encoding="utf-8"))
                for idx, video in enumerate(metadata.get("videos", []), start=1):
                    video_info[video["video_id"]] = {
                        "title": video.get("title", "Unknown"),
                        "index": idx,
                    }
            except Exception as e:
                print(f"⚠️ Không đọc được metadata: {e}")

        audio_dir = playlist_folder / "audio"
        corrupted_log = playlist_folder / "corrupted_transcripts.json"
        corrupted_data = []

        txt_files = list(transcripts_dir.glob("*.txt"))
        if not txt_files:
            print("⏭️ Không có file transcript nào")
            return

        print(f"📊 Tìm thấy {len(txt_files)} transcript\n")

        processed_count = 0
        skipped_count = 0

        for txt_file in txt_files:
            video_id = txt_file.stem
            info = video_info.get(video_id, {"title": "Unknown", "index": "?"})

            print(f"\n{'─' * 70}")
            print(f"🔍 Video #{info['index']}: {info['title']}")
            print(f"📄 Source: {txt_file.resolve()}")

            # Đọc transcript gốc
            try:
                text = txt_file.read_text(encoding="utf-8")
            except Exception as e:
                print(f"❌ Không đọc được file: {e}")
                skipped_count += 1
                continue

            # skip nếu đã qua rồi
            output_file = processed_dir / f"{video_id}.txt"

            if output_file.exists() and not force_refetch:
                print(f"⏭️ Đã xử lý trước đó, bỏ qua")
                skipped_count += 1
                continue

            # 1. Kiểm tra lỗi
            is_corrupted, reason = self.validator.is_corrupted(text)

            if is_corrupted:
                print(f"❌ File bị lỗi: {reason}")
                corrupted_data.append(
                    {
                        "video_id": video_id,
                        "video_index": info["index"],
                        "title": info["title"],
                        "reason": reason,
                        "source_path": str(txt_file.relative_to(DATA_ROOT)),
                    }
                )

                if force_refetch:
                    print(f"🔄 Refetching transcript...")
                    refetched_text = self._refetch_transcript(video_id, audio_dir)

                    if refetched_text:
                        # Lưu vào processed
                        output_file = processed_dir / f"{video_id}.txt"
                        output_file.write_text(refetched_text, encoding="utf-8")
                        print(f"💾 Saved: {output_file.resolve()}")
                        processed_count += 1
                    else:
                        print(f"⚠️ Không thể refetch, bỏ qua file này")
                        skipped_count += 1
                else:
                    print(f"⚠️ Dùng --force-refetch để tự động refetch")
                    skipped_count += 1
                continue

            # 2. File OK - Sửa chính tả (nếu có Gemini)
            print(f"✅ File OK")
            final_text = text

            if self.spell_checker:
                print(f"✏️ Đang sửa chính tả với LLM...")
                corrected = self.spell_checker.correct_text(text)

                if corrected:
                    # Validate lại sau khi sửa
                    is_corrupted_after, reason_after = self.validator.is_corrupted(
                        corrected
                    )

                    if is_corrupted_after:
                        print(f"⚠️ Gemini sửa bị lỗi ({reason_after}), dùng bản gốc")
                        final_text = text
                    else:
                        if corrected != text:
                            print(f"✅ Đã sửa chính tả")
                        else:
                            print(f"⏭️ Không cần sửa")
                        final_text = corrected
                else:
                    print(f"⚠️ LLM lỗi, dùng bản gốc")
                    final_text = text
            else:
                print(f"⏭️ Bỏ qua sửa chính tả (không có Gemini API key)")

            # 3. Lưu vào processed_transcripts
            output_file = processed_dir / f"{video_id}.txt"
            output_file.write_text(final_text, encoding="utf-8")
            print(f"💾 Saved: {output_file.resolve()}")
            processed_count += 1

        # Lưu log file lỗi
        if corrupted_data:
            save_json({"corrupted_files": corrupted_data}, corrupted_log)
            print(f"\n📋 Đã lưu danh sách file lỗi: {corrupted_log.resolve()}")
            print(f"   Tổng file lỗi: {len(corrupted_data)}")

        # Summary
        print(f"\n{'=' * 70}")
        print(f"📊 SUMMARY:")
        print(f"   ✅ Processed: {processed_count}")
        print(f"   ⏭️ Skipped: {skipped_count}")
        print(f"   ❌ Corrupted: {len(corrupted_data)}")
        print(f"{'=' * 70}")

    def _refetch_transcript(self, video_id: str, audio_dir: Path) -> Optional[str]:
        """
        Refetch transcript bằng Whisper
        Thử nhiều model sizes nếu model hiện tại thất bại
        Returns: transcript text hoặc None
        """
        # Model sizes để thử (từ nhỏ đến lớn)
        model_sizes = ["base", "small", "medium", "large"]

        try:
            # Thử từng model size
            for model_size in model_sizes:
                print(f"   🔄 Thử Whisper model '{model_size}'...")

                try:
                    # Tạo fetcher mới với model size khác
                    fetcher = TranscriptWhisperFetcher(
                        audio_dir=str(audio_dir), model_size=model_size
                    )

                    # Fetch
                    whisper_data = fetcher.fetch_transcript_from(
                        video_id,
                        cleanup=False,  # Không xóa audio để thử model khác
                        show_segments=False,
                    )

                    if not whisper_data or not whisper_data.get("segments"):
                        print(f"   ⚠️ Model '{model_size}' không trả về segments")
                        continue

                    # Normalize
                    segments = normalize_whisper_segments(whisper_data["segments"])
                    txt = segments_to_txt_with_timestamp(segments)

                    # Kiểm tra kết quả có bị lỗi không
                    is_corrupted, reason = self.validator.is_corrupted(txt)

                    if is_corrupted:
                        print(f"   ⚠️ Model '{model_size}' vẫn bị lỗi: {reason}")
                        continue

                    # OK - cleanup audio và return
                    print(f"   ✅ Thành công với model '{model_size}'!")
                    self._cleanup_audio(video_id, audio_dir)
                    return txt

                except Exception as e:
                    print(f"   ❌ Lỗi với model '{model_size}': {e}")
                    continue

            # Nếu tất cả model đều thất bại
            print(f"   ❌ Tất cả Whisper models đều thất bại")
            self._cleanup_audio(video_id, audio_dir)
            return None

        except Exception as e:
            print(f"   ❌ Lỗi refetch: {e}")
            self._cleanup_audio(video_id, audio_dir)
            return None

    def _cleanup_audio(self, video_id: str, audio_dir: Path):
        """Xóa file audio tạm"""
        try:
            audio_file = audio_dir / f"{video_id}.wav"
            if audio_file.exists():
                audio_file.unlink()
                print(f"   🧹 Đã xóa audio tạm")
        except Exception as e:
            print(f"   ⚠️ Không xóa được audio: {e}")


# =====================================================================
# CLI
# =====================================================================
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Transcript Preprocessor - Version 2.0",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ví dụ:
  # Xử lý tất cả playlist (chỉ validate + sửa chính tả)
  python -m data_loader.preprocess
  
  # Xử lý tất cả + refetch file lỗi
  python -m data_loader.preprocess --force-refetch
  
  # Xử lý 1 playlist cụ thể
  python -m data_loader.preprocess --playlist "cs431-cac-ki-thuat-hoc-sau-va-ung-dung"
        """,
    )

    parser.add_argument(
        "--force-refetch",
        action="store_true",
        help="Tự động refetch transcript bị lỗi bằng Whisper",
    )

    parser.add_argument(
        "--playlist", type=str, help="Chỉ xử lý một playlist cụ thể (folder name)"
    )

    parser.add_argument(
        "--api-key",
        type=str,
        help="Gemini API key (hoặc set GEMINI_API_KEY trong .env)",
    )

    args = parser.parse_args()

    preprocessor = TranscriptPreprocessor(use_llm=True)

    if args.playlist:
        # Xử lý 1 playlist
        playlist_folder = DATA_ROOT / args.playlist
        if not playlist_folder.exists():
            print(f"❌ Không tìm thấy playlist: {args.playlist}")
        else:
            preprocessor.process_playlist(playlist_folder, args.force_refetch)
    else:
        # Xử lý tất cả
        preprocessor.process_all_playlists(args.force_refetch)
