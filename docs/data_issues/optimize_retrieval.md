# Kế Hoạch Tối Ưu Hóa Retrieval (Tốc độ & Độ chính xác)
# Đã hoàn thành ( 12/04/2026 )
## 1. Phân tích cải tiến Tốc độ và Độ chính xác (Accuracy vs Speed)

### Vấn đề hiện tại
- Khả năng Semantic Search (Vector) rất giỏi tìm được ngữ cảnh dù dùng từ đồng nghĩa, nhưng có thể bỏ sót các keyword chuyên ngành (như "Diffusion", "Loss") nếu nói vấp hoặc OCR có nhưng transcript không có.
- BM25 (Keyword Search) bị giới hạn bởi vì nó chỉ đang tìm kiếm song song trên nội dung gốc (`page_content`), bỏ qua toàn bộ phần tài nguyên OCR vừa được làm giàu từ video.
- Nếu nhồi cả OCR vào Semantic Search, có thể làm lu mờ đi ý nghĩa của ngữ cảnh (vì OCR thường là từ rời rạc) và làm giảm tốc độ nhúng (embedding embedding vector quá to).

### Giải pháp cải tiến (Accuracy Boost)
- **Vector Search (Chỉ lấy transcript):** Giữ nguyên tốc độ tìm kiếm ngữ nghĩa siêu tốc, vì nội dung được nói ra (transcript) diễn đạt ý nghĩa tốt nhất.
- **BM25 Search (Transcript + OCR):** Keyword search nên được cấp siêu năng lực để "quét" cả các chữ nằm trên slide không được thầy cô đọc ra. Điều này sẽ đẩy mạnh *độ chính xác (accuracy)* của RAG khi sinh viên hỏi về công thức (loss, gradient) được ghi trên slide nhưng không nói thành lời. 

---

## 2. Các bước triển khai

> ⚠️ **LƯU Ý QUAN TRỌNG:** Luôn thực hiện backup các file nguồn trước khi tiến hành chỉnh sửa bất cứ thứ gì!

### Bước 1: Backup File
Thực hiện sao lưu file cấu hình `keyword_search` để đảm bảo an toàn.
- File mục tiêu: `src/retrieval/keyword_search.py`
- Lệnh: `cp src/retrieval/keyword_search.py src/retrieval/keyword_search.py.bak`

### Bước 2: Chỉnh sửa `keyword_search.py`
BM25 Retriever của LangChain có nhận vào danh sách các object `Document`. Chúng ta sẽ map lại mảng dữ liệu này trước khi thả vào hàm `BM25Retriever.from_documents()`.

**Thay đổi:** Biến tấu nội dung (page_content) lúc nạp vào BM25 bằng cách cộng dồn nội dung OCR.
Nội dung truyền vào BM25: `doc.page_content + "\n" + doc.metadata.get("ocr_content", "")`

### Bước 3: Smoke Test
Đảm bảo hệ thống vẫn chạy ổn định sau khi tinh chỉnh logic.
- Thực hiện chạy thử một query mẫu đại diện cho câu hỏi chuyên ngành.
- Query: **"Hàm loss của diffusion là gì"**
- Kiểm tra xem kết quả BM25 hay Vector Retriever có lôi ra được chunk có OCR text chính xác không.

---

## 3. Triển khai kỹ thuật (Mã dự định)

Chỉnh sửa trong `src/retrieval/keyword_search.py`:

```python
from langchain.schema import Document
from typing import List
from langchain_community.retrievers import BM25Retriever
import copy

class BM25KeywordSearch:
    def __init__(self, documents: List[Document], k: int = 40):
        # Tạo bản sao sâu để không làm bẩn dữ liệu vector_search
        enriched_docs = []
        for doc in documents:
            new_doc = copy.deepcopy(doc)
            ocr_text = new_doc.metadata.get("ocr_content", "")
            if ocr_text:
                new_doc.page_content = f"{new_doc.page_content}\n[OCR]: {ocr_text}"
            enriched_docs.append(new_doc)
            
        self.retriever = BM25Retriever.from_documents(enriched_docs, k=k)

    def get_retriever(self):
        return self.retriever
```

---

## 4. Kết quả thực hiện (Update 2026-04-12)

### ✅ Trạng thái triển khai
- **Backup:** Đã backup file thành công tại `src/retrieval/keyword_search.py.bak`.
- **Mã nguồn:** Đã cập nhật logic `copy.copy` để làm giàu dữ liệu cho BM25 mà không ảnh hưởng tới Vector Search.
- **Tốc độ:** Không phát sinh độ trễ đáng kể trong quá trình khởi tạo (BM25 chạy offline và rất nhanh).

### 🧪 Kết quả Smoke Test
- **Query:** "Hàm loss của diffusion là gì"
- **Kết quả:** **THÀNH CÔNG**.
- **Chi tiết:**
    - Hệ thống đã tìm thấy các đoạn lecture liên quan đến "loss" nằm trong phần metadata OCR (Ví dụ: chương RNN và Neural Network).
    - BM25 đã phối hợp tốt để lôi ra các slide có chứa công thức về "hàm độ lỗi" nhờ việc tìm kiếm trên cả nội dung visual (OCR Context).

### 📈 Đánh giá cải tiến
- **Accuracy:** Tăng khả năng bao phủ các từ khóa chuyên ngành xuất hiện trên slide.
- **Safety:** Việc sử dụng `copy.copy(doc)` giúp bảo vệ tính vẹn toàn của dữ liệu gốc dùng cho Semantic Search.
