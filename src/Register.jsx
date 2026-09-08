import { useState, useCallback } from 'react';
import { Mail, Lock, User, ArrowRight, Cpu, Eye, EyeOff, CheckCircle2, ChevronLeft } from 'lucide-react';
import * as authService from './services/authService';
import {
  validateEmailField, validatePasswordForSignup, validateFullName,
  getPasswordStrength, isNetworkError,
} from './utils/validators';
import { toUserMessage, reportError } from './utils/errorHandler';
import MembershipPlans from './components/MembershipPlans';

export default function Register({ setCurrentPage }) {
  const [step, setStep] = useState(1); // 1: Hesap Bilgileri, 2: Üyelik Planı Seçimi
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [fullName, setFullName] = useState('');
  const [selectedPlan, setSelectedPlan] = useState('FREE');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [emailError, setEmailError] = useState('');
  const [passwordError, setPasswordError] = useState('');
  const [fullNameError, setFullNameError] = useState('');
  const [passwordStrength, setPasswordStrength] = useState(0);

  const handleEmailChange = useCallback((e) => {
    const val = e.target.value;
    setEmail(val);
    setEmailError(val ? (validateEmailField(val) || '') : '');
  }, []);

  const handlePasswordChange = useCallback((e) => {
    const val = e.target.value;
    setPassword(val);
    setPasswordStrength(getPasswordStrength(val));
    setPasswordError(val ? (validatePasswordForSignup(val) || '') : '');
  }, []);

  const handleFullNameChange = useCallback((e) => {
    const val = e.target.value;
    setFullName(val);
    setFullNameError(val ? (validateFullName(val) || '') : '');
  }, []);

  const handleGoToPlanStep = (e) => {
    e?.preventDefault();
    setError('');
    const fullNameErr = validateFullName(fullName);
    const emailErr = validateEmailField(email);
    const passwordErr = validatePasswordForSignup(password);
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
      await authService.register(fullName.trim(), email.trim(), password, selectedPlan);
      // Tercih edilen planı yerel hafızada da sakla (backend'e preferred_plan olarak gönderildi)
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

  return (
    <div className="lumiere-app-shell auth-screen text-white flex min-h-screen items-center justify-center relative overflow-x-hidden p-4 sm:p-6">
      {/* Donmayan arkaplan: blur filtresi yerine önceden işlenmiş radial gradient kullanılır
          (büyük blur katmanları özellikle mobil GPU'larda sayfayı kasıyordu) */}
      <div className="absolute inset-0 auth-grid-bg pointer-events-none opacity-40" />
      <div
        className="absolute inset-0 pointer-events-none"
        style={{ background: 'radial-gradient(ellipse 60% 40% at 50% 0%, rgba(239,51,64,0.08), transparent 70%)' }}
      />

      <div className={`relative w-full ${step === 2 ? 'max-w-5xl' : 'max-w-md'} transition-all duration-300`}>
        {/* Üst Logo ve Başlık */}
        <div className="flex flex-col items-center mb-6">
          <div className="lp-brand-mark mx-auto flex items-center justify-center mb-3 shadow-lg shadow-red-950/30">
            <Cpu className="w-6 h-6 text-white" strokeWidth={2} />
          </div>
          <p className="lp-section-kicker mb-1">Kişisel yolculuğun</p>
          <h1 className="text-2xl font-black tracking-[-0.06em] text-white">
            LUMIERE <span className="text-red-500">COACHING</span>
          </h1>
          <p className="text-[11px] font-semibold tracking-[0.12em] text-neutral-500 mt-2 uppercase">
            {step === 1 ? 'Adım 1 / 2 · Hesabını oluştur' : 'Adım 2 / 2 · Planını seç'}
          </p>
        </div>

        {/* Adım Göstergesi */}
        <div className="flex items-center justify-center gap-2 mb-6 max-w-xs mx-auto">
          <button
            onClick={() => setStep(1)}
            className={`flex-1 h-1.5 rounded-full transition-all ${step >= 1 ? 'bg-red-500' : 'bg-neutral-800'}`}
          />
          <button
            onClick={() => {
              if (!validateFullName(fullName) && !validateEmailField(email) && !validatePasswordForSignup(password)) {
                setStep(2);
              }
            }}
            className={`flex-1 h-1.5 rounded-full transition-all ${step === 2 ? 'bg-red-500' : 'bg-neutral-800'}`}
          />
        </div>

        {error && (
          <div className="bg-red-500/10 border border-red-500/30 text-red-400 text-xs px-4 py-3 rounded-xl mb-5 font-mono max-w-md mx-auto">
            ⚠ {error}
          </div>
        )}

        {/* ADIM 1: HESAP BİLGİLERİ FORMU */}
        {step === 1 && (
          <div className="bg-[#181820]/90 border border-white/[0.1] rounded-[28px] p-6 sm:p-8 shadow-2xl shadow-black/60 relative overflow-hidden">
            <div className="absolute top-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-red-500/50 to-transparent" />

            <form onSubmit={handleGoToPlanStep} className="space-y-4">
              <div>
                <label className="block text-[11px] font-bold tracking-[0.12em] text-neutral-400 uppercase mb-2">
                  Ad Soyad
                </label>
                <div className="relative">
                  <User className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-neutral-500" strokeWidth={1.75} />
                  <input
                    type="text"
                    value={fullName}
                    onChange={handleFullNameChange}
                    className={`w-full bg-black/20 border border-white/[0.09] rounded-xl pl-10 pr-4 py-3.5 text-sm text-white placeholder-neutral-600 focus:outline-none focus:border-red-400 focus:ring-2 focus:ring-red-500/15 transition-colors ${fullNameError ? 'border-red-500' : ''}`}
                    placeholder="Adınız Soyadınız"
                    required
                    autoComplete="name"
                  />
                  {fullNameError && <p className="text-[10px] text-red-400 mt-1">{fullNameError}</p>}
                </div>
              </div>

              <div>
                <label className="block text-[11px] font-bold tracking-[0.12em] text-neutral-400 uppercase mb-2">
                  E-posta Adresi
                </label>
                <div className="relative">
                  <Mail className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-neutral-500" strokeWidth={1.75} />
                  <input
                    type="email"
                    value={email}
                    onChange={handleEmailChange}
                    className={`w-full bg-black/20 border border-white/[0.09] rounded-xl pl-10 pr-4 py-3.5 text-sm text-white placeholder-neutral-600 focus:outline-none focus:border-red-400 focus:ring-2 focus:ring-red-500/15 transition-colors ${emailError ? 'border-red-500' : ''}`}
                    placeholder="ornek@eposta.com"
                    required
                    autoComplete="email"
                  />
                  {emailError && <p className="text-[10px] text-red-400 mt-1">{emailError}</p>}
                </div>
              </div>

              <div>
                <div className="flex justify-between items-center mb-2">
                  <label className="text-[11px] font-bold tracking-[0.12em] text-neutral-400 uppercase">
                    Şifre
                  </label>
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="text-[10px] font-mono text-neutral-400 hover:text-red-400 flex items-center gap-1"
                  >
                    {showPassword ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
                    <span>{showPassword ? 'Gizle' : 'Göster'}</span>
                  </button>
                </div>
                <div className="relative">
                  <Lock className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-neutral-500" strokeWidth={1.75} />
                  <input
                    type={showPassword ? 'text' : 'password'}
                    value={password}
                    onChange={handlePasswordChange}
                    className={`w-full bg-black/20 border border-white/[0.09] rounded-xl pl-10 pr-4 py-3.5 text-sm text-white placeholder-neutral-600 focus:outline-none focus:border-red-400 focus:ring-2 focus:ring-red-500/15 transition-colors ${passwordError ? 'border-red-500' : ''}`}
                    placeholder="En az 8 karakter"
                    required
                    minLength={8}
                    autoComplete="new-password"
                  />
                  {passwordError && <p className="text-[10px] text-red-400 mt-1">{passwordError}</p>}
                </div>

                {/* Şifre Güç Çubuğu */}
                {password && (
                  <div className="mt-2 space-y-1">
                    <div className="flex w-full bg-neutral-800 h-1 rounded-full overflow-hidden">
                      <div
                        className={`h-full transition-all duration-300 ${
                          passwordStrength <= 1 ? 'bg-red-500 w-1/4' :
                          passwordStrength === 2 ? 'bg-amber-500 w-2/4' :
                          passwordStrength === 3 ? 'bg-red-500 w-3/4' : 'bg-emerald-500 w-full'
                        }`}
                      />
                    </div>
                  </div>
                )}
              </div>

              <button
                type="submit"
                className="lp-primary w-full font-bold text-sm tracking-wide py-3.5 rounded-xl transition-all flex items-center justify-center gap-2 mt-4 cursor-pointer"
              >
                <span>Üyelik Planı Seçimine Geç</span>
                <ArrowRight className="w-4 h-4" strokeWidth={2.5} />
              </button>
            </form>

            <div className="lp-divider">
              <i />
              VEYA
              <i />
            </div>

            <button
              onClick={() => setCurrentPage('login')}
              className="lp-ghost w-full"
              style={{ textAlign: 'center' }}
            >
              Zaten bir hesabın var mı? · Giriş yap
            </button>
          </div>
        )}

        {/* ADIM 2: 4'LÜ ÜYELİK PLANI SEÇİMİ VE KAYIT TAMAMLAMA */}
        {step === 2 && (
          <div className="space-y-5 bg-[#181820]/90 border border-white/[0.1] rounded-[28px] p-4 sm:p-8 shadow-2xl shadow-black/80 animate-fadeIn">
            <div className="flex items-center justify-between border-b border-neutral-800 pb-4">
              <button
                onClick={() => setStep(1)}
                className="flex items-center gap-1.5 text-xs font-mono text-neutral-400 hover:text-white transition-colors"
              >
                <ChevronLeft className="w-4 h-4" /> Hesap Bilgilerine Dön
              </button>
              <span className="text-xs font-mono text-neutral-500">
                Seçili Plan: <strong className="text-red-400">{selectedPlan}</strong>
              </span>
            </div>

            <MembershipPlans
              selectedPlan={selectedPlan}
              onSelectPlan={setSelectedPlan}
              actionButtonLabel="Bu Planla Devam Et"
            />

            <div className="pt-4 border-t border-neutral-800 flex flex-col sm:flex-row items-center justify-between gap-4">
              <p className="text-xs text-neutral-500 font-sans text-center sm:text-left">
                Seçtiğiniz plan hesabınızla birlikte hemen aktif edilecek. İstediğiniz zaman değiştirebilirsiniz.
              </p>
              <button
                type="button"
                disabled={loading}
                onClick={handleCompleteRegister}
                className="lp-primary w-full sm:w-auto min-w-[220px] font-bold text-sm py-3.5 px-6 rounded-xl transition-all flex items-center justify-center gap-2 cursor-pointer disabled:opacity-50"
              >
                {loading ? (
                  <span className="flex items-center gap-2">
                    <span className="w-4 h-4 border-2 border-black/30 border-t-black rounded-full animate-spin" />
                    Profil Oluşturuluyor...
                  </span>
                ) : (
                  <>
                    <span>Kaydı Tamamla & Başla</span>
                    <CheckCircle2 className="w-4 h-4" />
                  </>
                )}
              </button>
            </div>
          </div>
        )}

        <p className="text-center text-[10px] font-mono text-neutral-600 tracking-widest mt-6 uppercase">
          Lumiere AI Core &middot; Güvenli Çok Kullanıcılı Altyapı
        </p>
      </div>
    </div>
  );
}
