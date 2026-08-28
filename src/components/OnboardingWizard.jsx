import { useEffect, useRef, useState } from 'react';
import {
  Camera, Mic, ShieldCheck, Check, X, ArrowRight, ArrowLeft, Sparkles,
  RefreshCw, Dumbbell, Salad, AlertTriangle, User, Target, Ruler,
  Zap, Video as VideoIcon,
} from 'lucide-react';
import { API_BASE } from '../config';
import * as authService from '../services/authService';

/**
 * ÇOK SAYFALI ONBOARDING WIZARD (izin akışlı).
 *
 * Adımlar:
 *  0) Hoş geldin — süreç hakkında şeffaf bilgi (hangi adımda kamera/mikrofon istenecek)
 *  1) Temel bilgiler (yaş, boy, kilo, hedef kilo)
 *  2) Hedefler (hedef, tecrübe, aktivite, odak kas grubu, hedef fizik)
 *  3) KAMERA İZNİ — açık rıza ekranı + verilirse vücut videosu kaydı & AI fizik analizi
 *  4) MİKROFON İZNİ — açık rıza ekranı + verilirse sesli yaşam anlatımı & AI profilleme
 *  5) Özet — tüm veriler + izin durumları, "Programımı Oluştur"
 *  6) Başarılı — üretilen program/öğün özetini gösterir
 *
 * İzin kararları (verildi/verilmedi) profil sütunlarına
 * (camera_permission_granted / microphone_permission_granted) kaydedilir; izin
 * verilmese bile sihirbaz "atla" ile devam edebilir — hiçbir adım izne zorunlu değildir.
 */

const MAX_VIDEO_SECONDS = 20;
const VIDEO_BITRATE = 1_200_000; // ~1.2 Mbps -> 20 sn ≈ 3 MB

const GOALS = [
  { id: 'fat_loss', label: 'Yağ Yakımı', desc: 'Vücut yağını düşür, kası koru' },
  { id: 'muscle_gain', label: 'Kas Kazanımı', desc: 'Kütleyi ve gücü artır' },
  { id: 'recomp', label: 'Rekompozisyon', desc: 'Aynı anda yağ yak + kas kazan' },
  { id: 'strength', label: 'Güç', desc: 'Büyük kaldırışlar, düşük tekrar' },
  { id: 'endurance', label: 'Dayanıklılık', desc: 'Kondisyon ve stamina' },
];

const ACTIVITY_LEVELS = [
  { id: 'sedentary', label: 'Hareketsiz', desc: 'Masabaşı, minimal hareket' },
  { id: 'light', label: 'Hafif Aktif', desc: 'Haftada 1-2 gün hafif spor' },
  { id: 'moderate', label: 'Orta Aktif', desc: 'Haftada 3-4 gün antrenman' },
  { id: 'very_active', label: 'Çok Aktif', desc: 'Haftada 5-6 gün yoğun antrenman' },
];

const EXPERIENCE_LEVELS = [
  { id: '0', label: 'Başlangıç', desc: 'Henüz düzenli antrenman yapmıyorum' },
  { id: '6', label: '6 Ay', desc: 'Birkaç aydır düzenli antrenman' },
  { id: '12', label: '1 Yıl', desc: 'Yaklaşık bir yıldır antrenman' },
  { id: '36', label: '3+ Yıl', desc: 'Uzun süredir deneyimliyim' },
];

const STEP_LABELS = ['Başla', 'Bilgiler', 'Hedefler', 'Kamera', 'Ses', 'Özet'];

export default function OnboardingWizard({ onComplete, setCurrentPage }) {
  // 0=welcome 1=basics 2=goals 3=camera 4=voice 5=summary 6=success
  const [step, setStep] = useState(0);

  const [form, setForm] = useState({
    age: '', height: '', current_weight: '', target_weight: '',
    goal: 'recomp', target_physique: '', experience_months: '0',
    focus_muscle_group: '', activity_level: 'moderate',
  });
  const [stepError, setStepError] = useState('');

  // İzin durumu: 'idle' | 'granted' | 'denied' | 'unavailable'
  const [camPerm, setCamPerm] = useState('idle');
  const [micPerm, setMicPerm] = useState('idle');

  const [mediaError, setMediaError] = useState('');
  const [isRecording, setIsRecording] = useState(false);
  const [recordSeconds, setRecordSeconds] = useState(0);

  const [videoBlob, setVideoBlob] = useState(null);
  const [videoReport, setVideoReport] = useState(null);
  const [analyzingVideo, setAnalyzingVideo] = useState(false);

  const [audioBlob, setAudioBlob] = useState(null);
  const [voiceResult, setVoiceResult] = useState(null);
  const [analyzingVoice, setAnalyzingVoice] = useState(false);

  const [finishing, setFinishing] = useState(false);
  const [finishError, setFinishError] = useState('');
  const [, setCompleted] = useState(null); // üretim artık ProgramBuilder'da; complete yalnızca profil kaydeder

  const videoPreviewRef = useRef(null);
  const streamRef = useRef(null);
  const recorderRef = useRef(null);
  const chunksRef = useRef([]);
  const autoStopTimerRef = useRef(null);
  const tickTimerRef = useRef(null);

  const updateForm = (key, value) => setForm((f) => ({ ...f, [key]: value }));

  // Sekme kapanınca/tekrar render'da açık kalan stream'i mutlaka bırak.
  const stopLiveStreams = () => {
    streamRef.current?.getTracks().forEach((t) => t.stop());
    streamRef.current = null;
    if (autoStopTimerRef.current) { clearTimeout(autoStopTimerRef.current); autoStopTimerRef.current = null; }
    if (tickTimerRef.current) { clearInterval(tickTimerRef.current); tickTimerRef.current = null; }
  };

  useEffect(() => () => stopLiveStreams(), []);

  // ----------------------------------------
  // İZİN AKIŞI — açık, tek amaçlı rıza isteği
  // ----------------------------------------
  const requestPermission = async (kind) => {
    setMediaError('');
    const setPerm = kind === 'camera' ? setCamPerm : setMicPerm;
    if (!navigator.mediaDevices?.getUserMedia) {
      setPerm('unavailable');
      setMediaError('Tarayıcın kamera/mikrofon erişimini desteklemiyor. Bu adımı atlayabilirsin.');
      return;
    }
    try {
      const constraints = kind === 'camera'
        ? { video: { facingMode: 'user', width: { ideal: 640 }, height: { ideal: 480 } } }
        : { audio: true };
      const stream = await navigator.mediaDevices.getUserMedia(constraints);
      stream.getTracks().forEach((t) => t.stop()); // rıza alındı, hemen bırak
      setPerm('granted');
    } catch (err) {
      console.warn(`[permission:${kind}]`, err);
      if (err && (err.name === 'NotFoundError' || err.name === 'OverconstrainedError')) setPerm('unavailable');
      else setPerm('denied');
    }
  };

  // ----------------------------------------
  // KAYIT — yalnızca izin verildiyse
  // ----------------------------------------
  const startRecording = async (kind) => {
    setMediaError('');
    const setPerm = kind === 'video' ? setCamPerm : setMicPerm;
    try {
      const constraints = kind === 'video'
        ? { video: { facingMode: 'user', width: { ideal: 640 }, height: { ideal: 480 } } }
        : { audio: true };
      const stream = await navigator.mediaDevices.getUserMedia(constraints);
      streamRef.current = stream;
      if (kind === 'video' && videoPreviewRef.current) {
        videoPreviewRef.current.srcObject = stream;
        videoPreviewRef.current.play().catch(() => {});
      }
      chunksRef.current = [];
      const recorderOptions = kind === 'video' ? { videoBitsPerSecond: VIDEO_BITRATE } : {};
      const recorder = new MediaRecorder(stream, recorderOptions);
      recorder.ondataavailable = (e) => { if (e.data.size > 0) chunksRef.current.push(e.data); };
      recorder.onstop = () => {
        const blob = new Blob(chunksRef.current, { type: kind === 'video' ? 'video/webm' : 'audio/webm' });
        if (kind === 'video') setVideoBlob(blob); else setAudioBlob(blob);
        stream.getTracks().forEach((t) => t.stop());
        setIsRecording(false);
        setRecordSeconds(0);
        if (autoStopTimerRef.current) { clearTimeout(autoStopTimerRef.current); autoStopTimerRef.current = null; }
        if (tickTimerRef.current) { clearInterval(tickTimerRef.current); tickTimerRef.current = null; }
      };
      recorder.start();
      recorderRef.current = recorder;
      setIsRecording(true);
      tickTimerRef.current = setInterval(() => setRecordSeconds((s) => s + 1), 1000);
      if (kind === 'video') {
        autoStopTimerRef.current = setTimeout(() => {
          if (recorderRef.current && recorderRef.current.state === 'recording') recorderRef.current.stop();
        }, MAX_VIDEO_SECONDS * 1000);
      }
    } catch (err) {
      console.error(err);
      setPerm('denied');
      setMediaError('Erişim başlatılamadı. Tarayıcı adres çubuğundaki kilit → İzinler menüsünden kontrol edip tekrar dener misin?');
    }
  };

  const stopRecording = () => {
    recorderRef.current?.stop();
  };

  const resetRecording = (kind) => {
    if (kind === 'video') { setVideoBlob(null); setVideoReport(null); }
    else { setAudioBlob(null); setVoiceResult(null); }
    setMediaError('');
  };

  // Backend hata detayını (413/503/500 vb.) göster; 401'de oturumu temizleyip login'e dön.
  const extractErrorMessage = async (res, fallback) => {
    try {
      const data = await res.json();
      return data.detail || fallback;
    } catch {
      return fallback;
    }
  };

  const handleIfSessionExpired = (res) => {
    if (res.status === 401) {
      authService.clearLocalSession();
      setCurrentPage('login');
      return true;
    }
    return false;
  };

  const analyzeVideo = async () => {
    if (!videoBlob) return;
    setAnalyzingVideo(true);
    setMediaError('');
    try {
      const fd = new FormData();
      fd.append('file', videoBlob, 'body-scan.webm');
      const res = await fetch(`${API_BASE}/api/onboarding/video`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${authService.getAccessToken()}` },
        body: fd,
      });
      if (handleIfSessionExpired(res)) return;
      if (!res.ok) {
        setMediaError(await extractErrorMessage(res, 'Video analiz edilemedi, tekrar dener misin?'));
        return;
      }
      setVideoReport(await res.json());
    } catch (e) {
      console.error(e);
      setMediaError('Sunucuya bağlanılamadı. Backend çalışıyor mu ve video çok uzun değil mi kontrol eder misin?');
    } finally {
      setAnalyzingVideo(false);
    }
  };

  const analyzeVoice = async () => {
    if (!audioBlob) return;
    setAnalyzingVoice(true);
    setMediaError('');
    try {
      const fd = new FormData();
      fd.append('file', audioBlob, 'voice-note.webm');
      const res = await fetch(`${API_BASE}/api/onboarding/voice`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${authService.getAccessToken()}` },
        body: fd,
      });
      if (handleIfSessionExpired(res)) return;
      if (!res.ok) {
        setMediaError(await extractErrorMessage(res, 'Ses kaydı analiz edilemedi, tekrar dener misin?'));
        return;
      }
      setVoiceResult(await res.json());
    } catch (e) {
      console.error(e);
      setMediaError('Sunucuya bağlanılamadı. Backend çalışıyor mu kontrol eder misin?');
    } finally {
      setAnalyzingVoice(false);
    }
  };

  const finishOnboarding = async () => {
    setFinishing(true);
    setFinishError('');
    try {
      const payload = {
        age: form.age ? parseInt(form.age, 10) : null,
        height: form.height ? parseFloat(form.height) : null,
        current_weight: form.current_weight ? parseFloat(form.current_weight) : null,
        target_weight: form.target_weight ? parseFloat(form.target_weight) : null,
        goal: form.goal || null,
        target_physique: form.target_physique || null,
        experience_months: form.experience_months ? parseInt(form.experience_months, 10) : null,
        focus_muscle_group: form.focus_muscle_group || null,
        activity_level: form.activity_level || null,
        // İzin kararlarını kalıcı olarak profil sütunlarına yaz.
        camera_permission_granted: camPerm === 'granted',
        microphone_permission_granted: micPerm === 'granted',
      };
      const res = await fetch(`${API_BASE}/api/onboarding/complete`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${authService.getAccessToken()}`,
        },
        body: JSON.stringify(payload),
      });
      if (handleIfSessionExpired(res)) return;
      if (!res.ok) {
        const detail = await extractErrorMessage(res, 'kurulum tamamlanamadı');
        throw new Error(detail);
      }
      const data = await res.json();
      setCompleted(data);
      setStep(6); // başarı ekranı
    } catch (e) {
      console.error(e);
      setFinishError(e.message && e.message !== 'kurulum tamamlanamadı' ? e.message : 'Kurulum tamamlanamadı, tekrar dener misin?');
    } finally {
      setFinishing(false);
    }
  };

  const goToDashboard = async () => {
    await onComplete();
  };

  // ----------------------------------------
  // ADIM DOĞRULAMA
  // ----------------------------------------
  const validateStep = (s) => {
    if (s === 1) {
      const age = parseInt(form.age, 10);
      if (!age || age < 14 || age > 90) return 'Lütfen geçerli bir yaş gir (14-90).';
      const h = parseFloat(form.height);
      if (!h || h < 120 || h > 230) return 'Lütfen geçerli bir boy gir (cm).';
      const w = parseFloat(form.current_weight);
      if (!w || w < 30 || w > 350) return 'Lütfen geçerli bir kilo gir (kg).';
      if (form.target_weight && parseFloat(form.target_weight) <= 0) return 'Hedef kilo sıfırdan büyük olmalı.';
    }
    return '';
  };

  const goToStep = (next) => {
    const err = validateStep(step);
    if (err) { setStepError(err); return; }
    setStepError('');
    setMediaError('');
    if (isRecording) stopRecording(); // kayıt sürerken sayfa değişirse güvenle durdur
    if (next < step) stopLiveStreams(); // geri gidişte canlı kaynağı kapat
    setStep(next);
  };

  const goalMeta = GOALS.find((g) => g.id === form.goal);
  const activityMeta = ACTIVITY_LEVELS.find((a) => a.id === form.activity_level);
  const expMeta = EXPERIENCE_LEVELS.find((e) => e.id === String(form.experience_months));

  if (step === 6) {
    return (
      <div className="min-h-screen bg-neutral-950 text-white flex items-center justify-center p-4">
        <div className="w-full max-w-md text-center space-y-5 animate-fadeIn">
          <div className="w-16 h-16 mx-auto rounded-2xl bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center">
            <Check className="w-8 h-8 text-emerald-400" strokeWidth={2.5} />
          </div>
          <h1 className="text-2xl font-black font-mono tracking-wide">PROFİLİN HAZIR</h1>
          <p className="text-sm text-neutral-400 leading-relaxed">
            Temel bilgilerin kaydedildi. Şimdi iki ayrı detaylı anketle antrenman ve
            beslenme programlarını <span className="text-orange-400 font-bold">tamamen sana özel</span> oluşturacağız.
          </p>
          <div className="text-left bg-neutral-900 border border-neutral-800 rounded-2xl p-4 space-y-2.5">
            {[
              { Icon: Dumbbell, label: 'Antrenman', desc: 'Ekipman, program, sakatlık ve hedef soruları' },
              { Icon: Salad, label: 'Beslenme', desc: 'Alerji, bütçe, mutfak ve damak tadı soruları' },
            ].map(({ Icon, label, desc }) => (
              <div key={label} className="flex items-start gap-2.5">
                <Icon className="w-4 h-4 text-orange-400 shrink-0 mt-0.5" />
                <div>
                  <p className="text-xs font-bold">{label} Oluşturucu</p>
                  <p className="text-[10px] text-neutral-500 leading-snug">{desc}</p>
                </div>
              </div>
            ))}
          </div>
          <button
            onClick={goToDashboard}
            className="w-full bg-orange-500 hover:bg-orange-400 text-black font-bold font-mono text-sm tracking-wide py-3.5 rounded-xl transition-all flex items-center justify-center gap-2 cursor-pointer"
          >
            PROGRAM OLUŞTURUCUYA GEÇ <ArrowRight className="w-4 h-4" />
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-neutral-950 text-white flex flex-col items-center justify-center p-4 sm:p-6">
      {/* Donmayan arkaplan: blur filtresi yerine radial gradient */}
      <div
        className="absolute inset-0 pointer-events-none"
        style={{ background: 'radial-gradient(ellipse 60% 40% at 50% 0%, rgba(249,115,22,0.07), transparent 70%)' }}
      />
      <div className="relative w-full max-w-xl">
        {/* İlerleme göstergesi */}
        <div className="mb-6">
          <div className="flex items-center justify-between mb-2">
            {STEP_LABELS.map((label, i) => (
              <button
                key={label}
                onClick={() => { if (i < step) goToStep(i); }}
                disabled={i > step}
                className={`text-[10px] font-mono uppercase tracking-widest transition-colors ${
                  i === step ? 'text-orange-400 font-bold' : i < step ? 'text-neutral-400 hover:text-white' : 'text-neutral-700'
                }`}
              >
                {label}
              </button>
            ))}
          </div>
          <div className="h-1 bg-neutral-800 rounded-full overflow-hidden flex gap-1">
            {STEP_LABELS.map((_, i) => (
              <div
                key={i}
                className={`h-full flex-1 rounded-full transition-all duration-300 ${i <= step ? 'bg-orange-500' : 'bg-neutral-800'}`}
              />
            ))}
          </div>
        </div>

        <div className="bg-neutral-900 border border-neutral-800 rounded-2xl p-6 sm:p-8 shadow-2xl shadow-black/60 animate-fadeIn">
          {stepError && (
            <div className="bg-red-500/10 border border-red-500/30 text-red-400 text-xs px-4 py-3 rounded-xl mb-5 font-mono">
              ⚠ {stepError}
            </div>
          )}

          {/* ADIM 0: HOŞ GELDİN */}
          {step === 0 && (
            <div className="space-y-5 text-center">
              <div className="w-14 h-14 mx-auto rounded-2xl bg-orange-500/10 border border-orange-500/30 flex items-center justify-center">
                <Sparkles className="w-7 h-7 text-orange-400" />
              </div>
              <h1 className="text-2xl font-black font-mono tracking-wide">
                HOŞ GELDİN <span className="text-orange-500">SPORÇU</span>
              </h1>
              <p className="text-sm text-neutral-400 leading-relaxed">
                5 kısa adımda seni tanıyıp tamamen sana özel bir antrenman ve beslenme programı kuracağım.
              </p>
              <div className="grid grid-cols-2 gap-3 text-left">
                {[
                  { Icon: User, title: 'Bilgiler', desc: 'Yaş, boy, kilo ve hedeflerin' },
                  { Icon: Target, title: 'Hedefler', desc: 'Amacın ve tecrüben' },
                  { Icon: Camera, title: 'Kamera', desc: 'İstersen vücut videosu ile fizik analizi' },
                  { Icon: Mic, title: 'Mikrofon', desc: 'İstersen sesli anlatım ile yaşam rutini' },
                ].map(({ Icon, title, desc }) => (
                  <div key={title} className="bg-neutral-950 border border-neutral-800 rounded-xl p-3.5">
                    <Icon className="w-4 h-4 text-orange-400 mb-2" />
                    <p className="text-xs font-bold">{title}</p>
                    <p className="text-[11px] text-neutral-500 leading-snug mt-0.5">{desc}</p>
                  </div>
                ))}
              </div>
              <div className="bg-neutral-950 border border-neutral-800 rounded-xl p-3.5 flex items-start gap-2.5 text-left">
                <ShieldCheck className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
                <p className="text-[11px] text-neutral-400 leading-relaxed">
                  Kamera ve mikrofon <span className="text-white font-bold">tamamen isteğe bağlıdır</span> ve
                  kullanmadan önce ayrı ayrı, açıkça iznin istenir. İzin vermezsen sihirbaz yine de tamamlanır.
                </p>
              </div>
              <button
                onClick={() => goToStep(1)}
                className="w-full bg-orange-500 hover:bg-orange-400 text-black font-bold font-mono text-sm tracking-wide py-3.5 rounded-xl transition-all flex items-center justify-center gap-2 cursor-pointer"
              >
                BAŞLAYALIM <ArrowRight className="w-4 h-4" />
              </button>
            </div>
          )}

          {/* ADIM 1: TEMEL BİLGİLER */}
          {step === 1 && (
            <div className="space-y-4">
              <StepHeader Icon={Ruler} title="TEMEL BİLGİLER" desc="Programı tam senin ölçülerine göre kuracağım." />
              <div className="grid grid-cols-2 gap-3">
                <NumberField label="Yaş" value={form.age} onChange={(v) => updateForm('age', v)} placeholder="24" suffix="yıl" />
                <NumberField label="Boy" value={form.height} onChange={(v) => updateForm('height', v)} placeholder="178" suffix="cm" />
                <NumberField label="Mevcut Kilo" value={form.current_weight} onChange={(v) => updateForm('current_weight', v)} placeholder="82" suffix="kg" />
                <NumberField label="Hedef Kilo (ops.)" value={form.target_weight} onChange={(v) => updateForm('target_weight', v)} placeholder="78" suffix="kg" />
              </div>
              <StepNav onBack={() => goToStep(0)} onNext={() => goToStep(2)} nextLabel="DEVAM ET" />
            </div>
          )}

          {/* ADIM 2: HEDEFLER */}
          {step === 2 && (
            <div className="space-y-4">
              <StepHeader Icon={Target} title="HEDEFLERİN" desc="Ne yapmak istiyorsun? Program buna göre şekillenecek." />
              <div className="space-y-2">
                {GOALS.map((g) => (
                  <button
                    key={g.id}
                    onClick={() => updateForm('goal', g.id)}
                    className={`w-full text-left px-4 py-3 rounded-xl border transition-all cursor-pointer ${
                      form.goal === g.id
                        ? 'border-orange-500 bg-orange-500/10'
                        : 'border-neutral-800 bg-neutral-950 hover:border-neutral-700'
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <p className={`text-sm font-bold ${form.goal === g.id ? 'text-orange-400' : 'text-white'}`}>{g.label}</p>
                      {form.goal === g.id && <Check className="w-4 h-4 text-orange-400" />}
                    </div>
                    <p className="text-[11px] text-neutral-500 mt-0.5">{g.desc}</p>
                  </button>
                ))}
              </div>
              <div>
                <label className="block text-[11px] font-mono tracking-widest text-neutral-400 uppercase mb-2">Tecrübe</label>
                <div className="grid grid-cols-4 gap-2">
                  {EXPERIENCE_LEVELS.map((e) => (
                    <button
                      key={e.id}
                      onClick={() => updateForm('experience_months', e.id)}
                      title={e.desc}
                      className={`py-2.5 rounded-xl border text-[11px] font-mono transition-all cursor-pointer ${
                        String(form.experience_months) === e.id
                          ? 'border-orange-500 bg-orange-500/10 text-orange-400'
                          : 'border-neutral-800 bg-neutral-950 text-neutral-400 hover:border-neutral-700'
                      }`}
                    >
                      {e.label}
                    </button>
                  ))}
                </div>
              </div>
              <div>
                <label className="block text-[11px] font-mono tracking-widest text-neutral-400 uppercase mb-2">Günlük Aktivite</label>
                <div className="grid grid-cols-2 gap-2">
                  {ACTIVITY_LEVELS.map((a) => (
                    <button
                      key={a.id}
                      onClick={() => updateForm('activity_level', a.id)}
                      className={`text-left px-3.5 py-2.5 rounded-xl border transition-all cursor-pointer ${
                        form.activity_level === a.id
                          ? 'border-orange-500 bg-orange-500/10'
                          : 'border-neutral-800 bg-neutral-950 hover:border-neutral-700'
                      }`}
                    >
                      <p className={`text-xs font-bold ${form.activity_level === a.id ? 'text-orange-400' : 'text-white'}`}>{a.label}</p>
                      <p className="text-[10px] text-neutral-500">{a.desc}</p>
                    </button>
                  ))}
                </div>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <TextField label="Odak Kas Grubu (ops.)" value={form.focus_muscle_group} onChange={(v) => updateForm('focus_muscle_group', v)} placeholder="Omuz, sırt..." />
                <TextField label="Hedef Fizik (ops.)" value={form.target_physique} onChange={(v) => updateForm('target_physique', v)} placeholder="Atletik, geniş omuz..." />
              </div>
              <StepNav onBack={() => goToStep(1)} onNext={() => goToStep(3)} nextLabel="DEVAM ET" />
            </div>
          )}

          {/* ADIM 3: KAMERA İZNİ + VÜCUT VİDEOSU */}
          {step === 3 && (
            <div className="space-y-4">
              <StepHeader Icon={Camera} title="KAMERA" desc="İyi ışıkta, önden ve yandan dönerken kısa bir vücut videosu kaydedersen fizikini analiz edip programa işleyebilirim." />

              {camPerm !== 'granted' ? (
                <PermissionPrompt
                  kind="camera"
                  status={camPerm}
                  onRequest={() => requestPermission('camera')}
                  points={[
                    'Video yalnızca fizik analizi için kullanılır',
                    'Tarayıcıdan çıkarmadan önce sen silebilirsin',
                    'Verilmezse bu adım atlanır, kurulum tamamlanır',
                  ]}
                />
              ) : (
                <div className="bg-neutral-950 border border-neutral-800 rounded-xl p-4 flex flex-col items-center gap-3">
                  {!videoBlob && !isRecording && (
                    <>
                      <VideoIcon className="w-8 h-8 text-orange-400" />
                      <p className="text-xs text-neutral-400 text-center">Kamera hazır. Kayda basıp yavaşça önden ve yandan dön.</p>
                      <button onClick={() => startRecording('video')} className="w-full bg-red-600 hover:bg-red-500 text-white font-bold py-2.5 rounded-xl text-xs cursor-pointer transition-colors">
                        ● KAYDI BAŞLAT <span className="opacity-70">(max {MAX_VIDEO_SECONDS} sn)</span>
                      </button>
                    </>
                  )}
                  <video ref={videoPreviewRef} muted playsInline className={`w-full rounded-xl border border-neutral-800 ${isRecording ? '' : 'hidden'}`} />
                  {isRecording && (
                    <div className="flex flex-col items-center gap-2 w-full">
                      <div className="flex items-center gap-2 text-red-400 font-mono text-xs">
                        <span className="w-2.5 h-2.5 rounded-full bg-red-500 animate-pulse" />
                        KAYIT · {recordSeconds}s / {MAX_VIDEO_SECONDS}s
                      </div>
                      <button onClick={stopRecording} className="w-full bg-neutral-700 hover:bg-neutral-600 text-white font-bold py-2.5 rounded-xl text-xs cursor-pointer transition-colors">
                        ■ DURDUR
                      </button>
                    </div>
                  )}
                  {videoBlob && (
                    <>
                      <video src={URL.createObjectURL(videoBlob)} controls className="w-full rounded-xl border border-neutral-800" />
                      {!videoReport ? (
                        <div className="flex gap-2 w-full">
                          <button onClick={() => resetRecording('video')} className="flex-1 bg-neutral-800 hover:bg-neutral-700 text-white font-bold py-2.5 rounded-xl text-xs cursor-pointer transition-colors flex items-center justify-center gap-1.5">
                            <RefreshCw className="w-3.5 h-3.5" /> TEKRAR
                          </button>
                          <button onClick={analyzeVideo} disabled={analyzingVideo} className="flex-1 bg-orange-500 hover:bg-orange-400 text-black font-bold py-2.5 rounded-xl text-xs disabled:opacity-50 cursor-pointer transition-colors">
                            {analyzingVideo ? 'ANALİZ EDİLİYOR...' : 'GÖNDER & ANALİZ ET'}
                          </button>
                        </div>
                      ) : (
                        <div className="w-full bg-emerald-500/5 border border-emerald-500/30 rounded-xl p-3.5 text-xs text-neutral-300 leading-relaxed max-h-44 overflow-y-auto custom-scrollbar">
                          <p className="text-emerald-400 font-bold mb-1.5 flex items-center gap-1.5"><Zap className="w-3.5 h-3.5" /> Fizik Analizi:</p>
                          <p className="whitespace-pre-line">{typeof videoReport === 'string' ? videoReport : videoReport.report || videoReport.summary || JSON.stringify(videoReport)}</p>
                        </div>
                      )}
                    </>
                  )}
                </div>
              )}

              {mediaError && (
                <div className="bg-amber-500/10 border border-amber-500/30 text-amber-400 text-xs px-4 py-3 rounded-xl font-mono flex items-start gap-2">
                  <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" /> {mediaError}
                </div>
              )}

              <StepNav
                onBack={() => goToStep(2)}
                onNext={() => goToStep(4)}
                nextLabel={camPerm === 'granted' && !videoReport ? 'ATLA →' : 'DEVAM ET →'}
                skipHint={!videoReport ? 'Video olmadan da program oluşturulabilir' : null}
              />
            </div>
          )}

          {/* ADIM 4: MİKROFON İZNİ + SESLİ ANLATIM */}
          {step === 4 && (
            <div className="space-y-4">
              <StepHeader Icon={Mic} title="MİKROFON" desc="Güncel beslenmeni, antrenmanlarını, günlük rutinini ve gerçek hedefini kısaça anlat — hepsini profile işlerim." />

              {micPerm !== 'granted' ? (
                <PermissionPrompt
                  kind="microphone"
                  status={micPerm}
                  onRequest={() => requestPermission('microphone')}
                  points={[
                    'Sesin metne çevrilip tercihlerin profiline yazılır',
                    'Ham ses dosyası saklanmaz',
                    'Verilmezse bu adım atlanır, kurulum tamamlanır',
                  ]}
                />
              ) : (
                <div className="bg-neutral-950 border border-neutral-800 rounded-xl p-4 flex flex-col items-center gap-3">
                  {!audioBlob && !isRecording && (
                    <>
                      <Mic className="w-8 h-8 text-orange-400" />
                      <p className="text-xs text-neutral-400 text-center">Mikrofon hazır. Kayda basıp kendini rahatça anlat.</p>
                      <button onClick={() => startRecording('audio')} className="w-full bg-red-600 hover:bg-red-500 text-white font-bold py-2.5 rounded-xl text-xs cursor-pointer transition-colors">
                        ● KAYDI BAŞLAT
                      </button>
                    </>
                  )}
                  {isRecording && (
                    <div className="flex flex-col items-center gap-2 w-full">
                      <div className="flex items-center gap-2 text-red-400 font-mono text-xs">
                        <span className="w-2.5 h-2.5 rounded-full bg-red-500 animate-pulse" />
                        KAYIT · {recordSeconds}s
                      </div>
                      <button onClick={stopRecording} className="w-full bg-neutral-700 hover:bg-neutral-600 text-white font-bold py-2.5 rounded-xl text-xs cursor-pointer transition-colors">
                        ■ DURDUR
                      </button>
                    </div>
                  )}
                  {audioBlob && !voiceResult && (
                    <>
                      <audio src={URL.createObjectURL(audioBlob)} controls className="w-full" />
                      <div className="flex gap-2 w-full">
                        <button onClick={() => resetRecording('audio')} className="flex-1 bg-neutral-800 hover:bg-neutral-700 text-white font-bold py-2.5 rounded-xl text-xs cursor-pointer transition-colors flex items-center justify-center gap-1.5">
                          <RefreshCw className="w-3.5 h-3.5" /> TEKRAR
                        </button>
                        <button onClick={analyzeVoice} disabled={analyzingVoice} className="flex-1 bg-orange-500 hover:bg-orange-400 text-black font-bold py-2.5 rounded-xl text-xs disabled:opacity-50 cursor-pointer transition-colors">
                          {analyzingVoice ? 'İŞLENİYOR...' : 'GÖNDER'}
                        </button>
                      </div>
                    </>
                  )}
                  {voiceResult && (
                    <div className="w-full bg-emerald-500/5 border border-emerald-500/30 rounded-xl p-3.5 text-xs text-neutral-300 leading-relaxed max-h-44 overflow-y-auto custom-scrollbar">
                      <p className="text-emerald-400 font-bold mb-1.5 flex items-center gap-1.5"><Zap className="w-3.5 h-3.5" /> Anladıklarım:</p>
                      <p>{voiceResult.summary || voiceResult.transcript}</p>
                    </div>
                  )}
                </div>
              )}

              {mediaError && (
                <div className="bg-amber-500/10 border border-amber-500/30 text-amber-400 text-xs px-4 py-3 rounded-xl font-mono flex items-start gap-2">
                  <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" /> {mediaError}
                </div>
              )}

              <StepNav
                onBack={() => goToStep(3)}
                onNext={() => goToStep(5)}
                nextLabel={micPerm === 'granted' && !voiceResult ? 'ATLA →' : 'DEVAM ET →'}
                skipHint={!voiceResult ? 'Ses kaydı olmadan da program oluşturulabilir' : null}
              />
            </div>
          )}

          {/* ADIM 5: ÖZET + PROGRAM OLUŞTUR */}
          {step === 5 && (
            <div className="space-y-4">
              <StepHeader Icon={Sparkles} title="SON KONTROL" desc="Her şey hazır. Verdiğin bilgileri birleştirip sana özel programı kuruyorum." />
              <div className="bg-neutral-950 border border-neutral-800 rounded-xl divide-y divide-neutral-800/70 text-xs">
                <SummaryRow label="Hedef" value={goalMeta?.label} />
                <SummaryRow label="Tecrübe" value={expMeta?.label} />
                <SummaryRow label="Aktivite" value={activityMeta?.label} />
                <SummaryRow label="Kamera izni" value={camPerm === 'granted' ? 'Verildi ✓' : camPerm === 'denied' ? 'Verilmedi (atlandı)' : 'İstenmedi'} ok={camPerm === 'granted'} />
                <SummaryRow label="Mikrofon izni" value={micPerm === 'granted' ? 'Verildi ✓' : micPerm === 'denied' ? 'Verilmedi (atlandı)' : 'İstenmedi'} ok={micPerm === 'granted'} />
                <SummaryRow label="Fizik analizi" value={videoReport ? 'Tamamlandı' : 'Atlandı'} ok={!!videoReport} />
                <SummaryRow label="Sesli profil" value={voiceResult ? 'Tamamlandı' : 'Atlandı'} ok={!!voiceResult} />
              </div>
              {finishError && (
                <div className="bg-red-500/10 border border-red-500/30 text-red-400 text-xs px-4 py-3 rounded-xl font-mono flex items-start gap-2">
                  <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" /> {finishError}
                </div>
              )}
              <button
                onClick={finishOnboarding}
                disabled={finishing}
                className="w-full bg-orange-500 hover:bg-orange-400 text-black font-bold font-mono text-sm tracking-wide py-3.5 rounded-xl transition-all flex items-center justify-center gap-2 disabled:opacity-50 cursor-pointer"
              >
                {finishing ? (
                  <><RefreshCw className="w-4 h-4 animate-spin" /> KAYDEDİLİYOR...</>
                ) : (
                  <>KURULUMU TAMAMLA <ArrowRight className="w-4 h-4" /></>
                )}
              </button>
              <button onClick={() => goToStep(4)} className="w-full text-center text-xs text-neutral-500 hover:text-neutral-300 transition-colors cursor-pointer">
                ← Geri
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

/* ---------- Yardımcı alt bileşenler ---------- */

function StepHeader({ Icon, title, desc }) {
  return (
    <div className="flex items-start gap-3">
      <div className="w-10 h-10 shrink-0 rounded-xl bg-orange-500/10 border border-orange-500/20 flex items-center justify-center">
        <Icon className="w-5 h-5 text-orange-400" />
      </div>
      <div>
        <h2 className="text-base font-black font-mono tracking-wide">{title}</h2>
        <p className="text-xs text-neutral-500 leading-relaxed mt-0.5">{desc}</p>
      </div>
    </div>
  );
}

function StepNav({ onBack, onNext, nextLabel, skipHint }) {
  return (
    <div className="flex items-center justify-between pt-2">
      <button onClick={onBack} className="text-xs text-neutral-500 hover:text-neutral-300 transition-colors cursor-pointer flex items-center gap-1">
        <ArrowLeft className="w-3.5 h-3.5" /> Geri
      </button>
      <div className="text-right">
        <button
          onClick={onNext}
          className="bg-orange-500 hover:bg-orange-400 text-black font-bold font-mono text-xs tracking-wide px-5 py-2.5 rounded-xl transition-all inline-flex items-center gap-1.5 cursor-pointer"
        >
          {nextLabel} <ArrowRight className="w-3.5 h-3.5" />
        </button>
        {skipHint && <p className="text-[10px] text-neutral-600 mt-1.5 font-mono">{skipHint}</p>}
      </div>
    </div>
  );
}

const PERM_STATUS_META = {
  idle: { Icon: ShieldCheck, tone: 'text-neutral-400', label: 'İzin istenmedi' },
  denied: { Icon: X, tone: 'text-red-400', label: 'İzin verilmedi' },
  unavailable: { Icon: AlertTriangle, tone: 'text-amber-400', label: 'Cihazda uygun donanım bulunamadı' },
};

function PermissionPrompt({ kind, status, onRequest, points }) {
  const meta = PERM_STATUS_META[status] || PERM_STATUS_META.idle;
  const StatusIcon = meta.Icon;
  return (
    <div className="bg-neutral-950 border border-neutral-800 rounded-xl p-5 space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          {kind === 'camera' ? <Camera className="w-5 h-5 text-orange-400" /> : <Mic className="w-5 h-5 text-orange-400" />}
          <span className="text-sm font-bold">{kind === 'camera' ? 'Kamera erişimi' : 'Mikrofon erişimi'} istiyorum</span>
        </div>
        <span className={`flex items-center gap-1.5 text-[10px] font-mono uppercase tracking-widest ${meta.tone}`}>
          <StatusIcon className="w-3.5 h-3.5" /> {meta.label}
        </span>
      </div>
      <ul className="space-y-1.5">
        {points.map((p) => (
          <li key={p} className="flex items-start gap-2 text-[11px] text-neutral-400 leading-relaxed">
            <Check className="w-3.5 h-3.5 text-emerald-400 shrink-0 mt-0.5" /> {p}
          </li>
        ))}
      </ul>
      {status === 'denied' && (
        <p className="text-[11px] text-amber-400/90 leading-relaxed">
          Tarayıcı izni kapalı görünüyor. Adres çubuğundaki kilit → Site ayarları → Kamera/Mikrofon → 'İzin ver'
          diyip tekrar deneyebilirsin ya da bu adımı atlayabilirsin.
        </p>
      )}
      {status !== 'unavailable' && (
        <button
          onClick={onRequest}
          className="w-full bg-orange-500 hover:bg-orange-400 text-black font-bold font-mono text-xs tracking-wide py-3 rounded-xl transition-all flex items-center justify-center gap-2 cursor-pointer"
        >
          <ShieldCheck className="w-4 h-4" />
          {status === 'denied' ? 'TEKRAR DENE' : 'İZİN VER'}
        </button>
      )}
    </div>
  );
}

function FieldShell({ label, children }) {
  return (
    <div>
      <label className="block text-[11px] font-mono tracking-widest text-neutral-400 uppercase mb-2">{label}</label>
      {children}
    </div>
  );
}

function NumberField({ label, value, onChange, placeholder, suffix }) {
  return (
    <FieldShell label={label}>
      <div className="relative">
        <input
          type="number"
          inputMode="decimal"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder={placeholder}
          className="w-full bg-neutral-950 border border-neutral-800 rounded-xl px-3.5 py-3 text-sm text-white placeholder-neutral-600 focus:outline-none focus:border-orange-500 focus:ring-1 focus:ring-orange-500 transition-colors"
        />
        {suffix && <span className="absolute right-3.5 top-1/2 -translate-y-1/2 text-[10px] font-mono text-neutral-600 uppercase">{suffix}</span>}
      </div>
    </FieldShell>
  );
}

function TextField({ label, value, onChange, placeholder }) {
  return (
    <FieldShell label={label}>
      <input
        type="text"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        className="w-full bg-neutral-950 border border-neutral-800 rounded-xl px-3.5 py-3 text-sm text-white placeholder-neutral-600 focus:outline-none focus:border-orange-500 focus:ring-1 focus:ring-orange-500 transition-colors"
      />
    </FieldShell>
  );
}

function SummaryRow({ label, value, ok }) {
  return (
    <div className="flex items-center justify-between px-4 py-2.5">
      <span className="text-neutral-500 font-mono uppercase tracking-wider text-[10px]">{label}</span>
      <span className={`font-bold ${ok === true ? 'text-emerald-400' : ok === false ? 'text-neutral-400' : 'text-white'}`}>
        {value || '—'}
      </span>
    </div>
  );
}
