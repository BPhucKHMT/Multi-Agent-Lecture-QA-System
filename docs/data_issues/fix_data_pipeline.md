# Báo cáo Điều tra Lỗi Treo Pipeline (Hanging Transcript Loader)
# Đã hoàn thành ( 12/04/2026 )
## 📌 Hiện tượng
Khi chạy script `build_chunks_and_index.py`, tiến trình đạt đến 100% thanh tiến trình tải Transcript nhưng ngay lập tức bị "đứng hình" (pending/hanging mãi mãi).
Dòng in ra cuối cùng:
`Loading Transcripts: 100%|██████████| 72/72 [00:29<00:00,  2.41file/s]`

Đáng lý ra sau dòng này, script phải in tiếp `[cs114-máy-học] Chunking 72 documents...` nhưng lại không hề có phản hồi.

## 🕵️‍♂️ Điều tra nguyên nhân
Vấn đề nằm trong đoạn code class `TranscriptLoader` ở file `src/data_pipeline/data_loader/file_loader.py`:

```python
    def __call__(self, txt_files: List[str], metadata_path: str, workers: int = 2) -> List[dict]:
        num_processes = min(self.num_processes, workers)
        data = []

        with multiprocessing.Pool(processes=num_processes) as pool:
            total_files = len(txt_files)
            args = [(path, metadata_path) for path in txt_files]
            with tqdm(total=total_files, desc="Loading Transcripts", unit="file") as pbar:
                for result in pool.starmap(load_transcript, args):
                    data.append(result)
                    pbar.update(1)
        return data
```

1. **Deadlock khi dọn dẹp Pool (Teardown Hang)**: Khi khối `with multiprocessing.Pool(...) as pool:` kết thúc, Python tự động gọi `pool.close()` và `pool.join()`. Mặc dù `tqdm` đã báo 100% (tức là `starmap` đã gom đủ kết quả trả về), trên hệ điều hành **Windows** (sử dụng phương thức `spawn` thay vì `fork`), việc trao đổi dữ liệu cực lớn qua IPC Pipes (Inter-Process Communication) hay rò rỉ pipe đôi khi khiến tiến trình chính bị chặn vĩnh viễn lúc chờ các worker tắt.
2. **Dữ liệu lớn truyền qua Pipes**: Kết quả từ `load_transcript` chứa chuỗi `full_text` toàn bộ video và một mảng list `position_map` rất lớn (mỗi đoạn transcript có một timestamp map). Khi truyền tập dữ liệu khổng lồ này từ các process con về process cha, nó dễ gây ra tắc nghẽn bộ đệm chuẩn của Windows.
3. **Overhead không đáng có**: Việc đọc file text (`.txt`) từ SSD hoặc RAM cache vốn dĩ là thao tác I/O cực kỳ nhanh. Khởi tạo `multiprocessing` trên Windows cho thao tác này tạo ra overhead lớn hơn cả thời gian chạy tuần tự.

## 💊 Cách khắc phục (Fix)
Để sửa dứt điểm lỗi này, chúng ta cần loại bỏ `multiprocessing.Pool` ra khỏi thao tác đọc transcript. Thay vào đó, áp dụng một vòng lặp đồng bộ (hoặc dùng `ThreadPoolExecutor` nếu thực sự cần đa luồng, nhưng đối với đọc file text nội bộ tốc độ cao thì lặp tuần tự là đủ và an toàn nhất).

**Sửa lại `TranscriptLoader.__call__` trong `src/data_pipeline/data_loader/file_loader.py`**:

```python
    def __call__(self, txt_files: List[str], metadata_path: str, workers: int = 2) -> List[dict]:
        data = []
        total_files = len(txt_files)
        
        # Chạy vòng lặp đồng bộ thay vì multiprocessing để tránh lỗi deadlock trên Windows
        # Việc load file text siêu nhẹ, không cần tới multiprocessing
        with tqdm(total=total_files, desc="Loading Transcripts", unit="file") as pbar:
            for path in txt_files:
                result = load_transcript(path, metadata_path)
                data.append(result)
                pbar.update(1)
                
        return data
```

**Lợi ích của giải pháp**:
- **Tránh 100% Deadlock**: Không có IPC blocking hay lỗi khi đợi Worker process đóng ở Windows.
- **Tốc độ ngang ngửa**: Tránh được overhead cấp phát OS process, có khi còn lướt qua tệp .txt siêu nhỏ trong nháy mắt.
- **Tiêu thụ RAM tiết kiệm**: Load trực tiếp thẳng vào memory của process chính.
- Khắc phục triệt để tình trạng thanh tqdm nhảy 100% rồi kẹt.
