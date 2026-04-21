import os
import sys
import json
from pathlib import Path

# Add src to path if needed
sys.path.append(os.getcwd())

from src.data_pipeline.data_loader.pipeline import DataPipeline

# List of playlists to re-index
PLAYLIST_FOLDERS = [
    "cs114-máy-học",
    "cs116-lập-trình-python-cho-máy-học",
    "cs315-máy-học-nâng-cao",
    "cs431-các-kĩ-thuật-học-sâu-và-ứng-dụng"
]

def main():
    pipeline = DataPipeline()
    
    print("STARTING re-indexing of enriched chunks...")
    
    for folder in PLAYLIST_FOLDERS:
        print(f"\n--- Processing {folder} ---")
        try:
            # Check if file exists first
            from src.data_pipeline.data_loader.utils import get_playlist_paths
            paths = get_playlist_paths(folder)
            chunks_file = Path(paths["chunks_file"])
            
            if not chunks_file.exists():
                print(f"WARNING: Chunks file not found: {chunks_file}")
                continue
                
            pipeline.step8_index(folder)
        except Exception as e:
            print(f"ERROR indexing {folder}: {e}")

    print("\nDONE: All playlists have been re-indexed into the fresh Vector DB.")

if __name__ == "__main__":
    main()
