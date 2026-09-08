import { useState } from 'react';
import { ArrowRight, Lock, Mail, User, ChevronLeft } from 'lucide-react';
import Logo from './components/lumiere/Logo';
import * as authService from './services/authService';
import {
  validateEmailField, validatePasswordForSignup, validateFullName,
  getPasswordStrength, isNetworkError,
} from './utils/validators';
import { toUserMessage, reportError } from './utils/errorHandler';
import MembershipPlans from './components/MembershipPlans';

const field =
  'h-13 w-full rounded-xl border border-input bg-surface px-4 py-3.5 pl-11 text-base outline-none transition-colors placeholder:text-muted-foreground focus:border-ring';

/**
 * Kayıt ekranı — love repo `src/routes/register.tsx` tasarımı + mevcut authService.
 * 1. adım: hesap bilgileri; 2. adım: üyelik planı seçimi (backend preferred_plan).
 */
const [step, setStep] = useState(1);
  const [form, setForm] = useState({ name: '', email: '', password: '' });
  const [showPassword, setShowPassword] = useState(false);
  const [selectedPlan, setSelectedPlan] = useState('FREE');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [emailError, setEmailError] = useState('');
  const [passwordError, setPasswordError] = useState('');
  const [fullNameError, setFullNameError] = useState('');
  const [passwordStrength, setPasswordStrength] = useState(0);

  const handleEmailChange = (e) => {
    const val = e.target.value;
    setForm({ ...form, email: val });
    setEmailError(val ? (validateEmailField(val) || '') : '');
  };

  const handlePasswordChange = (e) => {
    const val = e.target.value;
    setForm({ ...form, password: val });
    setPasswordStrength(getPasswordStrength(val));
    setPasswordError(val ? (validatePasswordForSignup(val) || '') : '');
  };

  const handleFullNameChange = (e) => {
    const val = e.target.value;
    setForm({ ...form, name: val });
    setFullNameError(val ? (validateFullName(val) || '') : '');
  };

  const handleGoToPlanStep = (e) => {
    e?.preventDefault();
    setError('');
    const fullNameErr = validateFullName(form.name);
    const emailErr = validateEmailField(form.email);
    const passwordErr = validatePasswordForSignup(form.password);
    setFullNameError(fullNameErr || '');
    setEmailError(emailErr || '');
    setPasswordError(passwordErr || '');
    if (fullNameErr || emailErr || passwordErr) return;
    setStep(2);
  };

  const handleCompleteRegister = async () => {
    setError('');
    setLoading(true);
    try {
      await authService.register(form.name.trim(), form.email.trim(), form.password, selectedPlan);
      localStorage.setItem('preferred_plan', selectedPlan);
      setCurrentPage('dashboard');
    } catch (err) {
      if (isNetworkError(err)) {
        setError(err.message);
      } else {
        reportError(err, { scope: 'register' });
        setError(toUserMessage(err, 'Kayıt başarısız oldu.'));
      }
    } finally {
      setLoading(false);
    }
  };
export default function Register({ setCurrentPage }) {
return (
    <main className="hero-bg flex min-h-dvh flex-col justify-center px-5 py-10">
      <div className="mx-auto w-full max-w-sm">
        <div className="mb-8 flex flex-col items-center text-center">
          <Logo size="lg" showText={false} />
          <p className="eyebrow mt-5 text-primary-glow">Hesap oluştur</p>
          <h1 className="mt-2 text-3xl font-extrabold">Yeni başlangıç</h1>
          <p className="mt-2 text-sm text-muted-foreground">Birkaç adımda planın hazır olacak.</p>
        </div>

        {error && (
          <div className="mb-4 rounded-xl border border-destructive/40 bg-destructive/10 px-4 py-3 text-sm text-primary-glow">
            ⚠ {error}
          </div>
        )}

        {step === 1 && (
          <form onSubmit={handleGoToPlanStep} className="surface-card space-y-4 p-5">
            <div className="relative">
              <User
                size={17}
                className="pointer-events-none absolute left-4 top-1/2 -translate-y-1/2 text-muted-foreground"
              />
              <input
                required
                value={form.name}
                onChange={handleFullNameChange}
                placeholder="Ad Soyad"
                autoComplete="name"
                className={field}
              />
            </div>
            {fullNameError && <span className="block text-[11px] text-primary-glow">{fullNameError}</span>}

            <div className="relative">
              <Mail
                size={17}
                className="pointer-events-none absolute left-4 top-1/2 -translate-y-1/2 text-muted-foreground"
              />
              <input
                required
                type="email"
                inputMode="email"
                autoComplete="email"
                value={form.email}
                onChange={handleEmailChange}
                placeholder="E-posta"
                className={field}
              />
            </div>
            {emailError && <span className="block text-[11px] text-primary-glow">{emailError}</span>}

            <div className="relative">
              <Lock
                size={17}
                className="pointer-events-none absolute left-4 top-1/2 -translate-y-1/2 text-muted-foreground"
              />
              <input
                required
                minLength={8}
                type={showPassword ? 'text' : 'password'}
                autoComplete="new-password"
                value={form.password}
                onChange={handlePasswordChange}
                placeholder="Şifre (en az 8 karakter)"
                className={field}
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                aria-label="Şifreyi göster/gizle"
                className="absolute right-4 top-1/2 -translate-y-1/2 text-xs font-semibold text-muted-foreground"
              >
                {showPassword ? 'Gizle' : 'Göster'}
              </button>
            </div>
            {passwordError && <span className="block text-[11px] text-primary-glow">{passwordError}</span>}
            {passwordStrength > 0 && passwordStrength < 100 && (
              <div className="h-1.5 mt-1 overflow-hidden rounded-full bg-secondary">
                <div
                  className="h-full rounded-full"
                  style={{
                    width: `${passwordStrength}%`,
                    background: passwordStrength < 40
                      ? 'var(--destructive)'
                      : passwordStrength < 75
                        ? 'var(--warning)'
                        : 'var(--success)',
                  }}
                />
              </div>
            )}

            <button
              type="submit"
              className="ember ember-glow flex h-13 w-full items-center justify-center gap-2 rounded-xl text-base font-bold active:scale-[0.99]"
            >
              Devam et <ArrowRight size={18} />
            </button>

            <button
              type="button"
              onClick={() => setCurrentPage('login')}
              className="flex h-12 w-full items-center justify-center rounded-xl text-sm font-semibold text-muted-foreground"
            >
              Zaten hesabın var mı? Giriş yap
            </button>
          </form>
        )}

        {step === 2 && (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <button
                type="button"
                onClick={() => setStep(1)}
                className="flex items-center gap-1.5 text-xs font-bold text-muted-foreground"
              >
                <ChevronLeft size={15} /> Hesap bilgilerine dön
              </button>
              <span className="eyebrow text-primary-glow normal-case">
                Seçili: <strong>{selectedPlan}</strong>
              </span>
            </div>

            <MembershipPlans
              selectedPlan={selectedPlan}
              onSelectPlan={setSelectedPlan}
              actionButtonLabel="Bu Planla Devam Et"
            />

            <button
              type="button"
              disabled={loading}
              onClick={handleCompleteRegister}
              className="ember ember-glow flex h-13 w-full items-center justify-center gap-2 rounded-xl text-base font-bold active:scale-[0.99] disabled:opacity-60"
            >
              {loading ? 'Profil oluşturuluyor...' : 'Kaydı tamamla & başla'}
              <ArrowRight size={18} />
            </button>

            <p className="text-center text-[11px] text-muted-foreground">
              Seçtiğiniz plan hesabınızla birlikte hemen aktif edilir. İstediğiniz zaman değiştirebilirsiniz.
            </p>
          </div>
        )}
      </div>
    </main>
  );
}