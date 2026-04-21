# Chiến lược cải tiến Math Agent thành Math Tutor thực tế

## 1. Mục tiêu

Math agent cần đóng vai trò **tutor** (dạy học) thay vì chỉ là solver:

- Giải đúng và có kiểm chứng.
- Giải thích để người học hiểu được cách làm.
- Tạo cơ hội tự luyện để người học tự giải lại.
- Vẫn giữ nguyên contract response hiện tại để tương thích UI/API.

## 2. Hiện trạng

Math agent hiện tại (`src/rag_core/agents/math.py`) có flow:
1. Sinh code Sympy từ câu hỏi.
2. Chạy code để verify.
3. Tạo lời giải chi tiết từ kết quả verify.

Flow này tốt cho độ đúng, nhưng chưa đủ vai trò sư phạm:
- Thiếu phần định hướng học.
- Thiếu phần tự luyện.
- Chưa tách rõ phần "dạy học" và phần "kiểm chứng".

## 3. Chiến lược Phase 1 (không đổi schema public)

### 3.1. Nguyên tắc

1. **Tutor-first**: ưu tiên giúp người học hiểu.
2. **Verification-backed**: nếu verify được thì nêu rõ.
3. **Honest-failure**: nếu verify lỗi thì nói rõ giới hạn, không khẳng định chắc chắn.
4. **Backward-compatible**: giữ nguyên các key response hiện có.

### 3.2. Cấu trúc text chuẩn (4 block)

Mỗi phản hồi `type="math"` cần có 4 phần trong `text`:

1. **Mục tiêu học**: bài này học gì.
2. **Giải theo bước**: các bước biến đổi/chứng minh.
3. **Kiểm chứng kết quả**: trạng thái verify từ Sympy.
4. **Tự luyện nhanh**: 1 bài tương tự + 1 gợi ý.

> Frontend không cần thay đổi vì mọi cải tiến đều nằm trong `text`.

## 4. Chiến lược retrieval cho Math Tutor

### 4.1. Có cần retrieval không?

- **Không bắt buộc** cho bài toán thuần toán (để nhanh và tiết kiệm chi phí).
- **Nên bật retrieval có chọn lọc** khi câu hỏi cần bám bài giảng (thuật ngữ môn học, context video, yêu cầu trích dẫn).

### 4.2. Điều kiện bật retrieval (đề xuất)

Bật retrieval nếu query có tín hiệu:
- Hỏi theo ngữ cảnh môn/video cụ thể.
- Yêu cầu dẫn nguồn/citation.
- Cần nhắc lại công thức theo bài giảng đã dạy.

Không bật retrieval nếu query chỉ là:
- Tính toán/derive/chứng minh thuần toán, độc lập với transcript.

## 5. Kế hoạch nâng cấp kỹ thuật

## 5.1. `src/rag_core/agents/math.py`

1. Tách prompt theo 2 mục tiêu:
   - Prompt sinh Sympy để verify.
   - Prompt tutor để tạo 4 block text rõ ràng.
2. Chuẩn hóa message "verify thành công/thất bại".
3. Bổ sung phần tự luyện trong response text.
4. (Phase 1.5) thêm retrieval có điều kiện và remap citation đúng index.

## 5.2. `src/rag_core/lang_graph_rag.py`

- Giữ routing hiện tại (`MathSolver`) cho phase 1.
- Chỉ điều chỉnh nếu cần truyền thêm signal nội bộ cho retrieval mode.

## 6. Test và đo chất lượng

### 6.1. Unit test cho Math Agent

- Có đủ 4 block sư phạm trong `text`.
- Có section kiểm chứng rõ ràng.
- Verify lỗi vẫn trả phản hồi mang tính hướng dẫn.

### 6.2. Integration test với Supervisor

- Query toán route đúng vào `MathSolver`.
- Không phá contract response chung.
- Nếu có citation thì index và metadata arrays luôn đồng bộ.

## 7. KPI rollout

1. **Tutor-format rate**: % phản hồi có đủ 4 block.
2. **Verification success rate**: % ca chạy Sympy thành công.
3. **Self-practice coverage**: % phản hồi có bài tự luyện.
4. **Learner clarity feedback**: điểm đánh giá "dễ hiểu".

## 8. Checklist triển khai

- [x] Rà soát gap giữa math solver và math tutor.
- [x] Chốt hướng phase 1: tutor-first, giữ nguyên response contract.
- [x] Hoàn thành tài liệu chiến lược này.
- [x] Nâng cấp `src/rag_core/agents/math.py` theo 4 block tutor text.
- [x] Bổ sung test unit/integration cho tutor behavior.
- [x] Sửa lỗi verify do `UnicodeEncodeError` khi sandbox in Unicode trên Windows (cp1252).
- [x] Khi verify thất bại, vẫn sinh phần giải thích theo query (không trả generic text).
- [x] Khi LLM trả lời placeholder lỗi như `undefined`, tự động regenerate/fallback để không rò lỗi ra UI.
- [x] Bắt được cả placeholder bị tách ký tự (vd: `u n d e f i n e d`) để vẫn regenerate đúng.
- [x] Chuẩn hóa hiển thị công thức: convert dạng `[ ... ]`, `\\[ ... \\]`, `\\( ... \\)` sang `$...$/$$...$$` để frontend render đúng.
- [x] Làm sạch block kiểm chứng: normalize Unicode + thay thế cụm tiếng Anh phổ biến sang tiếng Việt để tránh output lẫn ngôn ngữ.
- [x] Ép chuẩn công thức LaTeX trên toàn response math (mục tiêu học + giải tay + kiểm chứng), không chỉ riêng phần giải tay.
- [x] Thêm lớp an toàn cuối để placeholder (`undefined`/`null`, kể cả dạng tách ký tự) không thể rò ra response cuối.
- [ ] Triển khai retrieval có chọn lọc cho query cần grounding.
- [ ] Theo dõi KPI và cập nhật lại tài liệu sau rollout.
