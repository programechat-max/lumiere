import React from 'react';
import { Cpu } from 'lucide-react';
import * as authService from './services/authService';
import { validateEmailField, validatePasswordForSignup, isNetworkError } from './utils/validators';
import { toUserMessage, reportError } from './utils/errorHandler';

export default function Login({ setCurrentPage }) {
  const [email, setEmail] = React.useState('');
  const [password, setPassword] = React.useState('');
  const [error, setError] = React.useState('');
  const [loading, setLoading] = React.useState(false);
  const [emailError, setEmailError] = React.useState('');
  const [passwordError, setPasswordError] = React.useState('');

  const handleEmailChange = (e) => {
    const value = e.target.value;
    setEmail(value);
    setEmailError(value ? (validateEmailField(value) || '') : '');
  };

  const handlePasswordChange = (e) => {
    const value = e.target.value;
    setPassword(value);
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
    <div className="lp-auth-screen lp-column text-white min-h-screen relative">
      <div style={{ textAlign: 'center' }}>
        <div className="lp-brand-mark lp-auth-brand flex items-center justify-center">
          <Cpu strokeWidth={2} />
        </div>
        <p className="lp-section-kicker">Kişisel performans alanın</p>
        <h1 className="lp-screen-title lp-auth-title">
          LUMIERE <span>COACHING</span>
        </h1>
        <p className="lp-small lp-muted lp-auth-sub">Koçun, planların ve ilerlemen tek yerde.</p>
      </div>

      {error && (
        <div className="lp-panel lp-auth-error">⚠ {error}</div>
      )}

      <div className="lp-panel lp-auth-panel">
        <form onSubmit={handleLogin}>
          <div className="lp-form-field">
            <label htmlFor="login-email">E-posta</label>
            <input
              id="login-email"
              type="email"
              value={email}
              onChange={handleEmailChange}
              placeholder="ornek@eposta.com"
              required
              autoComplete="email"
            />
            {emailError && <p className="lp-auth-field-error">{emailError}</p>}
          </div>

          <div className="lp-form-field">
            <label htmlFor="login-password">Şifre</label>
            <input
              id="login-password"
              type="password"
              value={password}
              onChange={handlePasswordChange}
              placeholder="••••••••"
              required
              minLength={8}
              autoComplete="current-password"
            />
            {passwordError && <p className="lp-auth-field-error">{passwordError}</p>}
          </div>

          <button type="submit" disabled={loading} className="lp-primary">
            {loading ? 'Doğrulanıyor...' : 'Giriş yap ›'}
          </button>
        </form>

        <div className="lp-divider">
          <i />
          VEYA
          <i />
        </div>

        <button
          onClick={() => setCurrentPage('register')}
          className="lp-ghost"
          style={{ width: '100%' }}
        >
          Yeni hesap oluştur
        </button>
      </div>

      <p className="lp-small lp-muted lp-auth-footnote">Güvenli bağlantı · verilerin sana ait</p>
    </div>
  );
}
