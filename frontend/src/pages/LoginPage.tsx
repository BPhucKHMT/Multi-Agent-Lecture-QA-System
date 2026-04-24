import React, { useState, type FormEvent } from "react";
import { useNavigate, useLocation, Link } from "react-router-dom";
import { ShieldIcon, MailIcon, LockIcon, EyeIcon, SparkIcon } from "../components/shared/Icons";
import { useConversationStore } from "../store/conversationStore";

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();
  const { login } = useConversationStore();
  const location = useLocation();

  // Nhận tin nhắn từ RegisterPage nếu có
  const successMessage = location.state?.message;

  const onSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError(null);
    setLoading(true);

    try {
      const response = await fetch("http://localhost:8000/api/v1/auth/login", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          email: email,
          password: password,
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Đăng nhập thất bại.");
      }

      // Sử dụng hàm login từ store để làm sạch state và tải dữ liệu mới
      await login(data.access_token, data.refresh_token);
      
      // Chuyển hướng sang Gateway
      navigate("/gateway");
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="relative min-h-screen text-slate-800 font-['Inter',sans-serif]">
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_left_top,rgba(0,123,255,0.08),transparent_42%),radial-gradient(circle_at_right_top,rgba(0,212,255,0.08),transparent_40%),radial-gradient(circle_at_right_bottom,rgba(40,167,69,0.08),transparent_40%),radial-gradient(circle_at_left_bottom,rgba(0,89,187,0.08),transparent_44%)]" />

      <header className="relative z-10 border-b border-slate-200/90 bg-white/80 px-4 py-4 backdrop-blur-sm sm:px-6">
        <div className="mx-auto flex w-full max-w-[1280px] items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="grid h-8 w-8 place-items-center rounded-lg bg-[#0070ea]">
              <SparkIcon />
            </div>
            <span className="font-['Plus_Jakarta_Sans',sans-serif] text-xl font-bold tracking-[-0.02em] text-blue-600">
              PUQ Chatbot
            </span>
          </div>
          <a href="#" className="text-sm font-medium text-slate-600 transition hover:text-slate-800">
            Về trang chủ
          </a>
        </div>
      </header>

      <main className="relative z-10 mx-auto flex min-h-[calc(100vh-165px)] w-full max-w-[1280px] items-center justify-center px-4 py-10 sm:px-6 sm:py-16">
        <div className="w-full max-w-[480px]">
          <div className="rounded-xl border border-[rgba(193,198,215,0.35)] bg-white p-6 shadow-[0_20px_25px_-5px_rgba(30,58,138,0.06),0_8px_10px_-6px_rgba(30,58,138,0.06)] sm:p-10">
            <div className="mb-8 flex flex-col items-center text-center">
              <div className="mb-4 grid h-16 w-16 place-items-center rounded-xl bg-[#b4ebff]">
                <ShieldIcon />
              </div>
              <h1 className="font-['Plus_Jakarta_Sans',sans-serif] text-4xl font-extrabold tracking-[-0.03em] text-[#181c23]">
                Chào mừng trở lại
              </h1>
              <p className="mt-2 text-base text-[#414754]">Tiếp tục hành trình học tập thông minh của bạn</p>
            </div>

            {successMessage && (
              <div className="mb-6 p-4 rounded-lg bg-green-50 border border-green-200 text-green-700 text-sm font-medium">
                {successMessage}
              </div>
            )}

            <form className="space-y-5" onSubmit={onSubmit}>
              <label className="block">
                <span className="mb-1.5 block text-sm font-semibold text-[#181c23]">Email đăng nhập</span>
                <span className="relative block">
                  <span className="pointer-events-none absolute inset-y-0 left-3 grid place-items-center">
                    <MailIcon />
                  </span>
                  <input
                    type="email"
                    required
                    value={email}
                    onChange={(event) => setEmail(event.target.value)}
                    className="w-full rounded-lg border border-[#c1c6d7] bg-white py-3 pl-10 pr-3 text-base outline-none transition placeholder:text-[#c1c6d7] focus:border-[#0070ea]"
                    placeholder="name@example.com"
                    autoComplete="email"
                  />
                </span>
              </label>

              <label className="block">
                <span className="mb-1.5 flex items-center justify-between text-sm font-semibold text-[#181c23]">
                  Mật khẩu
                  <a href="#" className="text-[#0059bb] hover:underline">
                    Quên mật khẩu?
                  </a>
                </span>
                <span className="relative block">
                  <span className="pointer-events-none absolute inset-y-0 left-3 grid place-items-center">
                    <LockIcon />
                  </span>
                  <input
                    type={showPassword ? "text" : "password"}
                    required
                    value={password}
                    onChange={(event) => setPassword(event.target.value)}
                    className="w-full rounded-lg border border-[#c1c6d7] bg-white py-3 pl-10 pr-10 text-base outline-none transition placeholder:text-[#c1c6d7] focus:border-[#0070ea]"
                    placeholder="••••••••"
                    autoComplete="current-password"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword((current) => !current)}
                    className="absolute inset-y-0 right-3 grid place-items-center"
                    aria-label="Toggle password visibility"
                  >
                    <EyeIcon />
                  </button>
                </span>
              </label>

              <button
                type="submit"
                disabled={loading}
                className="w-full rounded-lg bg-[#0070ea] py-3.5 text-lg font-bold text-[#fefcff] shadow-[0_10px_15px_-3px_rgba(0,89,187,0.2),0_4px_6px_-4px_rgba(0,89,187,0.2)] transition hover:bg-[#0065d2] disabled:opacity-70"
              >
                {loading ? "Đang xác thực..." : "Đăng nhập"}
              </button>
              
              {error && <p className="text-sm font-medium text-red-600">{error}</p>}
              <p className="text-xs text-slate-500">Mẹo: Bạn có thể đăng ký tài khoản mới bên dưới nếu chưa có.</p>
            </form>

            <div className="my-7 flex items-center gap-4 text-sm font-medium uppercase tracking-[0.05em] text-[#717786]">
              <div className="h-px flex-1 bg-[rgba(193,198,215,0.5)]" />
              <span>Hoặc tiếp tục với</span>
              <div className="h-px flex-1 bg-[rgba(193,198,215,0.5)]" />
            </div>

            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <button
                type="button"
                className="flex h-14 items-center justify-center gap-3 rounded-lg border border-[#c1c6d7] bg-white text-sm font-semibold text-[#181c23] transition hover:bg-slate-50"
              >
                <span className="grid h-5 w-5 place-items-center rounded-sm bg-black text-xs font-bold text-white">G</span>
                Google
              </button>
              <button
                type="button"
                className="flex h-14 items-center justify-center gap-3 rounded-lg border border-[#c1c6d7] bg-white text-sm font-semibold text-[#181c23] transition hover:bg-slate-50"
              >
                <span className="text-base font-black">GH</span>
                GitHub
              </button>
            </div>

            <p className="mt-7 text-center text-sm text-[#414754]">
              Chưa có tài khoản? <Link to="/register" className="font-bold text-[#0059bb] hover:underline">Tham gia ngay hôm nay</Link>
            </p>
          </div>

          <p className="mx-auto mt-8 max-w-[384px] text-center text-xs text-[#717786]">
            Bằng cách đăng nhập, bạn đồng ý với <a href="#" className="underline">Điều khoản dịch vụ</a> và{" "}
            <a href="#" className="underline">Chính sách bảo mật</a> của chúng tôi.
          </p>
        </div>
      </main>

      <footer className="relative z-10 border-t border-slate-200 bg-[#f8fafc] px-4 py-8 sm:px-6">
        <div className="mx-auto flex w-full max-w-[1280px] flex-col items-center justify-between gap-5 text-sm sm:flex-row">
          <p className="font-bold text-blue-600">Cognitive Luminary</p>
          <div className="flex flex-wrap items-center justify-center gap-5 text-[#64748b]">
            <a href="#" className="hover:underline">Chính sách bảo mật</a>
            <a href="#" className="hover:underline">Điều khoản dịch vụ</a>
            <a href="#" className="hover:underline">Trung tâm hỗ trợ</a>
            <a href="#" className="hover:underline">Liên hệ</a>
          </div>
          <p className="text-[#64748b]">© 2024 PUQ Chatbot. Bảo lưu mọi quyền.</p>
        </div>
      </footer>
    </div>
  );
}
