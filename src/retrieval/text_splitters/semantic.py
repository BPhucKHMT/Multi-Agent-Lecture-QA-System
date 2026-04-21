import os
import json
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document
from typing import List

class TranscriptChunker:
    """Chunk văn bản bằng RecursiveCharacterTextSplitter (thay thế Semantic để tăng tốc)."""
    
    def __init__(self, open_api_key: str = None):
        # Recursive chunker - Rule based, very fast, no API required
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=700,        # kích thước chunk mong muốn
            chunk_overlap=100,      # overlap giữa các chunk
            separators=["\n\n", "\n", ". ", " ", ""]
        )

    def __call__(self, documents: List[dict], output_dir: str) -> List[dict]:
        all_chunks = []
        
        for item in documents:
            full_text = item["full_text"]
            position_map = item["position_map"]
            playlist = item["playlist"]
            filename = item["filename"]
            title = item["title"]
            url = item["url"]

            # chia chunk bằng recursive splitter
            # Chúng ta dùng split_text để lấy list các string
            text_chunks = self.splitter.split_text(full_text)

            current_pos = 0
            for i, chunk_text in enumerate(text_chunks):
                # Tìm start_index thực tế của chunk_text trong full_text
                # Lưu ý: split_text có thể làm mất dấu phân tách, nhưng find sẽ tìm chính xác
                start_index = full_text.find(chunk_text, current_pos)
                if start_index == -1:
                    # Fallback nếu không tìm thấy (hiếm khi xảy ra với Recursive)
                    start_index = current_pos
                
                end_index = start_index + len(chunk_text)
                current_pos = start_index + 1 # Update search start for next chunk

                # tìm timestamp bao phủ đoạn text này
                matched_ts = [
                    pos for pos in position_map
                    if not (pos["pos_end"] < start_index or pos["pos_start"] > end_index)
                ]

                metadata = {
                    "playlist": playlist,
                    "video_url": url,
                    "filename": filename,
                    "title": title,
                    "chunk_id": i,
                    "start_timestamp": matched_ts[0]["start"] if matched_ts else None,
                    "end_timestamp": matched_ts[-1]["end"] if matched_ts else None
                }
                
                # Tạo document object để tương thích với phần còn lại của pipeline nếu cần
                doc = Document(page_content=chunk_text, metadata=metadata)
                all_chunks.append(doc)

        # lưu tất cả chunks vào file json (giữ tên semantic_chunks.json để tương thích pipeline)
        output_path = os.path.join(output_dir, "semantic_chunks.json")
        os.makedirs(output_dir, exist_ok=True)
        
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump([
                {"page_content": chunk.page_content, "metadata": chunk.metadata}
                for chunk in all_chunks
            ], f, ensure_ascii=False, indent=4)

        print(f"Saved {len(all_chunks)} chunks to {output_path} (using RecursiveCharacterTextSplitter)")
        return all_chunks
