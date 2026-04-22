# ⚛️ RAG QABot Frontend

Giao diện người dùng cho hệ thống hỏi đáp bài giảng (RAG) sử dụng kiến trúc Multi-Agent. Được xây dựng với các công nghệ hiện đại nhằm tối ưu hóa trải nghiệm tương tác AI mượt mà và trực quan.

---

## 🚀 Tính năng chính

- **Gateway Selector**: Cổng lựa chọn không gian làm việc chuyên biệt (Chatspace hoặc Summary Hub).
- **Summary Hub**: Tóm tắt video AI với Skeleton UI chuyên nghiệp và khả năng chuyển đổi trực tiếp sang thảo luận.
- **Chatspace**: Giao diện hội thoại đa nhiệm, hỗ trợ stream nội dung thời gian thực và hiển thị nguồn tham khảo (Citations).
- **Markdown & LaTeX Support**: Hiển thị đẹp mắt các đoạn code, công thức toán học và bảng biểu.
- **Responsive Design**: Tối ưu hóa cho nhiều kích thước màn hình với Tailwind CSS và Framer Motion.
- **Vietnamese Localization**: 100% giao diện đã được Việt hóa.

---

## 🛠️ Công nghệ sử dụng (Tech Stack)

### Core
- **Framework**: React 18 + Vite
- **Language**: TypeScript
- **Routing**: React Router Dom v7

### UI/UX
- **Styling**: Tailwind CSS
- **Animations**: Framer Motion
- **Icons**: Lucide React
- **Typography**: @tailwindcss/typography

### AI & Data Rendering
- **Markdown**: react-markdown + remark-gfm
- **Math/LaTeX**: katex + remark-math + rehype-katex
- **Code Highlighting**: react-syntax-highlighter

### State Management
- **Store**: Zustand (Custom Context Provider Implementation)

---

## 📁 Cấu trúc thư mục

```
frontend/
├── src/
│   ├── app/                # Cấu hình Routing, Layouts và Providers
│   ├── components/         # Thành phần giao diện tái sử dụng
│   │   ├── chat/           # MarkdownRenderer, MessageList, ChatInput, v.v.
│   │   ├── sidebar/        # ConversationSidebar, Navigation
│   │   └── shared/         # Các icons và thành phần chung
│   ├── lib/                # Logic nghiệp vụ và API
│   │   ├── api/            # Chat API, Video API, Summary API
│   │   └── utils/          # Các hàm tiện ích (Format, Citation)
│   ├── pages/              # Các trang chính (Login, Gateway, Workspace)
│   ├── store/              # Quản lý trạng thái toàn cục (Conversation Context)
│   ├── types/              # Định nghĩa TypeScript (API, RAG, App)
│   └── styles/             # Cấu hình CSS toàn cục
└── package.json
```

---

## ⚙️ Cài đặt và Chạy thử

### 1. Cài đặt dependencies
```bash
npm install
```

### 2. Cấu hình môi trường
Đảm bảo Backend đang chạy tại `http://localhost:8000` (hoặc cấu hình lại trong `src/lib/api/`).

### 3. Chạy chế độ Development
```bash
npm run dev
```

### 4. Build sản phẩm
```bash
npm run build
```

---

## 🧪 Kiểm thử (Testing)
Dự án sử dụng **Vitest** để kiểm thử logic Store và Utils.
```bash
npm run test
```

---

## 📝 Quy ước code
- **Component**: Ưu tiên Functional Components và Hooks.
- **Styling**: Sử dụng Tailwind CSS class, hạn chế viết CSS thuần.
- **State**: Các trạng thái liên quan đến hội thoại phải được quản lý qua `useConversationStore`.
- **Localization**: Tất cả chuỗi văn bản hiển thị phải viết bằng tiếng Việt.
