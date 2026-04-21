import os
import glob
from pathlib import Path

# Giả lập pipeline
folder_name = "cày-chay-tay-nạp-capped-legends"
base_artifacts = Path("artifacts")
data_dir = base_artifacts / "data" / folder_name
transcript_dir = "processed_transcripts"

# Kiểm tra đường dẫn
playlist_path = data_dir
transcript_path = os.path.join(playlist_path, transcript_dir)
txt_list = glob.glob(os.path.join(transcript_path, "*.txt"))

print(f"DEBUG INFO:")
print(f"  Playlist Path: {playlist_path} (exists: {playlist_path.exists()})")
print(f"  Transcript Path: {transcript_path} (exists: {os.path.exists(transcript_path)})")
print(f"  Full Glob Pattern: {os.path.join(transcript_path, '*.txt')}")
print(f"  Files found: {len(txt_list)}")
for f in txt_list:
    print(f"    - {f}")

# Kiểm tra contents của folder
if os.path.exists(transcript_path):
    print(f"  Listing folder contents:")
    for item in os.listdir(transcript_path):
        print(f"    - {item}")
