import React from 'react';
import { Mail, Lock, ArrowRight, Cpu, Eye, EyeOff } from 'lucide-react';
import * as authService from './services/authService';
import { validateEmailField, validatePasswordForSignup, getPasswordStrength, isNetworkError } from './utils/validators';
import { toUserMessage, reportError } from './utils/errorHandler';

export default function Login({ setCurrentPage }) {
  const [email, setEmail] = React.useState('');
  const [password, setPassword] = React.useState('');
  const [showPassword, setShowPassword] = React.useState(false);
  const [error, setError] = React.useState('');
  const [loading, setLoading] = React.useState(false);
  const [emailError, setEmailError] = React.useState('');
  const [passwordError, setPasswordError] = React.useState('');
  const [passwordStrength, setPasswordStrength] = React.useState(0); // 0-4

  const handleEmailChange = (e) => {
    const value = e.target.value;
    setEmail(value);
    setEmailError(value ? (validateEmailField(value) || '') : '');
  };

  const handlePasswordChange = (e) => {
    const value = e.target.value;
    setPassword(value);
    setPasswordStrength(getPasswordStrength(value));
    setPasswordError(value ? (validatePasswordForSignup(value) || '') : '');
  };

  const handleLogin = async (e) => {
    e.preventDefault();
    setError('');

    const emailErr = validateEmailField(email);
    const passwordErr = validatePasswordForSignup(password);
    setEmailError(emailErr || '');
    setPasswordError(passwordErr || '');
    if (emailErr || passwordErr) return;

    setLoading(true);
    try {
      // authService.login PROMPT 2/8 kapsamında eklenen /api/v1/auth/login akışını
      // kullanır: HttpOnly refresh-token cookie'si alır, access token'ı bellekte
      // (+ geriye dönük uyumluluk için localStorage aynası) tutar.
      await authService.login(email.trim(), password);
      setCurrentPage('dashboard');
    } catch (err) {
      if (isNetworkError(err)) {
        setError(err.message);
      } else {
        reportError(err, { scope: 'login' });
        setError(toUserMessage(err, 'Giriş başarısız oldu.'));
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-neutral-950 text-white flex items-center justify-center relative overflow-hidden p-4">
      {/* Arka plan: kayan HUD grid + turuncu glow */}
      <div className="absolute inset-0 auth-grid-bg pointer-events-none" />
      <div className="absolute -top-32 left-1/2 -translate-x-1/2 w-[420px] h-[420px] rounded-full bg-orange-500/20 blur-3xl auth-glow-orb pointer-events-none" />

      <div className="relative w-full max-w-md auth-fade-up">
        <div className="relative bg-neutral-900/70 backdrop-blur-xl border border-neutral-800 rounded-2xl overflow-hidden shadow-2xl shadow-black/50">
          {/* Üst tarama çizgisi */}
          <div className="absolute top-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-orange-500 to-transparent" />
          <div className="absolute inset-x-0 top-0 h-24 overflow-hidden pointer-events-none">
            <div className="h-px w-full bg-gradient-to-r from-transparent via-orange-400/70 to-transparent auth-scan-line" />
          </div>

          <div className="p-8">
            <div className="flex flex-col items-center mb-8">
              <div className="w-12 h-12 rounded-xl bg-orange-500/10 border border-orange-500/30 flex items-center justify-center mb-4">
                <Cpu className="w-6 h-6 text-orange-500" strokeWidth={1.75} />
              </div>
              <h1 className="text-lg font-black font-mono tracking-[0.1em] text-white">
                LUMIERE <span className="text-orange-500">COACHING</span>
              </h1>
              <p className="text-[11px] font-mono tracking-widest text-neutral-500 mt-1 uppercase">
                Sistem Erişimi
              </p>
            </div>

            {error && (
              <div className="bg-red-500/10 border border-red-500/20 text-red-400 text-sm px-4 py-3 rounded-lg mb-5 font-mono">
                ⚠ {error}
              </div>
            )}

            <form onSubmit={handleLogin} className="space-y-4">
              <div>
                <label className="block text-[11px] font-mono tracking-widest text-neutral-500 uppercase mb-2">
                  E-posta
                </label>
                <div className="relative">
                  <Mail className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-neutral-600" strokeWidth={1.75} />
                  <input
                    type="email"
                    value={email}
                    onChange={handleEmailChange}
                    className={`w-full bg-neutral-950/80 border border-neutral-800 rounded-lg pl-10 pr-4 py-3 text-sm text-white placeholder-neutral-600 focus:outline-none focus:border-orange-500/60 focus:ring-1 focus:ring-orange-500/40 transition-colors ${emailError ? 'border-red-500' : ''}`}
                    placeholder="ornek@eposta.com"
                    required
                    autoComplete="email"
                  />
                  {emailError && (
                    <p className="text-[10px] text-red-500 mt-1">{emailError}</p>
                  )}
                </div>
              </div>

              <div>
                <label className="block text-[11px] font-mono tracking-widest text-neutral-500 uppercase mb-2 flex justify-between">
                  Şifre
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="text-[10px] font-mono text-neutral-500 hover:text-orange-400 p-1"
                  >
                    {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </label>
                <div className="relative">
                  <Lock className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-neutral-600" strokeWidth={1.75} />
                  <input
                    type={showPassword ? 'text' : 'password'}
                    value={password}
                    onChange={handlePasswordChange}
                    className={`w-full bg-neutral-950/80 border border-neutral-800 rounded-lg pl-10 pr-4 py-3 text-sm text-white placeholder-neutral-600 focus:outline-none focus:border-orange-500/60 focus:ring-1 focus:ring-orange-500/40 transition-colors ${passwordError ? 'border-red-500' : ''}`}
                    placeholder="••••••••"
                    required
                    minLength={8}
                    autoComplete="current-password"
                  />
                  {passwordError && (
                    <p className="text-[10px] text-red-500 mt-1">{passwordError}</p>
                  )}
                  {/* Password strength indicator */}
                  <div className="mt-2">
                    <div className="flex w-full bg-neutral-800 h-1.5 rounded-full overflow-hidden">
                      <div
                        className={`h-full bg-orange-500 transition-all duration-300`}
                        style={{ width: `${passwordStrength * 20}%` }}
                      ></div>
                    </div>
                    <div className="flex justify-between text-[10px] font-mono text-neutral-500 mt-1">
                      <span>Zayıf</span>
                      <span>Orta</span>
                      <span>Güçlü</span>
                    </div>
                  </div>
                </div>
              </div>

              <button
                type="submit"
                disabled={loading}
                className="group w-full bg-orange-500 hover:bg-orange-400 text-black font-bold font-mono text-sm tracking-wide py-3.5 rounded-lg disabled:opacity-50 disabled:cursor-not-allowed transition-all shadow-lg shadow-orange-500/20 hover:shadow-orange-500/30 flex items-center justify-center gap-2 mt-2"
              >
                {loading ? (
                  <span className="flex items-center gap-2">
                    <span className="w-3.5 h-3.5 border-2 border-black/30 border-t-black rounded-full animate-spin" />
                    Doğrulanıyor...
                  </span>
                ) : (
                  <>
                    Giriş Yap
                    <ArrowRight className="w-4 h-4 group-hover:translate-x-0.5 transition-transform" strokeWidth={2} />
                  </>
                )}
              </button>
            </form>

            <div className="flex items-center gap-3 my-6">
              <div className="h-px flex-1 bg-neutral-800" />
              <span className="text-[10px] font-mono text-neutral-600 tracking-widest">VEYA</span>
              <div className="h-px flex-1 bg-neutral-800" />
            </div>

            <p className="text-center text-sm text-neutral-500 font-mono">
              Hesabın yok mu?{' '}
              <button
                onClick={() => setCurrentPage('register')}
                className="text-orange-500 hover:text-orange-400 bg-transparent border-none cursor-pointer font-semibold"
              >
                Kayıt Ol →
              </button>
            </p>
          </div>
        </div>

        <p className="text-center text-[10px] font-mono text-neutral-700 tracking-widest mt-6 uppercase">
          Jarvis Core &middot; Güvenli Bağlantı
        </p>
      </div>
    </div>
  );
}
