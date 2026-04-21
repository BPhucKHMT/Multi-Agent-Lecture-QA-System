import json
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

class PipelineState:
    """Track trạng thái pipeline + backup dữ liệu."""
    
    def __init__(self, state_file: str = "artifacts/pipeline_state.json", backup_root: str = "artifacts/backups"):
        self.state_file = Path(state_file)
        self.backup_root = Path(backup_root)
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        self.backup_root.mkdir(parents=True, exist_ok=True)
        self.state = self._load_state()

    def _load_state(self) -> Dict[str, Any]:
        if self.state_file.exists():
            try:
                with open(self.state_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return {"last_updated": "", "playlists": {}}
        return {"last_updated": "", "playlists": {}}

    def _save_state(self):
        self.state["last_updated"] = datetime.now().isoformat()
        with open(self.state_file, "w", encoding="utf-8") as f:
            json.dump(self.state, f, indent=2, ensure_ascii=False)

    def get_status(self, playlist_id: str, step: str) -> Dict[str, Any]:
        """Lấy trạng thái của một bước cụ thể."""
        return self.state.get("playlists", {}).get(playlist_id, {}).get(step, {"status": "pending"})

    def set_status(self, playlist_id: str, step: str, status: str, **extra):
        """Cập nhật trạng thái và lưu lại."""
        if "playlists" not in self.state:
            self.state["playlists"] = {}
        if playlist_id not in self.state["playlists"]:
            self.state["playlists"][playlist_id] = {}
        
        self.state["playlists"][playlist_id][step] = {
            "status": status,
            "timestamp": datetime.now().isoformat(),
            **extra
        }
        self._save_state()

    def backup(self, step_name: str, folder_name: str, target_paths: List[str]) -> str:
        """
        Backup các file/thư mục quan trọng trước khi ghi đè.
        Return: Đường dẫn thư mục backup.
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_dir = self.backup_root / f"{step_name}_{folder_name}_{timestamp}"
        backup_dir.mkdir(parents=True, exist_ok=True)

        for path_str in target_paths:
            path = Path(path_str)
            if path.exists():
                dest = backup_dir / path.name
                if path.is_dir():
                    shutil.copytree(path, dest)
                else:
                    shutil.copy2(path, dest)
        
        return str(backup_dir)

    def print_status(self):
        """In bảng trạng thái ra console."""
        print("\n" + "="*50)
        print("📊 PIPELINE STATUS REPORT")
        print("="*50)
        playlists = self.state.get("playlists", {})
        if not playlists:
            print("No data recorded.")
            return

        for pid, steps in playlists.items():
            print(f"\n📂 Playlist: {pid}")
            for step, info in steps.items():
                status = info.get("status", "pending")
                icon = "✅" if status == "done" else "⏳" if status == "in_progress" else "❌" if status == "failed" else "⚪"
                print(f"  {icon} {step:20}: {status}")
        print("="*50 + "\n")
