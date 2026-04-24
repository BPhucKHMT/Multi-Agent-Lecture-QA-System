import os
import sys
from pathlib import Path
from pydantic import TypeAdapter

# Add root to sys.path
sys.path.append(os.getcwd())

from backend.app.api.v1.endpoints.schemas import VideoListResponse
from backend.app.services.videos import list_videos

import sys
sys.stdout.reconfigure(encoding='utf-8')

# Mock a query
response_dict = list_videos(query="", page=1, page_size=5)

# Validate with Pydantic
try:
    response_obj = VideoListResponse(**response_dict)
    print("Pydantic validation successful")
    print(f"Total: {response_obj.total}")
    for video in response_obj.videos:
        print(f"ID: {video.id}")
        print(f"Video ID: {video.video_id}")
        print(f"Title: {video.title}")
        print(f"Thumbnail URL: {video.thumbnail_url}")
        print("-" * 20)
except Exception as e:
    print(f"Pydantic validation failed: {e}")
    # Print keys of the first video to see what's missing
    if response_dict['videos']:
        print(f"Keys in first video dict: {response_dict['videos'][0].keys()}")
