import sys
import os
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from src.shared.config import get_path

# Path to python executable we just used
# C:\Users\ADMIN\anaconda3\python.exe

def verify():
    persist_dir = get_path("vector_db_dir")
    print(f"Verifying Vector DB at: {persist_dir}")
    
    embedding = HuggingFaceEmbeddings(
        model_name="BAAI/bge-m3", 
        model_kwargs={"device": "cpu"}
    )
    
    db = Chroma(
        persist_directory=persist_dir,
        embedding_function=embedding
    )
    
    # Get all documents (small sample)
    results = db.get(limit=5)
    
    print(f"Found {len(results['ids'])} sample documents.")
    
    for i in range(len(results['ids'])):
        metadata = results['metadatas'][i]
        print(f"\nDocument {i}:")
        print(f"  Title: {metadata.get('title')}")
        print(f"  OCR length: {len(metadata.get('ocr_content', ''))}")
        if metadata.get('ocr_content'):
            print(f"  OCR sample: {metadata['ocr_content'][:100]}...")
        else:
            print("  OCR content: MISSING")

if __name__ == "__main__":
    verify()
