import React, { useState, type FormEvent } from "react";
import { useNavigate, Link } from "react-router-dom";
import { ShieldIcon, MailIcon, LockIcon, EyeIcon, SparkIcon, UserIcon } from "../components/shared/Icons";

export default function RegisterPage() {
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const onSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError(null);

    if (password !== confirmPassword) {
      setError("Mật khẩu xác nhận không khớp.");
      return;
    }

    setLoading(true);
    try {
      const response = await fetch("/api/v1/auth/register", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          email: email,
          username: username,
          password: password,
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Đăng ký thất bại. Vui lòng thử lại.");
      }

      // Đăng ký thành công, chuyển hướng về trang login
      navigate("/login", { state: { message: "Đăng ký thành công! Vui lòng đăng nhập." } });
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="relative min-h-screen text-slate-800 font-['Inter',sans-serif]">
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_left_top,rgba(13,148,136,0.06),transparent_42%),radial-gradient(circle_at_right_top,rgba(15,23,42,0.04),transparent_40%),radial-gradient(circle_at_right_bottom,rgba(16,185,129,0.04),transparent_40%),radial-gradient(circle_at_left_bottom,rgba(15,23,42,0.05),transparent_44%)]" />

      <header className="relative z-10 border-b border-slate-200/90 bg-white/80 px-4 py-4 backdrop-blur-sm sm:px-6">
        <div className="mx-auto flex w-full max-w-[1280px] items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="grid h-8 w-8 place-items-center rounded-lg bg-teal-600">
              <SparkIcon />
            </div>
            <span className="font-['Plus_Jakarta_Sans',sans-serif] text-xl font-bold tracking-[-0.02em] text-slate-900">
              PUQ Chatbot
            </span>
          </div>
          <Link to="/login" className="text-sm font-medium text-slate-600 transition hover:text-slate-800">
            Quay lại Đăng nhập
          </Link>
        </div>
      </header>

      <main className="relative z-10 mx-auto flex min-h-[calc(100vh-165px)] w-full max-w-[1280px] items-center justify-center px-4 py-10 sm:px-6 sm:py-16">
        <div className="w-full max-w-[480px]">
          <div className="rounded-xl border border-[rgba(193,198,215,0.35)] bg-white p-6 shadow-[0_20px_25px_-5px_rgba(15,23,42,0.04),0_8px_10px_-6px_rgba(15,23,42,0.04)] sm:p-10">
            <div className="mb-8 flex flex-col items-center text-center">
              <div className="mb-4 grid h-16 w-16 place-items-center rounded-xl bg-teal-50 border border-teal-100 text-teal-600">
                <UserIcon />
              </div>
              <h1 className="font-['Plus_Jakarta_Sans',sans-serif] text-3xl font-extrabold tracking-[-0.03em] text-[#181c23]">
                Tạo tài khoản mới
              </h1>
              <p className="mt-2 text-base text-[#414754]">Bắt đầu trải nghiệm học tập AI cá nhân hóa</p>
            </div>

            <form className="space-y-4" onSubmit={onSubmit}>
              <label className="block">
                <span className="mb-1.5 block text-sm font-semibold text-[#181c23]">Tên người dùng</span>
                <span className="relative block">
                  <span className="pointer-events-none absolute inset-y-0 left-3 grid place-items-center">
                    <UserIcon size={18} />
                  </span>
                  <input
                    type="text"
                    required
                    value={username}
                    onChange={(e) => setUsername(e.target.value)}
                    className="w-full rounded-lg border border-[#c1c6d7] bg-white py-2.5 pl-10 pr-3 text-base outline-none transition placeholder:text-[#c1c6d7] focus:border-slate-800 focus:ring-1 focus:ring-slate-800"
                    placeholder="example_user"
                  />
                </span>
              </label>

              <label className="block">
                <span className="mb-1.5 block text-sm font-semibold text-[#181c23]">Email</span>
                <span className="relative block">
                  <span className="pointer-events-none absolute inset-y-0 left-3 grid place-items-center">
                    <MailIcon />
                  </span>
                  <input
                    type="email"
                    required
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    className="w-full rounded-lg border border-[#c1c6d7] bg-white py-2.5 pl-10 pr-3 text-base outline-none transition placeholder:text-[#c1c6d7] focus:border-slate-800 focus:ring-1 focus:ring-slate-800"
                    placeholder="name@example.com"
                  />
                </span>
              </label>

              <label className="block">
                <span className="mb-1.5 block text-sm font-semibold text-[#181c23]">Mật khẩu</span>
                <span className="relative block">
                  <span className="pointer-events-none absolute inset-y-0 left-3 grid place-items-center">
                    <LockIcon />
                  </span>
                  <input
                    type={showPassword ? "text" : "password"}
                    required
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    className="w-full rounded-lg border border-[#c1c6d7] bg-white py-2.5 pl-10 pr-10 text-base outline-none transition placeholder:text-[#c1c6d7] focus:border-slate-800 focus:ring-1 focus:ring-slate-800"
                    placeholder="••••••••"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute inset-y-0 right-3 grid place-items-center"
                  >
                    <EyeIcon />
                  </button>
                </span>
              </label>

              <label className="block">
                <span className="mb-1.5 block text-sm font-semibold text-[#181c23]">Xác nhận mật khẩu</span>
                <span className="relative block">
                  <span className="pointer-events-none absolute inset-y-0 left-3 grid place-items-center">
                    <LockIcon />
                  </span>
                  <input
                    type={showPassword ? "text" : "password"}
                    required
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    className="w-full rounded-lg border border-[#c1c6d7] bg-white py-2.5 pl-10 pr-3 text-base outline-none transition placeholder:text-[#c1c6d7] focus:border-slate-800 focus:ring-1 focus:ring-slate-800"
                    placeholder="••••••••"
                  />
                </span>
              </label>

              <button
                type="submit"
                disabled={loading}
                className="w-full mt-4 rounded-lg bg-slate-900 py-3 text-lg font-bold text-white shadow-md shadow-slate-900/10 transition hover:bg-slate-800 disabled:opacity-70"
              >
                {loading ? "Đang đăng ký..." : "Đăng ký"}
              </button>

              {error && <p className="text-sm font-medium text-red-600 mt-2">{error}</p>}
            </form>

            <p className="mt-7 text-center text-sm text-[#414754]">
              Đã có tài khoản? <Link to="/login" className="font-bold text-teal-600 hover:text-teal-700 hover:underline">Đăng nhập ngay</Link>
            </p>
          </div>
        </div>
      </main>

      <footer className="relative z-10 border-t border-slate-200 bg-[#f8fafc] px-4 py-8 sm:px-6">
        <div className="mx-auto flex w-full max-w-[1280px] flex-col items-center justify-between gap-5 text-sm sm:flex-row">
          <p className="font-bold text-teal-600">Cognitive Luminary</p>
          <p className="text-[#64748b]">© 2024 PUQ Chatbot. Bảo lưu mọi quyền.</p>
        </div>
      </footer>
    </div>
  );
}
