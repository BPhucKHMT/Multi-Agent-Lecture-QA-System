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
    "tính",
    "biểu thức",
)

# Từ khóa liên quan đến Giao tiếp (Greeting)
CHITCHAT_PATTERNS = (
    # ===== GREETING =====
    "xin chào", "chào", "hello", "hi", "hey", "alo", "ê",
    "chào bạn", "chào bot", "hey bot", "hi bot",
    "good morning", "good afternoon", "good evening",
    "morning", "yo", "sup", "what's up", "wassup",
    "chào buổi sáng", "chào buổi chiều", "chào buổi tối",

    # ===== FAREWELL =====
    "tạm biệt", "bye", "goodbye", "see you", "see ya",
    "hẹn gặp lại", "bai", "bb", "good night",
    "tôi đi đây", "mình đi nhé", "out đây",

    # ===== THANKS =====
    "cảm ơn", "thanks", "thank you", "thank u",
    "tks", "ty", "thx",
    "cảm ơn bạn", "cảm ơn nhiều", "thank you so much",
    "ok cảm ơn", "thanks bro", "thank you bot",

    # ===== IDENTITY =====
    "bạn là ai", "mày là ai", "who are you",
    "giới thiệu bản thân", "bạn tên gì",
    "what are you", "are you human",
    "bạn là bot à", "ai tạo ra bạn",

    # ===== CAPABILITY =====
    "bạn làm được gì", "you can do what",
    "help", "giúp tôi", "có thể làm gì",
    "how can you help", "hướng dẫn",
    "tôi có thể hỏi gì", "use bạn sao",

    # ===== STATUS =====
    "bạn khỏe không", "how are you", "how are you doing",
    "ổn không", "today thế nào",
    "bạn đang làm gì", "what are you doing",
    "có rảnh không",

    # ===== FUN / JOKE =====
    "kể chuyện cười", "tell me a joke",
    "joke", "funny", "make me laugh",
    "giải trí", "chán quá", "bored",
    "có gì vui không",

    # ===== CASUAL / FILLER =====
    "ừ", "ok", "ừm", "hmm", "huh",
    "à", "ờ", "uh", "um",
    "được", "ok luôn", "fine",
    "k", "ko", "không", "no",
    "yes", "yeah", "yep",

    # ===== COMPLIMENT =====
    "bạn giỏi", "you are smart",
    "hay quá", "good answer",
    "nice one", "đỉnh", "xịn",
    "ok đấy", "tốt", "well done",

    # ===== TOXIC / NEGATIVE =====
    "ngu", "dốt", "stupid", "idiot",
    "bot ngu", "mày ngu",
    "vô dụng", "useless",
    "trash", "rác",

    # ===== META =====
    "bạn dùng model gì",
    "are you gpt",
    "bạn có dùng openai không",
    "backend là gì",
    "how you work",
    "cách bạn hoạt động",
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
    "đố",
    "bài tập",
)

# Từ khóa liên quan đến Lập trình (CodeAssistant)
CODING_PATTERNS = (
    "code",
    "lập trình",
    "lap trinh",
    "java",
    "c++",
    "sql",
    "sửa lỗi",
    "sua loi",
    "viết giúp",
    "script",
    "hướng dẫn code",
    "class",
    "vòng lặp",
)

FORCE_TUTOR_PATTERNS = (
    "diffusion",
    "transformer",
    "attention",
    "gradient",
    "loss",
    "activation",
    "neuron",
    "backprop",
    "tối ưu hóa",
    "hàm mất mát",
    "hàm loss",
    "chương",
    "bài giảng",
    "slide",
)

