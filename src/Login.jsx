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
    <div className="auth-login-screen">
      <main className="auth-login-container">
        <header className="auth-login-header">
          <div className="auth-login-brand" aria-hidden="true">
            <Cpu strokeWidth={1.8} />
          </div>
          <p className="auth-login-eyebrow">KİŞİSEL PERFORMANS ALANIN</p>
          <h1 className="auth-login-title">
            LUMIERE <span>COACHING</span>
          </h1>
          <p className="auth-login-subtitle">Koçun, planların ve ilerlemen tek yerde.</p>
        </header>

        {error && (
          <div className="auth-login-error" role="alert">⚠ {error}</div>
        )}

        <section className="auth-login-card">
          <div className="auth-login-card-heading">
            <p>TEKRAR HOŞ GELDİN</p>
            <h2>Hedeflerine kaldığın yerden devam et.</h2>
          </div>

          <form onSubmit={handleLogin} className="auth-login-form">
            <div className="auth-login-field">
              <label htmlFor="login-email">E-posta</label>
              <input
                className="auth-login-input"
                id="login-email"
                type="email"
                value={email}
                onChange={handleEmailChange}
                placeholder="ornek@eposta.com"
                required
                autoComplete="email"
              />
              {emailError && <p className="auth-login-field-error">{emailError}</p>}
            </div>

            <div className="auth-login-field">
              <label htmlFor="login-password">Şifre</label>
              <input
                className="auth-login-input"
                id="login-password"
                type="password"
                value={password}
                onChange={handlePasswordChange}
                placeholder="••••••••"
                required
                minLength={8}
                autoComplete="current-password"
              />
              {passwordError && <p className="auth-login-field-error">{passwordError}</p>}
            </div>

            <button type="submit" disabled={loading} className="auth-login-submit">
              {loading ? 'Doğrulanıyor...' : 'Giriş yap'}
              {!loading && <span aria-hidden="true">→</span>}
            </button>
          </form>

          <div className="auth-login-divider"><span>veya</span></div>

          <button
            onClick={() => setCurrentPage('register')}
            className="auth-login-register"
          >
            Yeni hesap oluştur
            <span aria-hidden="true">→</span>
          </button>
        </section>

        <p className="auth-login-footnote">
          <span aria-hidden="true">●</span> Güvenli bağlantı · verilerin sana ait
        </p>
      </main>
    </div>
  );
}
