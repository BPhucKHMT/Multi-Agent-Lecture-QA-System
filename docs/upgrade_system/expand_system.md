# Kế Hoạch Mở Rộng Hệ Thống RAG QABot (Multi-Agent & Multi-Page)

Tài liệu này mô tả kiến trúc mở rộng để nâng cấp RAG QABot thành nền tảng học tập thông minh cho các môn Machine Learning / Deep Learning.

---

## 1. Phân Tách Không Gian Học Tập (Multi-Page)

### 1.1. Không gian Thư viện & Tóm Tắt (Summary Hub)
- **Tính chất:** Trang thao tác tĩnh (Dashboard), hoạt động độc lập bằng các API endpoint trực tiếp.
- **Ý tưởng:** Hiển thị danh mục bài giảng đã có trong DB. Sinh viên chọn video → hệ thống gom toàn bộ chunks của video đó và tạo bản tóm tắt thông qua một API độc lập (bỏ qua hệ thống điều phối hội thoại).
- **Giá trị:** Chính xác (truy vấn trực tiếp DB theo ID video), nhanh, không cần đối thoại.

### 1.2. Không gian Thảo luận Đa Đặc Vụ (Multi-Agent Chatspace)
- **Tính chất:** Trang hội thoại tự nhiên (Chat).
- **Ý tưởng:** Sinh viên đặt câu hỏi tự do. Supervisor Agent đứng sau phân loại intent và điều hướng đến đúng Agent.

---

## 2. Kiến Trúc Multi-Agent Chatspace: Supervisor + Sub-graphs

### 2.1. Mô hình được chọn
**Supervisor (Tool-Calling) + Sub-graphs** — Supervisor LLM route câu hỏi, mỗi sub-agent là một sub-graph LangGraph tự quản lý logic nội bộ.

- Supervisor là LLM agent chạy trong vòng lặp (loop), gọi sub-agents thông qua tool-calling.
- Sub-agents **đơn giản** (Tutor, Quiz) được gọi như tools thông thường.
- Sub-agents **phức tạp** (Coding, Math) là **sub-graphs với loop nội bộ** — tự xử lý retry, verification mà Supervisor không cần hiểu chi tiết.
- Supervisor có thể gọi nhiều sub-agents liên tiếp cho các câu hỏi phức hợp (VD: "implement và tạo quiz").

### 2.2. Tại sao chọn kiến trúc này?
- **Mở rộng tự nhiên từ code hiện tại:** Hệ thống đã có `bind_tools([Retrieve])` và `route_decision`. Thêm tools + sub-graphs mới.
- **Hỗ trợ internal loops:** Coding Agent cần retry loop (sinh code → chạy → lỗi → sửa → chạy lại). Sub-graph xử lý tự nhiên mà Supervisor không cần hiểu code errors.
- **Supervisor chỉ cần route:** Không phải xử lý logic phức tạp bên trong mỗi agent. Mỗi sub-agent tự quản lý workflow riêng, trả về kết quả cuối cùng.
- **Testable riêng lẻ:** Mỗi sub-graph có thể test độc lập (unit test) mà không cần chạy toàn bộ pipeline.

### 2.3. So sánh với các kiến trúc khác

| Kiến trúc | Đánh giá |
|---|---|
| **Supervisor + Sub-graphs** ✅ | Phù hợp nhất. Route đơn giản, sub-agents tự quản lý loop, testable riêng lẻ. |
| Flat Supervisor (all tools same level) | Supervisor phải hiểu internal logic của mọi agent (VD: khi nào retry code). Prompt quá phức tạp. |
| Supervisor + Planner | Over-engineering. Supervisor loop đã xử lý được multi-agent queries tuần tự. Planner chỉ thêm LLM call overhead. |
| Hierarchical (nhiều tầng) | Quá phức tạp cho quy mô 4 Agents. |
| Swarm (agent tự chuyển giao) | Khó kiểm soát, khó debug. |

### 2.4. Tại sao không cần Planner?

**Câu hỏi:** Khi user yêu cầu phức hợp như *"Implement gradient descent, chứng minh convergence, và tạo 5 câu quiz"*, có cần Planner phân rã thành các bước?

**Trả lời: Không.** Supervisor loop xử lý tự nhiên:
1. Supervisor gọi `CodingAgent` → nhận code + output
2. Supervisor gọi `MathAgent` → nhận proof
3. Supervisor gọi `QuizAgent` → nhận quiz
4. Supervisor tổng hợp → trả về user

Planner chỉ cần khi thứ tự thực thi **không rõ ràng** hoặc cần **phân rã động**. Các tác vụ trong hệ thống này có chuỗi hành động dự đoán được, Supervisor tự quyết định thứ tự qua tool-calling.

---

## 3. Các Agent Dưới Quyền Supervisor (Chatspace)

### 3.1. Tutor Agent (Có sẵn — Nâng cấp Prompt)
- **Tool name:** `AskTutor`
- **Loại:** Simple tool (không cần sub-graph)
- **Tools nội bộ:** `Retrieve` (hybrid search + reranker)
- **Vai trò:** Trả lời lý thuyết, giải thích khái niệm, so sánh, giải thích đơn giản (ELI5).
- **Prompt nâng cấp:** Tự nhận diện format phù hợp (hỏi so sánh → bảng markdown, nói "không hiểu" → giải thích đơn giản, hỏi "khác gì" → bảng so sánh).
- **Output:** Text markdown + citation [0], [1], ... với video URL + timestamp.

### 3.2. Coding Agent (MỚI)
- **Tool name:** `CodeAssistant`
- **Loại:** Sub-graph với internal loop
- **Tools nội bộ:** `Retrieve` + `ExecuteCode`
- **Cách hoạt động:**
  1. Nhận yêu cầu code từ Supervisor
  2. Gọi `Retrieve` lấy context bài giảng về thuật toán
  3. LLM sinh code Python (PyTorch/NumPy/sklearn) dựa trên context
  4. Gọi `ExecuteCode` chạy trong sandbox (subprocess + timeout)
  5. Nếu lỗi → LLM đọc stderr → sửa code → `ExecuteCode` lại (max 3 lần)
  6. Trả về: code + stdout + hình ảnh (nếu có) + giải thích + citation
- **ExecuteCode sandbox:**
  - Python subprocess với timeout (30s) và memory limit
  - Package whitelist: numpy, torch, sklearn, matplotlib, sympy, pandas
  - Capture stdout, stderr, và **matplotlib figures** (save → base64)
  - Isolation: không truy cập filesystem ngoài sandbox
- **Use cases:**
  - "Implement gradient descent cho linear regression"
  - "Viết code training loop cho CNN"
  - "Vẽ decision boundary của SVM"
  - "Debug code backpropagation này cho tôi"
- **Output format:**
  ```python
  {
      "text": str,              # Giải thích + citation
      "code": str,              # Code Python
      "stdout": str,            # Output từ execution
      "images": List[str],      # Base64 encoded matplotlib figures
      "execution_success": bool,
      "video_url": List[str],   # Citation sources
      "title": List[str],
      "start_timestamp": List[str],
      "end_timestamp": List[str],
      "confidence": List[str],
      "type": "coding"
  }
  ```

### 3.3. Math Agent (MỚI)
- **Tool name:** `MathSolver`
- **Loại:** Sub-graph với verification step
- **Tools nội bộ:** `Retrieve` + `ExecuteCode` (sympy)
- **Cách hoạt động:**
  1. Nhận câu hỏi toán từ Supervisor
  2. Gọi `Retrieve` lấy context bài giảng (công thức, chứng minh từ transcript)
  3. LLM sinh derivation step-by-step với LaTeX formatting
  4. Gọi `ExecuteCode(sympy)` để **verify kết quả** toán học
  5. Trả về: derivation + verification result + citation
- **Use cases:**
  - "Chứng minh đạo hàm của sigmoid = σ(1-σ)"
  - "Derive gradient của cross-entropy loss"
  - "Step-by-step backpropagation cho mạng 2 layers"
  - "Tính Jacobian của softmax"
- **Output format:**
  ```python
  {
      "text": str,              # Step-by-step derivation với LaTeX
      "steps": List[dict],      # [{"step": 1, "equation": "...", "explanation": "..."}]
      "verification": str,      # Kết quả sympy verify ("✅ Verified" / "❌ Mismatch")
      "sympy_code": str,        # Code sympy đã chạy
      "video_url": List[str],
      "title": List[str],
      "start_timestamp": List[str],
      "end_timestamp": List[str],
      "confidence": List[str],
      "type": "math"
  }
  ```

### 3.4. Quiz Agent (MỚI)
- **Tool name:** `GenerateQuiz`
- **Loại:** Simple tool 
- **Tham số:** `topic` (chủ đề), `num_questions` (số câu hỏi)
- **Cách hoạt động:** Supervisor gọi `Retrieve` lấy context → gọi `GenerateQuiz` sinh câu hỏi trắc nghiệm dạng JSON.
- **Output format:**
  ```python
  {
      "questions": [
          {
              "question": str,
              "options": ["A", "B", "C", "D"],
              "correct": str,
              "explanation": str
          }
      ],
      "video_url": List[str],
      "title": List[str],
      "start_timestamp": List[str],
      "end_timestamp": List[str],
      "confidence": List[str],
      "type": "quiz"
  }
  ```

---

## 4. Agent Độc Lập (Summary Hub)

### 4.1. Summarize Agent (MỚI)
- **Tính chất:** Pipeline độc lập, API endpoint riêng (`POST /summarize`), **KHÔNG** nhận định tuyến từ Supervisor.
- **Loại:** Simple Chain / Document Chain
- **Tham số đầu vào:** `video_title` hoặc `video_id` (được trigger thông qua thao tác nhấp nút trên UI, thay vì câu lệnh hội thoại).
- **Cách hoạt động:** Quét xuyên suốt toàn bộ chunks của video thay vì semantic search sử dụng ChromaDB Metadata Filter, gộp toàn bộ text vào LLM để phân tích và tóm tắt thành tài liệu chi tiết bám sát nội dung.
- **Output format:** Dạng bài viết tóm tắt chi tiết phục vụ cho khu vực đọc tĩnh học liệu của sinh viên.

---

## 5. Bảng Phân Tích Mạng Lưới Agent Cập Nhật

| Agent | Module | Loại | Quyền Điều Phối Định Tuyến |
|---|---|---|---|
| **Tutor Agent** | Chatspace | Lập luận trả lời Text | **Supervisor** |
| **Coding Agent** | Chatspace | Sub-Graph & Sandbox | **Supervisor** |
| **Math Agent** | Chatspace | Sub-Graph & Verification | **Supervisor** |
| **Quiz Agent** | Chatspace | Structured Output | **Supervisor** |
| **Summarize Agent**| Summary Hub | Pipeline gộp Text tĩnh| **ĐỘC LẬP (API / Dashboard)**|

---

## 6. Luồng Xử Lý (LangGraph Flow của Chatspace)

### 6.1. Tổng quan Supervisor Workflow

```
START → [Supervisor Agent]
              │
              ├── tool_call: AskTutor        → [Tutor Node]        → (loop back hoặc END)
              ├── tool_call: CodeAssistant    → [Coding Sub-graph]  → (loop back hoặc END)
              ├── tool_call: MathSolver       → [Math Sub-graph]    → (loop back hoặc END)
              ├── tool_call: GenerateQuiz     → [Quiz Node]         → END
              └── no tool_call               → [Direct Answer]     → END
```

### 6.2. Cơ Chế Tương Tác Chéo (Trải nghiệm người dùng Dashboard -> Chat)

UX chuyển đổi từ Dashboard tĩnh sang Chatspace động được duy trì qua kỹ thuật **Chuyển hướng mang theo ngữ cảnh (Context Injection)**:

1. **Tại Summary Hub:** Giao diện cho phép chọn xem video và nhấn nút "Tóm tắt" (hệ thống gửi yêu cầu xuống `Summarize Agent` chuyên biệt để đọc tài liệu tĩnh). Ngay bên dưới kết quả tóm tắt của video đó sẽ xuất hiện nút **💬 Thảo luận & Làm bài tập về video này**.
2. **Chuyển hóa:** Khi nhấn nút, hệ thống điều hướng sinh viên sang Trang Chatspace.
3. **Bơm ngữ cảnh ngầm (Context Injection):** Hệ thống âm thầm chèn một block tin nhắn ngữ cảnh (System Context Message) vào trong luồng trò chuyện hiện tại của LangGraph báo rằng (*"Đang thảo luận chi tiết về video: 'Giới thiệu XYZ'"*).
4. **Phát huy sức mạnh tại Chatspace:** Lúc này sinh viên dùng Chat bình thường ("Liệt kê thêm công thức bài này" hay "Cho tôi 5 câu đố"). Bằng việc có thông tin ẩn đi kèm thì Supervisor đã dễ dàng truyền lệnh xuống Math Agent hay Quiz Agent chỉ lọc riêng trong bài để tiếp tục duy trì câu chuyện chặt chẽ.
