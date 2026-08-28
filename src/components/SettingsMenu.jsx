import React from 'react';
import {
  X, Bell, Shield, Smartphone, LogOut, Trash2, AlertTriangle,
  Download, Loader2, CheckCircle2, ChevronLeft, ChevronRight,
  Camera, Mic, ShieldCheck,
} from 'lucide-react';
import { apiFetch } from '../services/apiClient';
import { toUserMessage, reportError } from '../utils/errorHandler';

const TABS = [
  { key: 'notifications', label: 'Bildirimler', Icon: Bell },
  { key: 'sessions', label: 'Oturumlar', Icon: Smartphone },
  { key: 'permissions', label: 'İzinler', Icon: ShieldCheck },
  { key: 'privacy', label: 'Gizlilik', Icon: Shield },
];

// Kamera/mikrofon izin satırları - değerler /api/status'taki kalıcı rıza kararlarıdır.
const PERMISSION_ROWS = [
  { key: 'camera', label: 'Kamera', desc: 'Form analizi ve vücut videosu için', Icon: Camera },
  { key: 'microphone', label: 'Mikrofon', desc: 'Sesli check-in ve yaşam anlatımı için', Icon: Mic },
];

const NOTIF_TOGGLES = [
  { key: 'daily_checkin_enabled', label: 'Günlük check-in hatırlatması' },
  { key: 'workout_reminders_enabled', label: 'Antrenman hatırlatmaları' },
  { key: 'weekly_report_enabled', label: 'Haftalık analiz bildirimi' },
  { key: 'inactivity_alerts_enabled', label: 'Hareketsizlik uyarıları' },
  { key: 'billing_alerts_enabled', label: 'Faturalandırma uyarıları' },
];

function formatDateTime(value) {
  if (!value) return '—';
  try {
    return new Date(value).toLocaleString('tr-TR', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' });
  } catch {
    return value;
  }
}

/**
 * Mobil/iOS başlıkta dişli çark ikonuyla açılan ayarlar paneli (PROMPT 9 bildirim
 * tercihleri, PROMPT 2 oturum yönetimi, PROMPT 11 GDPR veri/hesap işlemleri için
 * gerçek bir kullanıcı arayüzü sağlar - backend'deki /api/v1/* uçlarını kullanır).
 */
export default function SettingsMenu({ open, onClose, onLogout, permissions = { camera: null, microphone: null }, onPermissionsChanged }) {
  // null => kök menü listesi (iOS Ayarlar uygulamasındaki gibi); bir sekme seçilince
  // ilgili veri SADECE O DOKUNMA olayında çekilir (effect içinde değil) - hem daha
  // native bir gezinme hissi verir hem de gereksiz otomatik fetch'i önler.
  const [activeTab, setActiveTab] = React.useState(null);

  const [notifSettings, setNotifSettings] = React.useState(null);
  const [notifLoading, setNotifLoading] = React.useState(false);
  const [notifSaving, setNotifSaving] = React.useState(false);
  const [notifError, setNotifError] = React.useState('');

  const [sessions, setSessions] = React.useState(null);
  const [sessionsLoading, setSessionsLoading] = React.useState(false);
  const [sessionsError, setSessionsError] = React.useState('');

  const [exporting, setExporting] = React.useState(false);
  const [deleteState, setDeleteState] = React.useState(null); // { scheduled_for, cancel_token } | 'confirm' | null
  const [privacyError, setPrivacyError] = React.useState('');
  const [privacyBusy, setPrivacyBusy] = React.useState(false);

  // İzin sekmesi: tarayıcıdan cihaz izni istenir, kararı kalıcı profile yazılır.
  const [permBusy, setPermBusy] = React.useState('');
  const [permError, setPermError] = React.useState('');

  const loadNotificationSettings = React.useCallback(async () => {
    setNotifLoading(true);
    setNotifError('');
    try {
      const data = await apiFetch('/api/v1/notifications/settings');
      setNotifSettings(data);
    } catch (err) {
      reportError(err, { scope: 'settings.notifications.load' });
      setNotifError(toUserMessage(err, 'Bildirim ayarları yüklenemedi.'));
    } finally {
      setNotifLoading(false);
    }
  }, []);

  const loadSessions = React.useCallback(async () => {
    setSessionsLoading(true);
    setSessionsError('');
    try {
      const data = await apiFetch('/api/v1/auth/sessions');
      setSessions(data);
    } catch (err) {
      reportError(err, { scope: 'settings.sessions.load' });
      setSessionsError(toUserMessage(err, 'Oturumlar yüklenemedi.'));
    } finally {
      setSessionsLoading(false);
    }
  }, []);

  const openTab = (key) => {
    setActiveTab(key);
    if (key === 'notifications' && !notifSettings && !notifLoading) loadNotificationSettings();
    if (key === 'sessions' && !sessions && !sessionsLoading) loadSessions();
  };

  const toggleNotif = async (key) => {
    if (!notifSettings) return;
    const updated = { ...notifSettings, [key]: !notifSettings[key] };
    setNotifSettings(updated);
    setNotifSaving(true);
    try {
      await apiFetch('/api/v1/notifications/settings', {
        method: 'PUT',
        body: JSON.stringify({ [key]: updated[key] }),
      });
    } catch (err) {
      reportError(err, { scope: 'settings.notifications.save' });
      setNotifSettings(notifSettings); // geri al
      setNotifError(toUserMessage(err, 'Ayar kaydedilemedi.'));
    } finally {
      setNotifSaving(false);
    }
  };

  const revokeSession = async (id) => {
    try {
      await apiFetch(`/api/v1/auth/sessions/${id}/revoke`, { method: 'POST' });
      setSessions((prev) => (prev || []).filter((s) => s.id !== id));
    } catch (err) {
      reportError(err, { scope: 'settings.sessions.revoke' });
      setSessionsError(toUserMessage(err, 'Oturum sonlandırılamadı.'));
    }
  };

  const handleExportData = async () => {
    setExporting(true);
    setPrivacyError('');
    try {
      const res = await apiFetch('/api/v1/privacy/export');
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = 'lumiere-verilerim.json.gz';
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
    } catch (err) {
      reportError(err, { scope: 'settings.privacy.export' });
      setPrivacyError(toUserMessage(err, 'Veri dışa aktarma başarısız oldu (ayda 1 kez talep edilebilir).'));
    } finally {
      setExporting(false);
    }
  };

  const handleRequestDeletion = async () => {
    setPrivacyBusy(true);
    setPrivacyError('');
    try {
      const data = await apiFetch('/api/v1/privacy/delete-account', { method: 'POST' });
      setDeleteState(data);
    } catch (err) {
      reportError(err, { scope: 'settings.privacy.delete' });
      setPrivacyError(toUserMessage(err, 'Hesap silme talebi oluşturulamadı.'));
    } finally {
      setPrivacyBusy(false);
    }
  };

  const handleCancelDeletion = async () => {
    if (!deleteState?.cancel_token) return;
    setPrivacyBusy(true);
    setPrivacyError('');
    try {
      await apiFetch('/api/v1/privacy/cancel-deletion', {
        method: 'POST',
        body: JSON.stringify({ cancel_token: deleteState.cancel_token }),
      });
      setDeleteState(null);
    } catch (err) {
      reportError(err, { scope: 'settings.privacy.cancel-delete' });
      setPrivacyError(toUserMessage(err, 'İptal işlemi başarısız oldu.'));
    } finally {
      setPrivacyBusy(false);
    }
  };

  // Kullanıcıdan tarayıcı düzeyinde cihaz izni iste; rıza alınınca kararı
  // kalıcı profil sütununa yaz ve üst bileşendeki status'u tazele.
  const handleGrantPermission = async (kind) => {
    setPermBusy(kind);
    setPermError('');
    try {
      if (!navigator.mediaDevices?.getUserMedia) {
        throw new Error('Tarayıcın cihaz erişimini desteklemiyor.');
      }
      const constraints = kind === 'camera'
        ? { video: { facingMode: 'user', width: { ideal: 640 }, height: { ideal: 480 } } }
        : { audio: true };
      const stream = await navigator.mediaDevices.getUserMedia(constraints);
      stream.getTracks().forEach((t) => t.stop()); // rıza alındı, hemen bırak
      await apiFetch('/api/profile', {
        method: 'PUT',
        body: JSON.stringify(kind === 'camera' ? { camera_permission_granted: true } : { microphone_permission_granted: true }),
      });
      onPermissionsChanged?.();
    } catch (err) {
      reportError(err, { scope: 'settings.permissions.grant' });
      const denied = err && (err.name === 'NotAllowedError' || err.name === 'SecurityError');
      setPermError(denied
        ? 'Tarayıcı izni reddedildi. Adres çubuğundaki kilit → Site ayarları → İzin ver dedikten sonra tekrar dene.'
        : toUserMessage(err, 'İzin alınamadı. Tarayıcı izinlerini kontrol edip tekrar dener misin?'));
    } finally {
      setPermBusy('');
    }
  };

  if (!open) return null;

  const handleClose = () => {
    onClose();
    setActiveTab(null);
  };

  const activeTabMeta = TABS.find((t) => t.key === activeTab);

  return (
    <>
      {/* Arka plan overlay */}
      <div
        className="fixed inset-0 bg-black/60 backdrop-blur-sm z-60 animate-fadeIn"
        onClick={handleClose}
      />

      {/* Panel: mobilde tam ekran alt sayfa gibi, masaüstünde sağdan açılan çekmece */}
      <div
        className="fixed inset-x-0 bottom-0 md:inset-y-0 md:right-0 md:left-auto md:w-105 z-61 bg-neutral-950 border-t md:border-t-0 md:border-l border-neutral-800 rounded-t-2xl md:rounded-none shadow-2xl animate-slideUp flex flex-col max-h-[88vh] md:max-h-none"
        style={{ paddingBottom: 'env(safe-area-inset-bottom)' }}
        role="dialog"
        aria-modal="true"
        aria-label="Ayarlar"
      >
        {/* Sürükleme tutamacı (iOS bottom-sheet hissi) */}
        <div className="md:hidden flex justify-center pt-2.5">
          <div className="w-10 h-1.5 rounded-full bg-neutral-700" />
        </div>

        <div className="flex items-center justify-between px-5 py-4 border-b border-neutral-900" style={{ paddingTop: 'max(env(safe-area-inset-top), 1rem)' }}>
          <div className="flex items-center gap-2 min-w-0">
            {activeTab && (
              <button
                onClick={() => setActiveTab(null)}
                className="p-1.5 -ml-1.5 rounded-lg text-neutral-400 hover:text-white hover:bg-neutral-800 transition-colors shrink-0"
                aria-label="Geri"
              >
                <ChevronLeft className="w-4.5 h-4.5" />
              </button>
            )}
            <h2 className="font-mono font-bold text-sm tracking-wide text-white truncate">
              {activeTabMeta ? activeTabMeta.label.toUpperCase() : 'AYARLAR'}
            </h2>
          </div>
          <button
            onClick={handleClose}
            className="p-2 -mr-2 rounded-lg text-neutral-500 hover:text-white hover:bg-neutral-800 transition-colors"
            aria-label="Kapat"
          >
            <X className="w-4.5 h-4.5" />
          </button>
        </div>

        {/* Kök menü listesi - iOS Ayarlar uygulamasındaki satır stiline benzer.
            Veri sadece bir satıra DOKUNULDUĞUNDA çekilir (openTab), otomatik değil. */}
        {!activeTab && (
          <div className="px-3 pt-3">
            {TABS.map(({ key, label, Icon }) => (
              <button
                key={key}
                onClick={() => openTab(key)}
                className="w-full flex items-center justify-between gap-3 px-3 py-3.5 rounded-xl text-left hover:bg-neutral-900 transition-colors"
              >
                <span className="flex items-center gap-3">
                  <span className="w-8 h-8 rounded-lg bg-orange-500/10 border border-orange-500/20 flex items-center justify-center">
                    <Icon className="w-4 h-4 text-orange-500" strokeWidth={2} />
                  </span>
                  <span className="text-sm text-neutral-200 font-medium">{label}</span>
                </span>
                <ChevronRight className="w-4 h-4 text-neutral-600" />
              </button>
            ))}
          </div>
        )}

        {activeTab && (
        <div className="flex-1 overflow-y-auto px-5 py-5 space-y-4">
          {activeTab === 'notifications' && (
            <div className="space-y-3">
              {notifLoading && (
                <div className="flex items-center gap-2 text-neutral-500 text-xs font-mono">
                  <Loader2 className="w-3.5 h-3.5 animate-spin" /> Yükleniyor...
                </div>
              )}
              {notifError && <p className="text-xs text-red-400 font-mono">⚠ {notifError}</p>}
              {notifSettings && NOTIF_TOGGLES.map(({ key, label }) => (
                <label
                  key={key}
                  className="flex items-center justify-between gap-3 bg-neutral-900/60 border border-neutral-800 rounded-xl px-4 py-3.5 cursor-pointer"
                >
                  <span className="text-sm text-neutral-200">{label}</span>
                  <button
                    type="button"
                    onClick={() => toggleNotif(key)}
                    disabled={notifSaving}
                    className={`relative w-10 h-6 rounded-full transition-colors shrink-0 ${notifSettings[key] ? 'bg-orange-500' : 'bg-neutral-700'}`}
                    aria-pressed={notifSettings[key]}
                  >
                    <span
                      className={`absolute top-0.5 left-0.5 w-5 h-5 rounded-full bg-white transition-transform ${notifSettings[key] ? 'translate-x-4' : 'translate-x-0'}`}
                    />
                  </button>
                </label>
              ))}
              {notifSettings && (
                <p className="text-[11px] text-neutral-500 font-mono pt-1">
                  Sessiz saatler: {notifSettings.quiet_hours_start}–{notifSettings.quiet_hours_end} (faturalandırma uyarıları hariç)
                </p>
              )}
            </div>
          )}

          {activeTab === 'sessions' && (
            <div className="space-y-2.5">
              {sessionsLoading && (
                <div className="flex items-center gap-2 text-neutral-500 text-xs font-mono">
                  <Loader2 className="w-3.5 h-3.5 animate-spin" /> Yükleniyor...
                </div>
              )}
              {sessionsError && <p className="text-xs text-red-400 font-mono">⚠ {sessionsError}</p>}
              {sessions?.length === 0 && (
                <p className="text-xs text-neutral-500 font-mono">Aktif oturum bulunamadı.</p>
              )}
              {sessions?.map((s) => (
                <div key={s.id} className="flex items-center justify-between gap-3 bg-neutral-900/60 border border-neutral-800 rounded-xl px-4 py-3.5">
                  <div className="min-w-0">
                    <p className="text-sm text-neutral-200 truncate">{s.device_name || s.user_agent || 'Bilinmeyen cihaz'}</p>
                    <p className="text-[10px] text-neutral-500 font-mono mt-0.5">
                      {s.ip_address || '—'} · son aktif {formatDateTime(s.last_active_at)}
                    </p>
                  </div>
                  <button
                    onClick={() => revokeSession(s.id)}
                    className="shrink-0 text-[10px] font-mono px-2.5 py-1.5 rounded-lg border border-neutral-700 text-neutral-400 hover:text-red-400 hover:border-red-500/40 transition-colors"
                  >
                    Sonlandır
                  </button>
                </div>
              ))}
            </div>
          )}

          {activeTab === 'permissions' && (
            <div className="space-y-3">
              {permError && (
                <p className="text-xs text-amber-400 font-mono leading-relaxed bg-amber-500/10 border border-amber-500/30 rounded-xl px-3.5 py-2.5">
                  ⚠ {permError}
                </p>
              )}
              {PERMISSION_ROWS.map(({ key, label, desc, Icon }) => {
                const granted = permissions[key] === true;
                const asked = permissions[key] !== null && permissions[key] !== undefined;
                return (
                  <div key={key} className="bg-neutral-900 border border-neutral-800 rounded-xl p-4">
                    <div className="flex items-start justify-between gap-3">
                      <div className="flex items-start gap-3 min-w-0">
                        <span className="w-8 h-8 shrink-0 rounded-lg bg-orange-500/10 border border-orange-500/20 flex items-center justify-center">
                          <Icon className="w-4 h-4 text-orange-500" strokeWidth={2} />
                        </span>
                        <div className="min-w-0">
                          <p className="text-sm font-bold text-white">{label}</p>
                          <p className="text-[11px] text-neutral-500 leading-snug mt-0.5">{desc}</p>
                        </div>
                      </div>
                      <span className={`shrink-0 text-[10px] font-mono px-2 py-1 rounded-lg border ${
                        granted
                          ? 'text-emerald-400 border-emerald-500/30 bg-emerald-500/10'
                          : asked
                            ? 'text-neutral-400 border-neutral-700'
                            : 'text-amber-400 border-amber-500/30 bg-amber-500/10'
                      }`}>
                        {granted ? 'VERİLDİ' : asked ? 'VERİLMEDİ' : 'SORULMADI'}
                      </span>
                    </div>
                    {!granted && (
                      <button
                        onClick={() => handleGrantPermission(key)}
                        disabled={!!permBusy}
                        className="mt-3 w-full flex items-center justify-center gap-2 bg-neutral-950 border border-neutral-700 hover:border-orange-500/40 hover:text-orange-400 text-neutral-300 text-xs font-mono py-2.5 rounded-lg transition-colors disabled:opacity-50"
                      >
                        {permBusy === key ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <ShieldCheck className="w-3.5 h-3.5" />}
                        İZİN VER
                      </button>
                    )}
                  </div>
                );
              })}
              <p className="text-[10px] text-neutral-500 font-mono leading-relaxed px-1">
                İzinler tamamen isteğe bağlıdır; verilmese de uygulamanın tüm özellikleri çalışır.
                Tarayıcı düzeyinde izni reddettiysen adres çubuğundaki kilit → Site ayarları menüsünden açabilirsin.
              </p>
            </div>
          )}

          {activeTab === 'privacy' && (
            <div className="space-y-4">
              {privacyError && <p className="text-xs text-red-400 font-mono">⚠ {privacyError}</p>}

              <button
                onClick={handleExportData}
                disabled={exporting}
                className="w-full flex items-center justify-center gap-2 bg-neutral-900 border border-neutral-800 hover:border-orange-500/40 text-neutral-200 text-sm font-mono py-3 rounded-xl transition-colors disabled:opacity-50"
              >
                {exporting ? <Loader2 className="w-4 h-4 animate-spin" /> : <Download className="w-4 h-4" />}
                Verilerimi İndir (JSON)
              </button>

              <div className="border-t border-neutral-900 pt-4">
                {!deleteState && (
                  <button
                    onClick={handleRequestDeletion}
                    disabled={privacyBusy}
                    className="w-full flex items-center justify-center gap-2 bg-red-500/10 border border-red-500/30 hover:bg-red-500/20 text-red-400 text-sm font-mono py-3 rounded-xl transition-colors disabled:opacity-50"
                  >
                    {privacyBusy ? <Loader2 className="w-4 h-4 animate-spin" /> : <Trash2 className="w-4 h-4" />}
                    Hesabımı Sil
                  </button>
                )}
                {deleteState && (
                  <div className="bg-red-500/10 border border-red-500/30 rounded-xl p-4 space-y-3">
                    <div className="flex items-start gap-2">
                      <AlertTriangle className="w-4 h-4 text-red-400 shrink-0 mt-0.5" />
                      <p className="text-xs text-red-300 leading-relaxed">
                        Hesabın <strong>{formatDateTime(deleteState.scheduled_for)}</strong> tarihinde kalıcı olarak
                        silinecek. Bu tarihe kadar iptal edebilirsin.
                      </p>
                    </div>
                    <button
                      onClick={handleCancelDeletion}
                      disabled={privacyBusy}
                      className="w-full flex items-center justify-center gap-2 bg-neutral-900 border border-neutral-700 text-neutral-200 text-xs font-mono py-2.5 rounded-lg hover:border-emerald-500/40 hover:text-emerald-400 transition-colors disabled:opacity-50"
                    >
                      <CheckCircle2 className="w-3.5 h-3.5" /> Silme İşlemini İptal Et
                    </button>
                  </div>
                )}
                <p className="text-[10px] text-neutral-500 font-mono mt-2 leading-relaxed">
                  30 günlük bekleme süresi boyunca hesabına giriş yaparak istediğin zaman iptal edebilirsin.
                </p>
              </div>
            </div>
          )}
        </div>
        )}

        <div className="px-5 py-4 border-t border-neutral-900">
          <button
            onClick={() => { handleClose(); onLogout(); }}
            className="w-full flex items-center justify-center gap-2 text-sm font-mono text-neutral-400 hover:text-red-400 py-2.5 transition-colors"
          >
            <LogOut className="w-4 h-4" /> Çıkış Yap
          </button>
        </div>
      </div>
    </>
  );
}
