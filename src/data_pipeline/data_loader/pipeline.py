"""
File: pipeline.py
Chức năng: Pipeline end-to-end tự động
    1. Transcript Flow: Crawl -> Preprocess -> Chunk
    2. Visual Flow: Download -> Scene -> Keyframe -> OCR
    3. Merge & Index: Combine -> Index Vector DB

Cách dùng:
    python -m src.data_pipeline.data_loader.pipeline 
    python -m src.data_pipeline.data_loader.pipeline --skip-visual
    python -m src.data_pipeline.data_loader.pipeline --playlist "cs315-may-hoc-nang-cao"
"""

from __future__ import annotations
import argparse
import sys
import os
import json
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

try:
    from src.data_pipeline.data_loader.coordinator import DataCoordinator, extract_playlist_id, PlaylistMetadataFetch
    from src.data_pipeline.data_loader.preprocess import TranscriptPreprocessor
    from src.data_pipeline.data_loader.video_downloader import VideoDownloader
    from src.data_pipeline.data_loader.scene_detector import SceneDetector
    from src.data_pipeline.data_loader.keyframe_extractor import KeyframeExtractor
    from src.data_pipeline.data_loader.ocr_processor import OCRProcessor
    from src.data_pipeline.combine_content import ContentCombiner
    from src.data_pipeline.data_loader.pipeline_state import PipelineState
    from src.data_pipeline.data_loader.utils import load_config, get_playlist_paths, slugify
    from src.data_pipeline.data_loader.file_loader import Loader
    from src.storage.vectorstore import VectorDB
    from src.shared.config import get_path
except ImportError as e:
    print(f"[ERROR] Lôi import module: {e}")
    sys.exit(1)

class DataPipeline:
    """Pipeline tự động cho Transcript và Visual."""
    
    def __init__(self, no_backup: bool = False):
        self.gpt_key = os.getenv("myAPIKey")
        self.gemini_key = os.getenv("googleAPIKey") # Fix: rule mentioned googleAPIKey
        self.state = PipelineState()
        self.no_backup = no_backup
        self._vector_db = None

    @property
    def vector_db(self):
        if self._vector_db is None:
            self._vector_db = VectorDB().db
        return self._vector_db

    def step1_crawl(self, playlist_url: str) -> str:
        """Crawl transcript & metadata. Trả về folder_name."""
        print("\n📥 BƯỚC 1: CRAWL TRANSCRIPTS")
        coord = DataCoordinator()
        # Trích xuất folder name trước khi crawl để map
        pid = extract_playlist_id(playlist_url)
        meta = PlaylistMetadataFetch(pid)
        meta.convert_to_json_data() # Kích hoạt việc fetch metadata
        folder_name = meta.playlist_name
        
        if not folder_name:
            # Fallback if playlist_name is still None
            folder_name = slugify(meta.title) if hasattr(meta, 'title') and meta.title else pid

        coord.process_playlist(playlist_url)
        self.state.set_status(pid, "crawl", "done", folder_name=folder_name)
        return folder_name

    def step2_preprocess(self, folder_name: str, force: bool = False):
        """Dọn dẹp transcript."""
        print("\n🔧 BƯỚC 2: PREPROCESS TRANSCRIPTS")
        preprocessor = TranscriptPreprocessor(use_llm=True)
        data_dir = Path(get_path("data_dir")) / folder_name
        preprocessor.process_playlist(data_dir, force_refetch=force)
        self.state.set_status(folder_name, "preprocess", "done")

    def step3_chunk(self, folder_name: str):
        """Tạo semantic chunks."""
        print("\n✂️ BƯỚC 3: SEMANTIC CHUNKING")
        paths = get_playlist_paths(folder_name)
        if not self.no_backup:
            self.state.backup("step3_chunk", folder_name, [paths["chunks_file"]])
            
        loader = Loader(open_api_key=self.gpt_key, vector_db=self.vector_db)
        
        # Gọi trực tiếp các hàm xử lý lõi để tránh lỗi đường dẫn của load_dir
        transcript_path = Path(paths["data_dir"]) / "processed_transcripts"
        txt_files = list(transcript_path.glob("*.txt"))
        
        # Lấy danh sách các file đã được index trong DB để bỏ qua
        try:
            filename_already_chunked = loader.get_filename_already_chunks(chroma_db=self.vector_db)
            print(f"[{folder_name}] Đã tìm thấy {len(filename_already_chunked)} file trong DB.")
        except Exception as e:
            print(f"⚠️ Không thể kiểm tra DB, sẽ xử lý lại tất cả: {e}")
            filename_already_chunked = set()

        # Lọc ra các file chưa có trong DB
        txt_files_to_process = [
            f for f in txt_files 
            if f.stem not in filename_already_chunked
        ]
        
        if not txt_files_to_process:
            print(f"✅ Tất cả {len(txt_files)} file của playlist '{folder_name}' đã được index. Bỏ qua bước Chunking.")
            return

        print(f"[{folder_name}] Cần xử lý mới: {len(txt_files_to_process)}/{len(txt_files)} file")

        # Load và Chunk các file mới
        docs = loader.load([str(f) for f in txt_files_to_process], paths["metadata_file"], workers=2)
        print(f"[{folder_name}] Đang chunk {len(docs)} documents...")
        loader.chunker(docs, paths["chunks_dir"])
        
        self.state.set_status(folder_name, "chunk", "done")

    def step4_download(self, playlist_url: str, folder_name: str):
        """Download video."""
        print("\n🎥 BƯỚC 4: DOWNLOAD VIDEOS")
        downloader = VideoDownloader()
        downloader.download_playlist(playlist_url, folder_name)
        downloader.get_technical_data(folder_name)
        self.state.set_status(folder_name, "download", "done")

    def step5_visual_extract(self, folder_name: str):
        """Scene & Keyframe extraction."""
        print("\n🖼️ BƯỚC 5: SCENE & KEYFRAME EXTRACTION")
        paths = get_playlist_paths(folder_name)
        
        detector = SceneDetector()
        detector.process_playlist(paths["videos_dir"], folder_name)
        
        extractor = KeyframeExtractor()
        extractor.process_playlist(paths["videos_dir"], paths["scene_dir"].replace(folder_name, ""), folder_name)
        self.state.set_status(folder_name, "visual_extract", "done")

    def step6_ocr(self, folder_name: str):
        """OCR keyframes."""
        print("\n🔍 BƯỚC 6: OCR KEYFRAMES")
        paths = get_playlist_paths(folder_name)
        
        # Load video info for FPS
        info_path = Path(paths["videos_dir"]) / "video_info.json"
        video_info = {}
        if info_path.exists():
            with open(info_path, "r") as f:
                video_info = json.load(f)
                
        processor = OCRProcessor()
        processor.process_playlist(Path(paths["keyframes_dir"]).parent, folder_name, video_info)
        self.state.set_status(folder_name, "ocr", "done")

    def step7_combine(self, folder_name: str):
        """Gộp OCR vào Chunk."""
        print("\n🔗 BƯỚC 7: COMBINE CONTENT")
        paths = get_playlist_paths(folder_name)
        if not self.no_backup:
            self.state.backup("step7_combine", folder_name, [paths["chunks_file"]])
            
        combiner = ContentCombiner()
        combiner.combine_for_playlist(folder_name, paths["ocr_dir"], paths["chunks_file"])
        self.state.set_status(folder_name, "combine", "done")

    def step8_index(self, folder_name: str):
        """Index vào Vector DB."""
        print("\n🗄️ BƯỚC 8: INDEX TO VECTOR DB")
        paths = get_playlist_paths(folder_name)
        
        with open(paths["chunks_file"], "r", encoding="utf-8") as f:
            chunks_data = json.load(f)
            
        # Reconstruct Document objects for LangChain
        from langchain_core.documents import Document
        docs = []
        ids = []
        for c in chunks_data:
            meta = c["metadata"]
            docs.append(Document(page_content=c["page_content"], metadata=meta))
            # Tạo ID duy nhất từ filename và chunk_id để tránh trùng lặp khi re-index
            chunk_id = meta.get("chunk_id", "0")
            v_id = meta.get("filename", "unknown")
            ids.append(f"{v_id}_{chunk_id}")
            
        if docs:
            self.vector_db.add_documents(docs, ids=ids)
            print(f"✅ Đã index {len(docs)} chunks (với unique IDs)")
        self.state.set_status(folder_name, "index", "done")

    def run_playlist(self, url: str, skip_transcript=False, skip_visual=False, force_preprocess=False):
        """Chạy full pipeline cho 1 playlist."""
        # Step 1 luôn chạy để lấy folder_name
        folder_name = self.step1_crawl(url)
        
        if not skip_transcript:
            self.step2_preprocess(folder_name, force=force_preprocess)
            self.step3_chunk(folder_name)
            
        if not skip_visual:
            self.step4_download(url, folder_name)
            self.step5_visual_extract(folder_name)
            self.step6_ocr(folder_name)
            
        self.step7_combine(folder_name)
        self.step8_index(folder_name)

    def run_from_config(self, skip_transcript=False, skip_visual=False, force_preprocess=False):
        """Chạy pipeline cho tất cả playlist trong config.yaml."""
        config = load_config()
        playlists = config.get("playlists", [])
        enabled = [p for p in playlists if p.get("enabled", True)]
        
        if not enabled:
            print("⚠️ Không có playlist nào được enable trong config.yaml")
            return

        print(f"🚀 Bắt đầu xử lý {len(enabled)} playlists...")
        for p in enabled:
            try:
                self.run_playlist(p["url"], skip_transcript, skip_visual, force_preprocess)
            except Exception as e:
                print(f"❌ Lỗi khi xử lý {p['url']}: {e}")
                import traceback
                traceback.print_exc()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="End-to-End RAG Data Pipeline")
    parser.add_argument("--playlist", type=str, help="URL playlist YouTube cụ thể")
    parser.add_argument("--skip-transcript", action="store_true", help="Bỏ qua luồng transcript")
    parser.add_argument("--skip-visual", action="store_true", help="Bỏ qua luồng visual")
    parser.add_argument("--force-refetch", action="store_true", help="Force preprocess transcript")
    parser.add_argument("--no-backup", action="store_true", help="Bỏ qua bước backup")
    parser.add_argument("--status", action="store_true", help="Xem trạng thái pipeline")
    
    args = parser.parse_args()
    
    pipeline = DataPipeline(no_backup=args.no_backup)
    
    if args.status:
        pipeline.state.print_status()
    elif args.playlist:
        pipeline.run_playlist(args.playlist, skip_transcript=args.skip_transcript, 
                             skip_visual=args.skip_visual, force_preprocess=args.force_refetch)
    else:
        pipeline.run_from_config(skip_transcript=args.skip_transcript, 
                                skip_visual=args.skip_visual, force_preprocess=args.force_refetch)
