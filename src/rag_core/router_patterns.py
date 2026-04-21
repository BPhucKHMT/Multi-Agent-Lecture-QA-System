"""
Module lưu trữ các bộ từ khóa (Patterns) phục vụ cho việc điều hướng (Routing) 
giữa các Agent trong hệ thống Multi-Agent RAG.
"""

# Từ khóa liên quan đến Toán học (MathSolver)
FORCE_MATH_PATTERNS = (
    "chứng minh",
    "chung minh",
    "đạo hàm",
    "dao ham",
    "tích phân",
    "tich phan",
    "giải phương trình",
    "giai phuong trinh",
    "bất đẳng thức",
    "bat dang thuc",
    "hàm lồi",
    "ham loi",
    "delta",
)

# Từ khóa liên quan đến Giao tiếp (Greeting)
GREETING_PATTERNS = (
    "xin chào",
    "chào",
    "hello",
    "hi",
    "hey",
)

# Từ khóa liên quan đến Quiz/Trắc nghiệm (GenerateQuiz)
QUIZ_PATTERNS = (
    "quiz",
    "trắc nghiệm",
    "trac nghiem",
    "kiểm tra",
    "kiem tra",
    "câu hỏi ôn tập",
    "cau hoi on tap",
)

# Từ khóa liên quan đến Lập trình (CodeAssistant)
CODING_PATTERNS = (
    "code",
    "lập trình",
    "lap trinh",
    "python",
    "java",
    "c++",
    "sql",
    "sửa lỗi",
    "sua loi",
)
