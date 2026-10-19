import React, { useState, useMemo } from 'react';
import { useAuth } from '../context/AuthContext';
import {
  Film,
  Sparkles,
  Lock,
  Mail,
  User as UserIcon,
  Eye,
  EyeOff,
  ArrowRight,
  AlertCircle,
  CheckCircle2,
  XCircle,
  ShieldCheck,
  Zap,
} from 'lucide-react';

interface SignupPageProps {
  onNavigateToLogin: () => void;
  onNavigateToDemo: () => void;
  onSuccess: () => void;
}

export const SignupPage: React.FC<SignupPageProps> = ({
  onNavigateToLogin,
  onNavigateToDemo,
  onSuccess,
}) => {
  const { signup } = useAuth();
  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [agreeTerms, setAgreeTerms] = useState(true);
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Real-time password criteria
  const passwordCriteria = useMemo(() => {
    return {
      hasMinLength: password.length >= 8,
      hasLetter: /[A-Za-z]/.test(password),
      hasDigit: /\d/.test(password),
      passwordsMatch: password.length > 0 && password === confirmPassword,
    };
  }, [password, confirmPassword]);

  const strengthScore = useMemo(() => {
    let score = 0;
    if (passwordCriteria.hasMinLength) score++;
    if (passwordCriteria.hasLetter) score++;
    if (passwordCriteria.hasDigit) score++;
    if (/[^A-Za-z0-9]/.test(password)) score++;
    return score;
  }, [passwordCriteria, password]);

  const strengthColor = useMemo(() => {
    if (strengthScore <= 1) return 'bg-rose-500';
    if (strengthScore === 2) return 'bg-amber-500';
    if (strengthScore === 3) return 'bg-cyan-500';
    return 'bg-emerald-500';
  }, [strengthScore]);

  const isFormValid =
    fullName.trim().length >= 2 &&
    email.includes('@') &&
    passwordCriteria.hasMinLength &&
    passwordCriteria.hasLetter &&
    passwordCriteria.hasDigit &&
    passwordCriteria.passwordsMatch &&
    agreeTerms;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!isFormValid) {
      if (!passwordCriteria.passwordsMatch) {
        setError('Passwords do not match. Please verify your entries.');
      } else if (!passwordCriteria.hasMinLength) {
        setError('Password must be at least 8 characters long.');
      } else {
        setError('Please complete all required fields.');
      }
      return;
    }

    setIsLoading(true);
    setError(null);
    try {
      await signup({
        full_name: fullName.trim(),
        email: email.trim().toLowerCase(),
        password,
        confirm_password: confirmPassword,
      });
      onSuccess();
    } catch (err: any) {
      setError(err.message || 'Registration failed. Please check your information.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-[calc(100vh-4rem)] flex items-center justify-center p-4 sm:p-6 lg:p-8">
      <div className="w-full max-w-5xl bg-white border border-[#E2E8F0] rounded-2xl shadow-xl overflow-hidden grid grid-cols-1 lg:grid-cols-12 min-h-[620px]">
        {/* Left Column: Form */}
        <div className="lg:col-span-6 p-6 sm:p-10 flex flex-col justify-between">
          <div>
            <div className="flex items-center gap-2.5 mb-6">
              <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-indigo-600 to-cyan-500 flex items-center justify-center text-white shadow-md shadow-indigo-500/20">
                <Film className="w-4 h-4" />
              </div>
              <span className="text-xl font-bold tracking-tight text-[#0F172A]">ClipPilot AI</span>
            </div>

            <h1 className="text-2xl font-bold text-[#0F172A] tracking-tight">Create your account</h1>
            <p className="text-sm text-[#64748B] mt-1 mb-6">
              Get full access to the prompt video editor, project storage, and export downloads.
            </p>

            {error && (
              <div className="mb-5 p-3.5 rounded-xl bg-rose-50 border border-rose-200 text-rose-700 text-xs flex items-start gap-2.5">
                <AlertCircle className="w-4 h-4 shrink-0 mt-0.5 text-rose-500" />
                <span className="leading-relaxed font-medium">{error}</span>
              </div>
            )}

            <form onSubmit={handleSubmit} className="flex flex-col gap-3.5">
              <div>
                <label className="block text-xs font-semibold text-[#334155] mb-1.5" htmlFor="signup-name">
                  Full Name
                </label>
                <div className="relative">
                  <UserIcon className="w-4 h-4 text-[#94A3B8] absolute left-3.5 top-1/2 -translate-y-1/2" />
                  <input
                    id="signup-name"
                    type="text"
                    value={fullName}
                    onChange={(e) => setFullName(e.target.value)}
                    placeholder="Jane Doe"
                    className="form-input pl-10"
                    required
                    autoComplete="name"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-[#334155] mb-1.5" htmlFor="signup-email">
                  Work or Creator Email
                </label>
                <div className="relative">
                  <Mail className="w-4 h-4 text-[#94A3B8] absolute left-3.5 top-1/2 -translate-y-1/2" />
                  <input
                    id="signup-email"
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="jane@example.com"
                    className="form-input pl-10"
                    required
                    autoComplete="email"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-[#334155] mb-1.5" htmlFor="signup-password">
                  Password
                </label>
                <div className="relative">
                  <Lock className="w-4 h-4 text-[#94A3B8] absolute left-3.5 top-1/2 -translate-y-1/2" />
                  <input
                    id="signup-password"
                    type={showPassword ? 'text' : 'password'}
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="At least 8 characters with digits"
                    className="form-input pl-10 pr-10"
                    required
                    autoComplete="new-password"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-[#94A3B8] hover:text-[#334155] p-1"
                    aria-label={showPassword ? 'Hide password' : 'Show password'}
                  >
                    {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>

                {/* Password Strength Indicator */}
                {password.length > 0 && (
                  <div className="mt-2 flex flex-col gap-1.5">
                    <div className="h-1.5 w-full bg-[#E2E8F0] rounded-full overflow-hidden flex">
                      <div
                        className={`h-full transition-all duration-300 ${strengthColor}`}
                        style={{ width: `${(strengthScore / 4) * 100}%` }}
                      />
                    </div>
                    <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-[11px] text-[#64748B]">
                      <span className={`flex items-center gap-1 ${passwordCriteria.hasMinLength ? 'text-emerald-600 font-semibold' : ''}`}>
                        {passwordCriteria.hasMinLength ? <CheckCircle2 className="w-3 h-3" /> : <XCircle className="w-3 h-3 text-slate-300" />}
                        8+ chars
                      </span>
                      <span className={`flex items-center gap-1 ${passwordCriteria.hasLetter ? 'text-emerald-600 font-semibold' : ''}`}>
                        {passwordCriteria.hasLetter ? <CheckCircle2 className="w-3 h-3" /> : <XCircle className="w-3 h-3 text-slate-300" />}
                        Letters
                      </span>
                      <span className={`flex items-center gap-1 ${passwordCriteria.hasDigit ? 'text-emerald-600 font-semibold' : ''}`}>
                        {passwordCriteria.hasDigit ? <CheckCircle2 className="w-3 h-3" /> : <XCircle className="w-3 h-3 text-slate-300" />}
                        Numbers
                      </span>
                    </div>
                  </div>
                )}
              </div>

              <div>
                <label className="block text-xs font-semibold text-[#334155] mb-1.5" htmlFor="signup-confirm">
                  Confirm Password
                </label>
                <div className="relative">
                  <Lock className="w-4 h-4 text-[#94A3B8] absolute left-3.5 top-1/2 -translate-y-1/2" />
                  <input
                    id="signup-confirm"
                    type={showConfirmPassword ? 'text' : 'password'}
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    placeholder="Repeat your password"
                    className={`form-input pl-10 pr-10 ${
                      confirmPassword && !passwordCriteria.passwordsMatch ? 'error' : ''
                    }`}
                    required
                    autoComplete="new-password"
                  />
                  <button
                    type="button"
                    onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-[#94A3B8] hover:text-[#334155] p-1"
                    aria-label={showConfirmPassword ? 'Hide password' : 'Show password'}
                  >
                    {showConfirmPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
                {confirmPassword && !passwordCriteria.passwordsMatch && (
                  <p className="text-[11px] text-rose-600 mt-1 font-medium">Passwords do not match</p>
                )}
              </div>

              <div className="pt-1">
                <label className="flex items-start gap-2 text-xs text-[#475569] cursor-pointer select-none">
                  <input
                    type="checkbox"
                    checked={agreeTerms}
                    onChange={(e) => setAgreeTerms(e.target.checked)}
                    className="mt-0.5 rounded border-[#CBD5E1] text-indigo-600 focus:ring-indigo-500"
                    required
                  />
                  <span>
                    I agree to the terms of service and deterministic media processing terms.
                  </span>
                </label>
              </div>

              <button
                type="submit"
                disabled={isLoading || !isFormValid}
                className="btn btn-primary w-full py-2.5 mt-2 font-bold text-sm shadow-md shadow-indigo-500/20"
              >
                {isLoading ? (
                  <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                ) : (
                  <>
                    <span>Create Creator Account</span>
                    <ArrowRight className="w-4 h-4" />
                  </>
                )}
              </button>
            </form>
          </div>

          <div className="pt-6 border-t border-[#F1F5F9] mt-6 flex flex-col sm:flex-row items-center justify-between gap-3 text-xs text-[#64748B]">
            <p>
              Already have an account?{' '}
              <button
                type="button"
                onClick={onNavigateToLogin}
                className="text-indigo-600 hover:text-indigo-700 font-bold hover:underline"
              >
                Sign in
              </button>
            </p>

            <button
              type="button"
              onClick={onNavigateToDemo}
              className="text-[#475569] hover:text-[#0F172A] font-semibold hover:underline"
            >
              Explore Demo Mode
            </button>
          </div>
        </div>

        {/* Right Column: Visual Tech Showcase */}
        <div className="hidden lg:col-span-6 bg-gradient-to-br from-indigo-900 via-indigo-950 to-slate-900 p-10 lg:flex flex-col justify-between text-white relative overflow-hidden">
          <div className="absolute -top-10 -right-10 w-80 h-80 bg-cyan-500/10 rounded-full blur-3xl pointer-events-none" />
          <div className="absolute -bottom-10 -left-10 w-80 h-80 bg-indigo-500/20 rounded-full blur-3xl pointer-events-none" />

          <div className="relative z-10">
            <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-white/10 border border-white/15 text-indigo-200 text-xs font-semibold mb-6">
              <Zap className="w-3.5 h-3.5 text-cyan-300" />
              <span>Full Creative Privacy Guaranteed</span>
            </div>
            <h2 className="text-2xl xl:text-3xl font-extrabold tracking-tight leading-snug">
              Every video edit belongs only to you.
            </h2>
            <p className="text-xs text-indigo-200/80 mt-2 leading-relaxed max-w-md">
              Secure authentication guarantees isolated job histories, per-user media storage, and private cryptographic export receipts.
            </p>
          </div>

          {/* Differentiator Highlights */}
          <div className="relative z-10 my-8 flex flex-col gap-3">
            <div className="p-4 rounded-xl bg-white/5 border border-white/10 flex items-start gap-3">
              <div className="p-2 rounded-lg bg-indigo-500/20 text-indigo-300 shrink-0">
                <ShieldCheck className="w-4 h-4" />
              </div>
              <div>
                <h4 className="text-xs font-bold text-white">Private Local Storage</h4>
                <p className="text-[11px] text-slate-300 mt-0.5">
                  Your uploaded and exported video files reside strictly in protected storage directories accessible only to your account.
                </p>
              </div>
            </div>

            <div className="p-4 rounded-xl bg-white/5 border border-white/10 flex items-start gap-3">
              <div className="p-2 rounded-lg bg-cyan-500/20 text-cyan-300 shrink-0">
                <Sparkles className="w-4 h-4" />
              </div>
              <div>
                <h4 className="text-xs font-bold text-white">Explainable Edit Plans</h4>
                <p className="text-[11px] text-slate-300 mt-0.5">
                  Inspect every exact cut, aspect crop, and volume boost before committing genuine compute resources.
                </p>
              </div>
            </div>
          </div>

          <div className="relative z-10 text-[11px] text-indigo-200/70 border-t border-white/10 pt-4 flex items-center justify-between">
            <span>ClipPilot AI • IncuBrix Selection PS2</span>
            <span>FastAPI + SQLite Engine</span>
          </div>
        </div>
      </div>
    </div>
  );
};
