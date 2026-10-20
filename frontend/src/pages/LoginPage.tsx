import React, { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import {
  Film,
  Sparkles,
  Lock,
  Mail,
  Eye,
  EyeOff,
  ArrowRight,
  AlertCircle,
  Play,
  CheckCircle2,
} from 'lucide-react';

interface LoginPageProps {
  onNavigateToSignup: () => void;
  onNavigateToDemo: () => void;
  onSuccess: () => void;
}

export const LoginPage: React.FC<LoginPageProps> = ({
  onNavigateToSignup,
  onNavigateToDemo,
  onSuccess,
}) => {
  const { login, isAuthenticated, user, logout } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [rememberMe, setRememberMe] = useState(true);
  const [showPassword, setShowPassword] = useState(false);
  const [capsLockActive, setCapsLockActive] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  React.useEffect(() => {
    if (isAuthenticated) {
      onSuccess();
    }
  }, [isAuthenticated, onSuccess]);

  if (isAuthenticated && user) {
    return (
      <div className="min-h-[calc(100vh-4rem)] flex items-center justify-center p-4 sm:p-6 lg:p-8">
        <div className="w-full max-w-md bg-white border border-[#E2E8F0] rounded-2xl shadow-xl p-8 flex flex-col items-center text-center gap-5">
          <div className="w-16 h-16 rounded-2xl bg-indigo-50 border border-indigo-200 text-indigo-600 flex items-center justify-center font-bold text-xl shadow-sm">
            {user.full_name ? user.full_name.substring(0, 2).toUpperCase() : 'CP'}
          </div>
          <div>
            <span className="badge badge-emerald text-xs mb-2">Already Authenticated</span>
            <h2 className="text-xl font-bold text-[#0F172A]">Signed In as {user.full_name}</h2>
            <p className="text-xs text-[#64748B] mt-1">{user.email}</p>
          </div>
          <div className="w-full flex flex-col gap-2.5 pt-2">
            <button
              onClick={onSuccess}
              className="btn btn-primary w-full py-3 font-bold text-sm shadow-md"
            >
              <span>Continue to Studio Workspace</span>
              <ArrowRight className="w-4 h-4 ml-1" />
            </button>
            <button
              onClick={async () => {
                await logout();
              }}
              className="btn btn-secondary w-full py-2.5 text-xs font-semibold text-rose-600 hover:bg-rose-50 border-[#E2E8F0]"
            >
              <span>Sign Out / Switch Account</span>
            </button>
          </div>
        </div>
      </div>
    );
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.getModifierState('CapsLock')) {
      setCapsLockActive(true);
    } else {
      setCapsLockActive(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email.trim() || !password) {
      setError('Please provide both email address and password.');
      return;
    }

    setIsLoading(true);
    setError(null);
    try {
      await login({
        email: email.trim(),
        password,
        remember_me: rememberMe,
      });
      onSuccess();
    } catch (err: any) {
      setError(err.message || 'Invalid email or password. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-[calc(100vh-4rem)] flex items-center justify-center p-4 sm:p-6 lg:p-8">
      <div className="w-full max-w-5xl bg-white border border-[#E2E8F0] rounded-2xl shadow-xl overflow-hidden grid grid-cols-1 lg:grid-cols-12 min-h-[580px]">
        {/* Left Column: Form */}
        <div className="lg:col-span-6 p-6 sm:p-10 flex flex-col justify-between">
          <div>
            <div className="flex items-center gap-2.5 mb-8">
              <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-indigo-600 to-cyan-500 flex items-center justify-center text-white shadow-md shadow-indigo-500/20">
                <Film className="w-4 h-4" />
              </div>
              <span className="text-xl font-bold tracking-tight text-[#0F172A]">ClipPilot AI</span>
            </div>

            <h1 className="text-2xl font-bold text-[#0F172A] tracking-tight">Welcome back</h1>
            <p className="text-sm text-[#64748B] mt-1 mb-6">
              Sign in to manage your video projects, custom prompts, and export receipts.
            </p>

            {error && (
              <div className="mb-5 p-3.5 rounded-xl bg-rose-50 border border-rose-200 text-rose-700 text-xs flex items-start gap-2.5">
                <AlertCircle className="w-4 h-4 shrink-0 mt-0.5 text-rose-500" />
                <span className="leading-relaxed font-medium">{error}</span>
              </div>
            )}

            <form onSubmit={handleSubmit} className="flex flex-col gap-4">
              <div>
                <label className="block text-xs font-semibold text-[#334155] mb-1.5" htmlFor="login-email">
                  Email Address
                </label>
                <div className="relative">
                  <Mail className="w-4 h-4 text-[#94A3B8] absolute left-3.5 top-1/2 -translate-y-1/2 pointer-events-none z-10" />
                  <input
                    id="login-email"
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="creator@example.com"
                    className="form-input pl-11"
                    required
                    autoComplete="email"
                  />
                </div>
              </div>

              <div>
                <div className="flex items-center justify-between mb-1.5">
                  <label className="text-xs font-semibold text-[#334155]" htmlFor="login-password">
                    Password
                  </label>
                  {capsLockActive && (
                    <span className="text-[11px] font-semibold text-amber-600 flex items-center gap-1">
                      Caps Lock is on
                    </span>
                  )}
                </div>
                <div className="relative">
                  <Lock className="w-4 h-4 text-[#94A3B8] absolute left-3.5 top-1/2 -translate-y-1/2 pointer-events-none z-10" />
                  <input
                    id="login-password"
                    type={showPassword ? 'text' : 'password'}
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    onKeyDown={handleKeyDown}
                    placeholder="Enter your password"
                    className="form-input pl-11 pr-11"
                    required
                    autoComplete="current-password"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-3.5 top-1/2 -translate-y-1/2 text-[#94A3B8] hover:text-[#334155] p-1 z-10"
                    aria-label={showPassword ? 'Hide password' : 'Show password'}
                  >
                    {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
              </div>

              <div className="flex items-center justify-between pt-1">
                <label className="flex items-center gap-2 text-xs text-[#475569] cursor-pointer select-none">
                  <input
                    type="checkbox"
                    checked={rememberMe}
                    onChange={(e) => setRememberMe(e.target.checked)}
                    className="rounded border-[#CBD5E1] text-indigo-600 focus:ring-indigo-500"
                  />
                  <span>Remember me for 30 days</span>
                </label>
              </div>

              <button
                type="submit"
                disabled={isLoading}
                className="btn btn-primary w-full py-2.5 mt-2 font-bold text-sm shadow-md shadow-indigo-500/20"
              >
                {isLoading ? (
                  <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                ) : (
                  <>
                    <span>Sign In to Studio</span>
                    <ArrowRight className="w-4 h-4" />
                  </>
                )}
              </button>
            </form>
          </div>

          <div className="pt-6 border-t border-[#F1F5F9] mt-6 flex flex-col sm:flex-row items-center justify-between gap-3 text-xs text-[#64748B]">
            <p>
              Don't have an account?{' '}
              <button
                type="button"
                onClick={onNavigateToSignup}
                className="text-indigo-600 hover:text-indigo-700 font-bold hover:underline"
              >
                Sign up free
              </button>
            </p>

            <button
              type="button"
              onClick={onNavigateToDemo}
              className="text-[#475569] hover:text-[#0F172A] flex items-center gap-1 font-semibold hover:underline"
            >
              <Play className="w-3 h-3 text-cyan-600" />
              <span>Explore Demo</span>
            </button>
          </div>
        </div>

        {/* Right Column: Creative Artwork & Product Composition */}
        <div className="hidden lg:col-span-6 bg-gradient-to-br from-indigo-900 via-indigo-950 to-slate-900 p-10 lg:flex flex-col justify-between text-white relative overflow-hidden">
          {/* Subtle Ambient Decorative Circles */}
          <div className="absolute top-0 right-0 w-80 h-80 bg-cyan-500/10 rounded-full blur-3xl pointer-events-none" />
          <div className="absolute bottom-0 left-0 w-80 h-80 bg-indigo-500/15 rounded-full blur-3xl pointer-events-none" />

          <div className="relative z-10">
            <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-white/10 border border-white/15 text-indigo-200 text-xs font-semibold mb-6">
              <Sparkles className="w-3.5 h-3.5 text-cyan-300" />
              <span>Prompt-Based Video Editing Studio</span>
            </div>
            <h2 className="text-2xl xl:text-3xl font-extrabold tracking-tight leading-snug">
              Turn natural words into finished video edits.
            </h2>
            <p className="text-xs text-indigo-200/80 mt-2 leading-relaxed max-w-md">
              ClipPilot translates your prompts into discrete, validated FFmpeg steps with live silence detection and millisecond precision.
            </p>
          </div>

          {/* Interactive Preview Mockup Card */}
          <div className="relative z-10 my-8 bg-slate-900/80 backdrop-blur-md border border-white/10 rounded-xl p-5 shadow-2xl">
            <div className="flex items-center justify-between text-xs text-slate-400 mb-3 border-b border-white/10 pb-2">
              <span className="font-semibold text-slate-200">Live Edit Plan Demo</span>
              <span className="badge badge-emerald text-[10px]">Verified FFmpeg</span>
            </div>
            <p className="text-xs font-mono text-cyan-300 bg-black/40 p-2.5 rounded-lg border border-white/5 mb-3">
              "Trim first 3s, convert to 9:16 vertical for TikTok, boost volume by 50%"
            </p>
            <div className="grid grid-cols-3 gap-2 text-center text-[11px]">
              <div className="p-2 rounded bg-white/5 border border-white/5">
                <span className="text-slate-400 block text-[10px]">Action</span>
                <span className="font-semibold text-white">Fast Seek 3.0s</span>
              </div>
              <div className="p-2 rounded bg-white/5 border border-white/5">
                <span className="text-slate-400 block text-[10px]">Aspect</span>
                <span className="font-semibold text-white">9:16 Crop</span>
              </div>
              <div className="p-2 rounded bg-white/5 border border-white/5">
                <span className="text-slate-400 block text-[10px]">Audio</span>
                <span className="font-semibold text-white">150% Boost</span>
              </div>
            </div>
          </div>

          {/* Feature Checklist */}
          <div className="relative z-10 flex flex-col gap-2.5 text-xs text-indigo-100/90">
            <div className="flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
              <span>Genuine FFmpeg 9.0 media processing engine</span>
            </div>
            <div className="flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 text-cyan-400 shrink-0" />
              <span>Private local storage & audit receipts</span>
            </div>
            <div className="flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 text-indigo-300 shrink-0" />
              <span>User-specific project history isolation</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
