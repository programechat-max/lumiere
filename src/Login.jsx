import { useState } from 'react';
import { ArrowRight, Lock, Mail, ShieldCheck } from 'lucide-react';
import Logo from './components/lumiere/Logo';
import * as authService from './services/authService';
import { validateEmailField, validatePasswordForSignup, isNetworkError } from './utils/validators';
import { toUserMessage, reportError } from './utils/errorHandler';

/**
 * Giriş ekranı — love repo `src/routes/index.tsx` tasarımı + mevcut authService.
 * Backend: /api/v1/auth/login (HttpOnly refresh-token cookie akışı).
 */
export default function Login({ setCurrentPage }) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [emailError, setEmailError] = useState('');
  const [passwordError, setPasswordError] = useState('');

  const handleEmailChange = (e) => {
    const value = e.target.value;
    setEmail(value);
    setEmailError(value ? (validateEmailField(value) || '') : '');
  };

  const handlePasswordChange = (e) => {
    const value = e.target.value;
    setPassword(value);
    setPasswordError(value ? '' : '');
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
    <main className="hero-bg flex min-h-dvh flex-col justify-center px-5 py-10">
      <div className="mx-auto w-full max-w-sm">
        <div className="mb-8 flex flex-col items-center text-center">
          <Logo size="lg" showText={false} />
          <p className="eyebrow mt-5 text-primary-glow">Kişisel performans alanın</p>
          <h1 className="mt-2 text-3xl font-extrabold leading-tight">
            LUMIERE <span className="text-primary-glow">COACHING</span>
          </h1>
          <p className="mt-2 text-sm text-muted-foreground">Koçun, planların ve ilerlemen tek yerde.</p>
        </div>

        {error && (
          <div className="mb-4 rounded-xl border border-destructive/40 bg-destructive/10 px-4 py-3 text-sm text-primary-glow">
            ⚠ {error}
          </div>
        )}

        <form onSubmit={handleLogin} className="surface-card space-y-4 p-5">
          <label className="block">
            <span className="eyebrow text-muted-foreground">E-posta</span>
            <div className="relative mt-2">
              <Mail
                size={17}
                className="pointer-events-none absolute left-4 top-1/2 -translate-y-1/2 text-muted-foreground"
              />
              <input
                required
                type="email"
                inputMode="email"
                autoComplete="email"
                value={email}
                onChange={handleEmailChange}
                placeholder="ornek@eposta.com"
                className="h-13 w-full rounded-xl border border-input bg-surface px-4 py-3.5 pl-11 text-base outline-none transition-colors placeholder:text-muted-foreground focus:border-ring"
              />
            </div>
            {emailError && <span className="mt-1 block text-[11px] text-primary-glow">{emailError}</span>}
          </label>

          <label className="block">
            <span className="eyebrow text-muted-foreground">Şifre</span>
            <div className="relative mt-2">
              <Lock
                size={17}
                className="pointer-events-none absolute left-4 top-1/2 -translate-y-1/2 text-muted-foreground"
              />
              <input
                required
                type="password"
                autoComplete="current-password"
                value={password}
                onChange={handlePasswordChange}
                placeholder="••••••••"
                className="h-13 w-full rounded-xl border border-input bg-surface px-4 py-3.5 pl-11 text-base outline-none transition-colors placeholder:text-muted-foreground focus:border-ring"
              />
            </div>
            {passwordError && <span className="mt-1 block text-[11px] text-primary-glow">{passwordError}</span>}
          </label>

          <button
            type="submit"
            disabled={loading}
            className="ember ember-glow flex h-13 w-full items-center justify-center gap-2 rounded-xl text-base font-bold active:scale-[0.99] disabled:opacity-60"
          >
            {loading ? 'Doğrulanıyor...' : 'Giriş yap'} <ArrowRight size={18} />
          </button>

          <button
            type="button"
            onClick={() => setCurrentPage('register')}
            className="flex h-13 w-full items-center justify-center rounded-xl border border-border bg-surface text-base font-semibold active:scale-[0.99]"
          >
            Yeni hesap oluştur
          </button>
        </form>

        <p className="mt-6 flex items-center justify-center gap-2 text-xs text-muted-foreground">
          <ShieldCheck size={14} /> Verilerin şifreli saklanır
        </p>
      </div>
    </main>
  );
}