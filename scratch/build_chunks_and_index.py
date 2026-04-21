import os
import sys
from pathlib import Path

# Add src to path
sys.path.append(os.getcwd())

from src.data_pipeline.data_loader.pipeline import DataPipeline
from src.data_pipeline.data_loader.utils import load_config, slugify
from src.data_pipeline.data_loader.coordinator import PlaylistMetadataFetch, extract_playlist_id

def get_folder_name(url):
    """Helper to get folder name without crawling."""
    pid = extract_playlist_id(url)
    meta = PlaylistMetadataFetch(pid)
    # This might still hit YouTube API for title, but won't crawl everything
    meta.convert_to_json_data()
    folder_name = meta.playlist_name
    if not folder_name:
        folder_name = slugify(meta.title) if hasattr(meta, 'title') and meta.title else pid
    return folder_name

def main():
    pipeline = DataPipeline()
    config = load_config()
    playlists = config.get("playlists", [])
    enabled = [p for p in playlists if p.get("enabled", True)]
    
    print(f"🚀 Building enriched chunks (Chunk -> Combine -> Index) for {len(enabled)} playlists...")
    
    for p in enabled:
        url = p["url"]
        print(f"\n--- Processing {url} ---")
        try:
            # We need the folder_name to find files
            # Since user has them, we just need to resolve the name
            folder_name = get_folder_name(url)
            print(f"📂 Folder identified: {folder_name}")
            
            # Step 3: Semantic Chunking (using processed_transcripts)
            print("\n✂️ STEP 3: SEMANTIC CHUNKING")
            pipeline.step3_chunk(folder_name)
            
            # Step 7: Combine OCR
            print("\n🔗 STEP 7: COMBINE CONTENT")
            pipeline.step7_combine(folder_name)
            
            # Step 8: Indexing
            print("\n🗄️ STEP 8: INDEXING")
            pipeline.step8_index(folder_name)
            
        except Exception as e:
            print(f"❌ Error processing {url}: {e}")
            import traceback
            traceback.print_exc()

    print("\n✅ Processing complete.")

if __name__ == "__main__":
    main()
