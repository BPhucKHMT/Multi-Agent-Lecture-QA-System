import yaml
from pathlib import Path
from typing import Dict, Any

def load_config(config_path: str = "config.yaml") -> Dict[str, Any]:
    """Load config.yaml file."""
    path = Path(config_path)
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}

def get_playlist_paths(folder_name: str) -> Dict[str, str]:
    """
    Tự động sinh các đường dẫn cho một playlist dựa trên folder_name.
    folder_name thường được lấy từ metadata của playlist (slugified title).
    """
    base_artifacts = Path("artifacts")
    
    paths = {
        "videos_dir": str(base_artifacts / "videos" / folder_name),
        "data_dir": str(base_artifacts / "data" / folder_name),
        "chunks_dir": str(base_artifacts / "chunks" / folder_name),
        "scene_dir": str(base_artifacts / "data_extraction" / "SceneJSON" / folder_name),
        "keyframes_dir": str(base_artifacts / "data_extraction" / "Keyframes" / folder_name),
        "ocr_dir": str(base_artifacts / "data_extraction" / "OCR" / "ocr_output_final" / folder_name),
        "chunks_file": str(base_artifacts / "chunks" / folder_name / "semantic_chunks.json"),
        "metadata_file": str(base_artifacts / "data" / folder_name / "metadata.json")
    }
    
    # Đảm bảo các thư mục tồn tại
    for key, p in paths.items():
        if "file" not in key:
            Path(p).mkdir(parents=True, exist_ok=True)
            
    return paths

def slugify(text: str) -> str:
    """Chuyển tiêu đề thành dạng folder-name-chuan."""
    import re
    import unicodedata
    
    text = unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('utf-8')
    text = re.sub(r'[^\w\s-]', '', text).strip().lower()
    return re.sub(r'[-\s]+', '-', text)
