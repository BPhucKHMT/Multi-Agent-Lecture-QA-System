import os
import sys
from pathlib import Path

# Add src to sys.path
sys.path.append(os.getcwd())

from backend.app.services.videos import _build_video_index
from src.shared.config import get_path

import sys
sys.stdout.reconfigure(encoding='utf-8')

print(f"Videos dir: {get_path('videos_dir')}")
videos = _build_video_index()
print(f"Total videos found: {len(videos)}")

count_no_video_id = 0
for video in videos:
    if not video.get('video_id'):
        count_no_video_id += 1

print(f"Videos missing video_id: {count_no_video_id}")

for video in videos[:10]:
    print(f"Title: {video['title']}")
    print(f"Video ID: {repr(video.get('video_id'))}")
    print(f"Thumbnail: {repr(video.get('thumbnail_url'))}")
    print("-" * 20)
