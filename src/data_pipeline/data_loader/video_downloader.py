import subprocess
import os
import json
from pathlib import Path
from typing import Dict, Any, List
import cv2

class VideoDownloader:
    """Download videos từ YouTube playlist và lấy metadata kỹ thuật."""
    
    def __init__(self, output_root: str = "artifacts/videos"):
        self.output_root = Path(output_root)
        self.output_root.mkdir(parents=True, exist_ok=True)

    def download_playlist(self, playlist_url: str, folder_name: str, limit: int = None) -> Dict[str, Any]:
        """
        Download tất cả video trong playlist.
        """
        output_dir = self.output_root / folder_name
        output_dir.mkdir(parents=True, exist_ok=True)
        
        archive_file = output_dir / "download_archive.txt"
        
        # Build command yt-dlp
        # Format: "idx - title.mp4"
        template = str(output_dir / "%(playlist_index)s - %(title)s.%(ext)s")
        
        cmd = [
            "yt-dlp",
            "-f", "bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[height<=720][ext=mp4]",
            "--merge-output-format", "mp4",
            "-o", template,
            "--download-archive", str(archive_file),
            "--no-post-overwrites",
            playlist_url
        ]
        
        if limit:
            cmd.extend(["--playlist-end", str(limit)])
            
        print(f"🎬 Đang tải playlist vào: {output_dir}")
        try:
            result = subprocess.run(cmd, check=True, capture_output=True, text=True, encoding='utf-8', errors='ignore')
            return {"status": "success", "output": output_dir}
        except subprocess.CalledProcessError as e:
            print(f"❌ Lỗi tải video: {e.stderr}")
            return {"status": "failed", "error": str(e)}

    def get_technical_data(self, folder_name: str) -> Dict[str, Any]:
        """
        Lấy FPS và thời lượng của tất cả video đã tải.
        Lưu vào video_info.json trong folder_name.
        """
        video_dir = self.output_root / folder_name
        info_file = video_dir / "video_info.json"
        
        data = {}
        if info_file.exists():
            with open(info_file, "r", encoding="utf-8") as f:
                data = json.load(f)
        
        video_files = list(video_dir.glob("*.mp4"))
        updated = False
        
        for v_path in video_files:
            v_name = v_path.name
            if v_name not in data:
                cap = cv2.VideoCapture(str(v_path))
                if cap.isOpened():
                    fps = cap.get(cv2.CAP_PROP_FPS)
                    frame_count = cap.get(cv2.CAP_PROP_FRAME_COUNT)
                    duration = frame_count / fps if fps > 0 else 0
                    data[v_name] = {
                        "fps": fps,
                        "frame_count": int(frame_count),
                        "duration": duration
                    }
                    updated = True
                cap.release()
        
        if updated:
            with open(info_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        
        return data
