#!/usr/bin/env python
"""Quick test for chunker strategies."""
import sys
import os
import json
import tempfile
import shutil
import importlib.util

# Load chunker module trực tiếp để tránh import transformers
spec = importlib.util.spec_from_file_location("chunker", "src/retrieval/text_splitters/chunker.py")
chunker_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(chunker_module)

TranscriptChunker = chunker_module.TranscriptChunker
RecursiveChunker = chunker_module.RecursiveChunker
TimestampChunker = chunker_module.TimestampChunker
SemanticChunker = chunker_module.SemanticChunker

def sample_documents():
    """Create sample transcript documents for testing."""
    return [
        {
            "full_text": "Hello world. This is a test. " * 50,
            "position_map": [
                {"start": "0:00:00", "end": "0:00:05", "text": "Hello world.", "pos_start": 0, "pos_end": 12},
                {"start": "0:00:05", "end": "0:00:10", "text": "This is a test. " * 10, "pos_start": 12, "pos_end": 132},
            ],
            "playlist": "test_playlist",
            "filename": "test_video_1",
            "title": "Test Video 1",
            "url": "https://example.com/test1"
        }
    ]

def test_recursive():
    print("\n=== Test RecursiveChunker ===")
    os.environ["CHUNK_STRATEGY"] = "recursive"
    chunker = TranscriptChunker(open_api_key="dummy")
    tmpdir = tempfile.mkdtemp()
    try:
        chunks = chunker(sample_documents(), tmpdir)
        print(f"Created {len(chunks)} chunks")
        with open(os.path.join(tmpdir, "semantic_chunks.json")) as f:
            data = json.load(f)
        print(f"Metadata sample: {data[0]['metadata'].keys()}")
        print(f"Chunk strategy: {data[0]['metadata'].get('chunk_strategy')}")
        assert data[0]['metadata']['chunk_strategy'] == 'recursive'
        print("PASS: Recursive chunker works")
    finally:
        shutil.rmtree(tmpdir)

def test_timestamp_150_50():
    print("\n=== Test TimestampChunker (150s, 50s) ===")
    os.environ["CHUNK_STRATEGY"] = "timestamp_150_50"
    chunker = TranscriptChunker(open_api_key="dummy")
    tmpdir = tempfile.mkdtemp()
    try:
        chunks = chunker(sample_documents(), tmpdir)
        print(f"Created {len(chunks)} chunks")
        with open(os.path.join(tmpdir, "semantic_chunks.json")) as f:
            data = json.load(f)
        print(f"Metadata sample: {data[0]['metadata'].keys()}")
        print(f"Chunk strategy: {data[0]['metadata'].get('chunk_strategy')}")
        print(f"Window: {data[0]['metadata'].get('window_seconds')}s, overlap: {data[0]['metadata'].get('overlap_seconds')}s")
        assert data[0]['metadata']['chunk_strategy'] == 'timestamp_150_50'
        assert data[0]['metadata']['window_seconds'] == 150
        assert data[0]['metadata']['overlap_seconds'] == 50
        print("PASS: Timestamp chunker works")
    finally:
        shutil.rmtree(tmpdir)

def test_timestamp_90_30():
    print("\n=== Test TimestampChunker (90s, 30s) ===")
    os.environ["CHUNK_STRATEGY"] = "timestamp_90_30"
    chunker = TranscriptChunker(open_api_key="dummy")
    tmpdir = tempfile.mkdtemp()
    try:
        chunks = chunker(sample_documents(), tmpdir)
        print(f"Created {len(chunks)} chunks")
        with open(os.path.join(tmpdir, "semantic_chunks.json")) as f:
            data = json.load(f)
        assert data[0]['metadata']['chunk_strategy'] == 'timestamp_90_30'
        assert data[0]['metadata']['window_seconds'] == 90
        assert data[0]['metadata']['overlap_seconds'] == 30
        print("PASS: Timestamp 90/30 works")
    finally:
        shutil.rmtree(tmpdir)

def test_unknown_fallback():
    print("\n=== Test Unknown Strategy Fallback ===")
    os.environ["CHUNK_STRATEGY"] = "unknown_strategy"
    chunker = TranscriptChunker(open_api_key="dummy")
    tmpdir = tempfile.mkdtemp()
    try:
        chunks = chunker(sample_documents(), tmpdir)
        with open(os.path.join(tmpdir, "semantic_chunks.json")) as f:
            data = json.load(f)
        assert data[0]['metadata']['chunk_strategy'] == 'recursive'
        print("PASS: Unknown strategy falls back to recursive")
    finally:
        shutil.rmtree(tmpdir)

def test_semantic_fallback():
    print("\n=== Test Semantic Strategy (with fallback) ===")
    os.environ["CHUNK_STRATEGY"] = "semantic"
    os.environ["SEMANTIC_EMBEDDING_PROVIDER"] = "openai"
    os.environ["myAPIKey"] = "dummy"
    chunker = TranscriptChunker(open_api_key="dummy")
    tmpdir = tempfile.mkdtemp()
    try:
        chunks = chunker(sample_documents(), tmpdir)
        with open(os.path.join(tmpdir, "semantic_chunks.json")) as f:
            data = json.load(f)
        # Nếu thiếu dependencies, sẽ fallback về recursive
        print(f"Semantic chunker resulted in {len(chunks)} chunks")
        print(f"Chunk strategy: {data[0]['metadata'].get('chunk_strategy')}")
        print("PASS: Semantic strategy handled (may fallback if deps missing)")
    finally:
        shutil.rmtree(tmpdir)

if __name__ == "__main__":
    print("Testing chunker module...")
    try:
        test_recursive()
        test_timestamp_150_50()
        test_timestamp_90_30()
        test_unknown_fallback()
        test_semantic_fallback()
        print("\n" + "="*50)
        print("All tests PASSED!")
    except Exception as e:
        print(f"\nTest FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
