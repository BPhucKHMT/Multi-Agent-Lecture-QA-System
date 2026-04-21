import sys
import os
from pathlib import Path

# Add src to path
sys.path.append(os.getcwd())

from src.storage.vectorstore import VectorDB

def cleanup():
    print("🧹 Starting Database Cleanup...")
    vdb = VectorDB()
    collection = vdb.db._collection
    
    # Fetch all IDs
    all_ids = collection.get(include=[])['ids']
    total_before = len(all_ids)
    
    # Identify UUID-style IDs (old duplicates)
    # New IDs look like 'video_id_chunk_num' (no hyphens from UUID)
    to_delete = [id for id in all_ids if "-" in id and len(id) > 20]
    
    if not to_delete:
        print("✨ No old UUID records found. Database is already clean!")
        return

    print(f"🗑️ Found {len(to_delete)} old/duplicate records to delete.")
    
    # Chroma DB delete has limits on batch size sometimes, but let's try
    # Batch delete to be safe
    batch_size = 500
    for i in range(0, len(to_delete), batch_size):
        batch = to_delete[i:i + batch_size]
        collection.delete(ids=batch)
        print(f"✅ Deleted batch {i//batch_size + 1}/{(len(to_delete)-1)//batch_size + 1}")

    print(f"\n🎉 Cleanup Complete!")
    print(f"📊 Total before: {total_before}")
    print(f"📊 Total after: {collection.count()}")

if __name__ == "__main__":
    cleanup()
