import cv2
import os

video_path = "artifacts/videos/cày-chay-tay-nạp-capped-legends/1 - Vũ Liz Cày Chay Tay Nạp Capped Legends Tập 1 ： Xây Dựng Đội Hình Capped Legends Mạnh Nhất.f398.mp4"

print(f"Checking video: {video_path}")
print(f"Exists: {os.path.exists(video_path)}")

cap = cv2.VideoCapture(video_path)
if not cap.isOpened():
    print("❌ OpenCV could NOT open the video file normally.")
    # Thử encode lại đường dẫn
    import numpy as np
    # OpenCV on Windows sometimes needs this hack for unicode paths
    pass
else:
    print("✅ OpenCV opened the video file!")
    fps = cap.get(cv2.CAP_PROP_FPS)
    print(f"FPS: {fps}")
    ret, frame = cap.read()
    print(f"Frame read success: {ret}")
    cap.release()
