import sys
import os
from pathlib import Path

# Add src to path
sys.path.append(os.getcwd())

from src.storage.vectorstore import VectorDB
import json

def verify_thorough():
    print("🔍 Performing thorough VectorDB check...")
    vdb = VectorDB()
    collection = vdb.db._collection
    
    total_count = collection.count()
    print(f"📊 Total documents in DB: {total_count}")
    
    # Check for IDs following our new pattern
    all_data = collection.get(include=['metadatas'])
    ids = all_data['ids']
    metadatas = all_data['metadatas']
    
    pattern_ids = [id for id in ids if "_" in id and not "-" in id] # Simple heuristic for filename_chunkid
    uuid_ids = [id for id in ids if "-" in id and len(id) > 20]
    
    print(f"✅ Documents with Unique IDs (fixed pattern): {len(pattern_ids)}")
    print(f"⚠️ Documents with UUIDs (old pattern/duplicates): {len(uuid_ids)}")
    
    # Detect exact duplicates in content
    print("\n🧐 Checking for exact content duplicates...")
    contents = collection.get(include=['documents'])['documents']
    unique_contents = set(contents)
    print(f"Unique contents: {len(unique_contents)}")
    print(f"Redundant (duplicate) contents: {total_count - len(unique_contents)}")
    
    # Check OCR coverage
    ocr_count = sum(1 for m in metadatas if m.get('ocr_content'))
    print(f"\n📷 OCR Enrichment Coverage: {ocr_count}/{total_count} ({ocr_count/total_count:.1%})")
    
    # Sample a "Fixed ID" document
    if pattern_ids:
        print(f"\n📍 Sample Fixed ID Document ({pattern_ids[0]}):")
        sample = collection.get(ids=[pattern_ids[0]], include=['metadatas', 'documents'])
        print(f"Title: {sample['metadatas'][0].get('title')}")
        print(f"OCR: {'Yes' if sample['metadatas'][0].get('ocr_content') else 'No'}")

if __name__ == "__main__":
    verify_thorough()
