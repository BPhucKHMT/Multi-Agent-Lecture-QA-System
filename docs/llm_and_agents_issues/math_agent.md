# Kế hoạch Triển khai Sửa lỗi Output của Math Agent

> **Dành cho Claude/Agent:** REQUIRED SUB-SKILL: Sử dụng `superpowers:executing-plans` để thực thi plan này từng task một.

**Mục tiêu:** Khắc phục các lỗi về định dạng output của Math Agent bao gồm: bị lẫn tiếng Anh, chữ dính sát vào công thức, dư thừa block code markdown, và lỗi hiển thị chữ "undefined" màu đỏ trên giao diện (do KaTeX/markdown).

**Kiến trúc:** Chúng ta sẽ sửa file `src/rag_core/agents/math.py` để điều chỉnh các mẫu regex xử lý nội dung, loại bỏ các prompt hạn chế (nguyên nhân gây ra chữ "undefined"), cắt bỏ thủ công các block code markdown bị bọc bên ngoài, và ép buộc nhắc nhở (prompt) phải sinh ra nội dung thuần Tiếng Việt.

**Tech Stack:** Python, Streamlit, LangChain, Math Regex/KaTeX rendering.

---

### Task 1: Sửa lỗi khoảng trắng & Định dạng Markdown (Lỗi "Chữ dính nhau")

Bộ phân tích của Streamlit yêu cầu phải có dòng trống (newline) bao quanh block công thức `$$` và có khoảng trắng xung quanh công thức inline `$`. Các Regex hiện tại đang dùng hàm `.strip()` và loại bỏ khoảng trắng một cách thô bạo, dẫn đến chữ bị dính vào công thức và cản trở việc hiển thị block math.

**Files:**
- Sửa đổi: `src/rag_core/agents/math.py` (ở hai hàm `_normalize_math_markdown` và `_clean_verification_text`)

**Bước 1: Viết test thất bại / Kiểm tra màn hình UI trực quan**
*Hiện chưa có file test chuẩn cho UI parsing này, do đó thay đổi sẽ đưa thẳng vào code và kiểm tra trực tiếp qua hàm hoặc trên giao diện màn hình trực quan.*

**Bước 2: Viết mã triển khai tối thiểu**
Tìm hàm `_normalize_math_markdown` trong `src/rag_core/agents/math.py` và sửa đổi để đảm bảo có thêm các khoảng trắng và dấu xuống dòng:

Sửa đổi `_normalize_math_markdown` (ở khoảng dòng 54) thành:
```python
    normalized = re.sub(
        r"\\\[\s*(.*?)\s*\\\]",
        lambda m: f"\n\n$${m.group(1).strip()}$$\n\n",
        normalized,
        flags=re.DOTALL,
    )
    normalized = re.sub(
        r"\\\(\s*(.*?)\s*\\\)",
        lambda m: f" ${m.group(1).strip()}$ ",
        normalized,
        flags=re.DOTALL,
    )
    normalized = re.sub(
        r"\[\s*([^\[\]]*\\[^\[\]]*)\s*\]",
        lambda m: f"\n\n$${m.group(1).strip()}$$\n\n",
        normalized,
        flags=re.DOTALL,
    )

Đồng thời, bạn cũng cần XÓA các đoạn code thay thế ký tự thành Unicode cố định (bởi vì chúng ta muốn giữ nguyên định dạng mã LaTeX):
**Xóa toàn bộ các đoạn .replace("sigma(x)", "σ(x)")** khỏi tất cả các hàm (`_latexize_query_text`, `_latexize_expression`, `_clean_verification_text`).
```

**Bước 3: Commit**
```bash
git add src/rag_core/agents/math.py
git commit -m "fix(math): thêm khoảng trắng và newline cho math markdown để chống lỗi chữ dính nhau"
```

---

### Task 2: Loại bỏ các Block Code Markdown khỏi Lời giải (Lỗi "Dính code j đó đó")

Đôi khi LLM tự ý gói bọc lời giải toán học bằng block mã code ` ```markdown ... ``` `. Nếu không được loại bỏ ra khỏi chuỗi kết quả, giao diện sẽ hiển thị y nguyên một cục code xám thay vì render công thức Toán.

**Files:**
- Sửa đổi: `src/rag_core/agents/math.py` (trong hàm `_build_math_tutor_text`)

**Bước 1: Viết mã triển khai tối thiểu**
Tìm hàm `_build_math_tutor_text` trong `src/rag_core/agents/math.py`. Thêm logic cắt bỏ block code thừa ở ngay dòng đầu của hàm:

Sửa đổi `_build_math_tutor_text` (ở khoảng dòng 191):
```python
def _build_math_tutor_text(query: str, explanation: str, is_success: bool, math_result: str) -> str:
    clean_explanation = (explanation or "").strip()
    clean_explanation = re.sub(r"^```(?:markdown|math)?\s*(.*?)\s*```$", r"\1", clean_explanation, flags=re.DOTALL | re.IGNORECASE)
    clean_explanation = _normalize_math_markdown(clean_explanation)
    clean_explanation = clean_explanation or "Mình chưa tạo được diễn giải chi tiết."
```

**Bước 2: Commit**
```bash
git add src/rag_core/agents/math.py
git commit -m "fix(math): loại bỏ các ký tự markdown thừa xuất hiện trong diễn giải của LLM"
```

---

### Task 3: Sắp xếp lại Câu Lệnh (Prompt) Giảm thiểu Lỗi "Undefined" và Tiếng Anh (Lỗi "Undefined", "Dính tiếng Anh")

Prompt cũ đang giới hạn tiêu cực: "Không được dùng placeholder như undefined hoặc null". Lệnh này đôi khi phản tác dụng, khiến LLM lỡ in ra `undefined` hoặc gây lỗi macro chưa định nghĩa (`\undefined`) trong KaTeX. Bên cạnh đó, tracebacks lỗi báo cáo thực thi của SymPy vẫn xuất tiếng Anh khi script thất bại. Chúng ta cần cập nhật lời nhắc của LLM mạnh mẽ hơn đối với yêu cầu tiếng Việt.

**Files:**
- Sửa đổi: `src/rag_core/agents/math.py` (trong các hàm `generate_sympy_code`, `generate_derivation`, `_repair_explanation`)

**Bước 1: Viết mã triển khai tối thiểu**
Chỉnh sửa lại các chuỗi (string) bên trong phần Prompts thuộc `src/rag_core/agents/math.py`:

Trong `_repair_explanation` (ở khoảng dòng 176):
```python
Ràng buộc:
- Mọi công thức phải dùng định dạng chuẩn LaTeX (ví dụ: dùng `\sigma` thay vì `σ`, dùng `\frac{a}{b}` thay vì `a/b`).
- Phải bọc công thức bằng markdown math: $...$ hoặc $$...$$.
- Không dùng dạng [ ... ] hoặc \( ... \) để bọc công thức.
- Luôn có khoảng trắng rõ ràng giữa chữ tiếng Việt và công thức toán.
- Chỉ viết phần nội dung lời giải, không thêm tiêu đề markdown.
```

Trong `generate_sympy_code` (ở khoảng dòng 235):
```python
Bạn là chuyên gia giải toán bằng Python Sympy.
Yêu cầu: {query}
Hãy sinh ra MÃ PYTHON SỬ DỤNG SYMPY ĐỂ GIẢI BÀI TOÁN TRÊN VÀ PRINT KẾT QUẢ CUỐI CÙNG HOẶC RA NGHIỆM ĐỂ XÁC MINH CÂU TRẢ LỜI.
Dùng tiếng Việt trong hàm print() nếu có in ra chuỗi giải thích.
Trả về mã script nằm trong block ```python...```. Không cần giải thích dài dòng ở đây.
```

Trong `generate_derivation` (ở khoảng dòng 260):
```python
...
Bây giờ, hãy viết ra BÀI GIẢI CHI TIẾT TỪNG BƯỚC (step-by-step derivation), dùng hoàn toàn tiếng Việt.
Mọi công thức PHẢI viết ở dạng mã chuẩn LaTeX (VD: `\sigma`, `\frac{...}`) và bọc đúng chuẩn markdown math: $...$ hoặc $$...$$ (không dùng [ ... ]).
Luôn cách một khoảng trắng giữa văn bản và công thức toán. Dùng xuống dòng trước và sau những đoạn khối công thức $$...$$ lớn.
Chỉ viết phần nội dung lời giải, không thêm tiêu đề markdown.
```

Trong nhánh prompt dự phòng của `generate_derivation` (ở khoảng dòng 276):
```python
...
Hãy viết hướng dẫn giải tay bằng tiếng Việt theo từng bước để học sinh vẫn hiểu cách làm và tự kiểm tra được.
Dịch các thông báo lỗi kỹ thuật tiếng Anh sang cụm từ báo lỗi dễ hiểu bằng tiếng Việt.
Mọi công thức PHẢI dùng định dạng mã chuẩn LaTeX và bọc bằng markdown math: $...$ hoặc $$...$$ (không dùng [ ... ]).
Luôn cách một khoảng trắng giữa văn bản và công thức toán.
Chỉ viết phần nội dung lời giải, không thêm tiêu đề markdown.
```

**Bước 2: Commit**
```bash
git add src/rag_core/agents/math.py
git commit -m "fix(math): tối ưu prompt Tiếng Việt, định dạng lại khoảng cách và xử lý lỗi undefined"
```

---

### Verification Plan (Kế Hoạch Kiểm Tra)

1. Khởi động hệ thống: Chạy backend `uvicorn src.api.main:app` và frontend `streamlit run src/frontend/app.py`.
2. Theo kịch bản trên hình ảnh lỗi, hãy nhập chuẩn nguyên câu chat vào giao diện: "Chứng minh tính lồi/lõm của hàm sigmoid σ(x) = 1/(1+e^-x)."
3. Quan sát và kiểm chứng kết quả trả về qua UI Streamlit:
   - Các chữ báo lỗi màu đỏ dạng `undefined` hoặc `null` biến mất.
   - Các công thức toán biểu diễn đẹp, không bị tụt dòng hoặc dính chặt vào các từ bên cạnh.
   - Nội dung được hiển thị bằng tiếng Việt 100%, không bị lọt thông báo lỗi thư viện SymPy từ tiếng Anh vào.
   - Lời giải được hiển thị ngay lập tức, không lọt block dư thừa ` ```markdown `.
