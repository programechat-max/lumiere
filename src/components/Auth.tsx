import { useRef, useState } from 'react';
import { ArrowRight, Camera, Check, ChevronRight, Flame, Footprints, MoonStar, Sparkles, Target, Trophy, UtensilsCrossed, Dumbbell } from 'lucide-react';
import { Logo } from './chrome';
import { FORM_GROUPS } from './BioData';
import { splitLabel } from '../lib/planner';
import { apiFetch } from '../services/apiClient';
import type { Store } from '../lib/store';

export function AuthShell({ children, foot }: { children: React.ReactNode; foot?: React.ReactNode }) {
  return (
    <div className="min-h-dvh bg-[#f4f1ec] text-[#1c1512]">
      <div className="pointer-events-none fixed inset-0 overflow-hidden">
        <div className="absolute -top-32 left-1/2 h-80 w-[560px] -translate-x-1/2 rounded-full bg-[#d92835]/15 blur-[100px]" />
        <div className="absolute -bottom-40 -left-24 h-80 w-80 rounded-full bg-[#c99a3f]/15 blur-[90px]" />
      </div>
      <div className="relative mx-auto flex min-h-dvh w-full max-w-md flex-col px-6 pb-10 pt-8">
        <Logo />
        <div className="flex flex-1 flex-col justify-center py-8">{children}</div>
        {foot && <div className="pb-2 text-center text-xs font-semibold text-[#9a8c80]">{foot}</div>}
      </div>
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="block">
      <span className="eyebrow text-[#9a8c80]">{label}</span>
      <div className="mt-1.5">{children}</div>
    </label>
  );
}
const inputCls = 'h-13 w-full rounded-2xl border border-[#e2d7c6] bg-white px-4 py-3.5 text-[15px] font-semibold text-[#1c1512] outline-none placeholder:font-normal placeholder:text-[#b3a696] focus:border-[#d92835] focus:ring-2 focus:ring-[#d92835]/15';

export function LoginScreen({ store, go }: { store: Store; go: (p: 'register' | 'app') => void }) {
  const [email, setEmail] = useState('');
  const [pass, setPass] = useState('');
  const [err, setErr] = useState('');
  const [busy, setBusy] = useState(false);
  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email.includes('@') || pass.length < 4) { setErr('E-posta ve şifreni kontrol et.'); return; }
    setBusy(true);
    setErr('');
    try {
      await store.login(email.trim(), pass);
      go('app');
    } catch (ex) {
      setErr(ex instanceof Error ? ex.message : 'Giriş başarısız oldu.');
    } finally {
      setBusy(false);
    }
  };
  return (
    <AuthShell foot={<>Lumiere Coaching · Yapay zekâ destekli antrenman & beslenme</>}>
      <div className="rise-in">
        <p className="eyebrow text-[#d92835]">Tekrar hoş geldin</p>
        <h1 className="font-display mt-2 text-[34px] font-extrabold leading-[1.05]">Ritmine<br />geri dön<span className="text-[#d92835]">.</span></h1>
        <p className="mt-3 text-sm font-medium leading-relaxed text-[#6f6259]">12 günlük serin seni bekliyor. Bugünün planı ve koçun hazır.</p>
      </div>
      <form onSubmit={submit} className="rise-in stagger-1 mt-7 space-y-4">
        <Field label="E-posta">
          <input className={inputCls} value={email} onChange={(e) => setEmail(e.target.value)} placeholder="ornek@eposta.com" inputMode="email" />
        </Field>
        <Field label="Şifre">
          <input className={inputCls} type="password" value={pass} onChange={(e) => setPass(e.target.value)} placeholder="••••••••" />
        </Field>
        {err && <p className="rounded-xl bg-[#fde1df] px-3 py-2.5 text-xs font-bold text-[#8f1826]">{err}</p>}
        <button type="submit" disabled={busy} className="ember-btn flex h-13 w-full items-center justify-center gap-2 rounded-2xl py-4 text-[15px] font-extrabold">
          {busy ? <span className="h-5 w-5 animate-spin rounded-full border-2 border-white/40 border-t-white" /> : <>Giriş yap <ArrowRight size={18} /></>}
        </button>
      </form>
      <button onClick={() => go('register')} className="rise-in stagger-2 mt-5 w-full text-center text-sm font-bold text-[#6f6259]">
        Hesabın yok mu? <span className="text-[#d92835]">Kayıt ol</span>
      </button>
      <div className="rise-in stagger-3 mt-7 grid grid-cols-3 gap-2">
        {[
          { Icon: Footprints, t: 'Otomatik adım' },
          { Icon: MoonStar, t: 'Uyku takibi' },
          { Icon: Sparkles, t: 'AI koç' },
        ].map(({ Icon, t }) => (
          <div key={t} className="card-paper flex flex-col items-center gap-1.5 rounded-2xl px-2 py-3.5 text-center">
            <Icon size={18} className="text-[#d92835]" />
            <span className="text-[10px] font-extrabold">{t}</span>
          </div>
        ))}
      </div>
    </AuthShell>
  );
}

export function RegisterScreen({ store, go }: { store: Store; go: (p: 'login' | 'onboard') => void }) {
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [pass, setPass] = useState('');
  const [err, setErr] = useState('');
  const [busy, setBusy] = useState(false);
  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim() || !email.includes('@') || pass.length < 6) {
      setErr('Ad, geçerli e-posta ve en az 6 karakter şifre gerekli.');
      return;
    }
    setBusy(true);
    setErr('');
    try {
      await store.register(name.trim(), email.trim(), pass);
      store.setProfile({ ...store.profile, name: name.trim().split(' ')[0] });
      go('onboard');
    } catch (ex) {
      setErr(ex instanceof Error ? ex.message : 'Kayıt başarısız oldu.');
    } finally {
      setBusy(false);
    }
  };
  return (
    <AuthShell foot={<button onClick={() => go('login')} className="font-bold text-[#6f6259]">Zaten üye misin? <span className="text-[#d92835]">Giriş yap</span></button>}>
      <p className="eyebrow text-[#d92835]">30 saniyede başla</p>
      <h1 className="font-display mt-2 text-[34px] font-extrabold leading-[1.05]">Koçunla<br />tanış<span className="text-[#d92835]">.</span></h1>
      <form onSubmit={submit} className="mt-7 space-y-4">
        <Field label="Adın">
          <input className={inputCls} value={name} onChange={(e) => setName(e.target.value)} placeholder="Adın" required />
        </Field>
        <Field label="E-posta">
          <input className={inputCls} value={email} onChange={(e) => setEmail(e.target.value)} placeholder="ornek@eposta.com" inputMode="email" required />
        </Field>
        <Field label="Şifre">
          <input className={inputCls} type="password" value={pass} onChange={(e) => setPass(e.target.value)} placeholder="En az 6 karakter" minLength={6} required />
        </Field>
        {err && <p className="rounded-xl bg-[#fde1df] px-3 py-2.5 text-xs font-bold text-[#8f1826]">{err}</p>}
        <button type="submit" disabled={busy} className="ember-btn flex h-13 w-full items-center justify-center gap-2 rounded-2xl py-4 text-[15px] font-extrabold">
          {busy ? <span className="h-5 w-5 animate-spin rounded-full border-2 border-white/40 border-t-white" /> : <>Devam et <ArrowRight size={18} /></>}
        </button>
      </form>
    </AuthShell>
  );
}

const GOALS = [
  { Icon: Trophy, t: 'Yağ yakımı', d: 'Kas koruyarak incel' },
  { Icon: Dumbbell, t: 'Kas kazanımı', d: 'Hacim + güç odaklı' },
  { Icon: Target, t: 'Form koruma', d: 'Dengeli & sürdürülebilir' },
];

export function OnboardingScreen({ store, done }: { store: Store; done: () => void }) {
  const [step, setStep] = useState(0);
  const [name, setName] = useState('');
  const [gender, setGender] = useState('Erkek');
  const [age, setAge] = useState('27');
  const [heightCm, setHeightCm] = useState('175');
  const [goal, setGoal] = useState(0);
  const [level, setLevel] = useState(1);
  const [weight, setWeight] = useState('78');
  const [targetWeight, setTargetWeight] = useState('72');
  const [days, setDays] = useState(3);
  const [diet, setDiet] = useState(0);
  // ---- Vücut videosu (antrenman programının temel aldığı analiz) ----
  const videoInputRef = useRef<HTMLInputElement>(null);
  const [videoState, setVideoState] = useState<'idle' | 'busy' | 'done' | 'skip'>('idle');
  const [videoName, setVideoName] = useState('');
  const [videoPreview, setVideoPreview] = useState('');
  const [videoAnalysis, setVideoAnalysis] = useState<Record<string, unknown> | null>(null);
  const [videoErr, setVideoErr] = useState('');
  // ---- Vücut analizi (video adımından ÖNCE; tüm alanlar opsiyonel) ----
  // Kullanıcı InBody benzeri cihaz çıktısından okuyabildiği değerleri girer.
  // Girilen ilk ölçüm, plan uygulanırken /api/onboarding/complete ile kalıcı
  // ilk kayda dönüşür ve Kişisel Bilgiler sayfasının başlangıcı olur.
  const [bodyValues, setBodyValues] = useState<Record<string, string>>({});
  const [bodySegmentsOpen, setBodySegmentsOpen] = useState(false);
  const total = 10;

  const handleVideoFile = async (file: File) => {
    if (!file) return;
    if (!file.type.startsWith('video/')) { setVideoErr('Lütfen bir video dosyası seç.'); return; }
    if (file.size > 300 * 1024 * 1024) { setVideoErr('Video çok büyük — 10-15 saniyelik kısa bir kayıt dene.'); return; }
    setVideoErr('');
    if (videoPreview) URL.revokeObjectURL(videoPreview);
    setVideoName(file.name);
    setVideoPreview(URL.createObjectURL(file));
    setVideoState('busy');
    setVideoAnalysis(null);
    const fd = new FormData();
    fd.append('file', file, file.name);
    try {
      const res = await apiFetch('/api/onboarding/video', { method: 'POST', body: fd, timeoutMs: 180_000, retries: 1 });
      setVideoAnalysis(res as Record<string, unknown>);
      setVideoState('done');
    } catch (ex) {
      setVideoErr(ex instanceof Error ? ex.message : 'Video analiz edilemedi. Tekrar dener misin?');
      setVideoState('idle');
    }
  };

  /**
   * Onboarding formundaki ölçüm alanlarını API payload'ına çevirir.
   * Boş bırakılan alanlar payload'a hiç girmez; hiçbir alan doldurulmadıysa
   * null döner ve ilk kayıt oluşturulmaz (adım tamamen opsiyoneldir).
   */
  const collectBodyPayload = (): Record<string, number | string | null> | null => {
    const payload: Record<string, number | string | null> = {};
    Object.entries(bodyValues).forEach(([key, raw]) => {
      const cleaned = raw.trim().replace(',', '.');
      if (cleaned === '') return;
      const parsed = Number(cleaned);
      if (Number.isFinite(parsed)) payload[key] = parsed;
    });
    return Object.keys(payload).length > 0 ? payload : null;
  };

  // Profil oluşturma bitince Program Oluşturucu sayfası açılır;
  // completeOnboarding, plan uygulanınca orada çağrılır.
  const finish = () => {
    store.setProfile({
      ...(name.trim() ? { name: name.trim() } : {}),
      gender,
      age: parseInt(age, 10) || 27,
      heightCm: parseFloat(heightCm.replace(',', '.')) || 175,
      goal: ['Yağ yakımı + kas koruma', 'Kas kazanımı', 'Form koruma'][goal],
      level: ['Başlangıç', 'Orta seviye', 'İleri seviye'][level],
      currentWeight: parseFloat(weight.replace(',', '.')) || 78,
      targetWeight: parseFloat(targetWeight.replace(',', '.')) || 72,
      workoutDays: days,
      diet: ['Dengeli', 'Akdeniz', 'Vejetaryen', 'Vegan', 'Keto'][diet],
    });
    // Vücut videosu analizi varsa plan oluşturucuya taşınır ve orada
    // /api/onboarding/complete ile kalıcı hafızaya yazılır.
    store.applyOnboardingVideo(videoState === 'done' ? videoAnalysis : null);
    // Vücut analizi adımı boş geçilmediyse ilk ölçüm kalıcı kayda dönüşür.
    store.applyOnboardingBodyComposition(collectBodyPayload());
    done();
  };
  const next = () => (step < total - 1 ? setStep(step + 1) : finish());
  return (
    <div className="min-h-dvh bg-[#f4f1ec] text-[#1c1512]">
      <div className="mx-auto flex min-h-dvh w-full max-w-md flex-col px-6 pb-10 pt-[max(2rem,env(safe-area-inset-top))]">
        <Logo />
        <div className="mt-6 flex gap-1.5">
          {Array.from({ length: total }).map((_, i) => (
            <div key={i} className="h-1.5 flex-1 overflow-hidden rounded-full bg-[#e2d7c6]">
              <div className={`h-full rounded-full transition-all duration-500 ${i <= step ? 'bg-[#d92835]' : ''}`} style={{ width: i <= step ? '100%' : '0%' }} />
            </div>
          ))}
        </div>
        <div key={step} className="rise-in flex flex-1 flex-col justify-center py-6">
          {step === 0 && (
            <>
              <p className="eyebrow text-[#d92835]">Adım 1 / 10 · Profil</p>
              <h2 className="font-display mt-2 text-[28px] font-extrabold leading-tight">Seni nasıl<br />anışlayalım?</h2>
              <div className="card-paper mt-6 rounded-3xl p-5">
                <Field label="Adın">
                  <input className={inputCls} value={name} onChange={(e) => setName(e.target.value)} placeholder="Adın (opsiyonel)" />
                </Field>
              </div>
              <div className="mt-4 flex items-center gap-2 rounded-2xl bg-[#1c1512] p-4 text-white">
                <Flame size={18} className="shrink-0 text-[#ff5a63]" />
                <p className="text-xs font-semibold leading-relaxed">Koçun sana özel <b>antrenman programı</b> ve <b>beslenme planı</b> hazırlayacak.</p>
              </div>
            </>
          )}
          {step === 1 && (
            <>
              <p className="eyebrow text-[#d92835]">Adım 2 / 10 · Hakkında</p>
              <h2 className="font-display mt-2 text-[28px] font-extrabold leading-tight">Metabolizmanı<br />tanıyalım.</h2>
              <div className="mt-6 grid grid-cols-2 gap-2">
                {['Kadın', 'Erkek'].map((g) => (
                  <button key={g} onClick={() => setGender(g)} className={`rounded-2xl border-2 py-4 text-[15px] font-extrabold transition ${gender === g ? 'border-[#d92835] bg-white shadow-[0_14px_30px_-18px_rgba(217,40,53,0.5)]' : 'border-[#e7ddcf] bg-white/60'}`}>{g}</button>
                ))}
              </div>
              <div className="card-paper mt-3 flex items-center justify-center gap-3 rounded-3xl p-6">
                <input value={age} onChange={(e) => setAge(e.target.value.replace(/\D/g, '').slice(0, 3))} inputMode="numeric" className="font-display w-20 bg-transparent text-center text-5xl font-extrabold outline-none" />
                <span className="text-lg font-extrabold text-[#9a8c80]">yaş</span>
              </div>
              <div className="mt-4 flex items-center gap-2 rounded-2xl bg-[#1c1512] p-4 text-white">
                <Flame size={18} className="shrink-0 text-[#ff5a63]" />
                <p className="text-xs font-semibold leading-relaxed">BMR hesabında (Mifflin-St Jeor) cinsiyet ve yaş kullanılır.</p>
              </div>
            </>
          )}
          {step === 3 && (
            <>
              <p className="eyebrow text-[#d92835]">Adım 4 / 10 · Hedefin</p>
              <h2 className="font-display mt-2 text-[28px] font-extrabold leading-tight">Neye<br />odaklanalım?</h2>
              <div className="mt-6 space-y-2.5">
                {GOALS.map((g, i) => (
                  <button key={g.t} onClick={() => setGoal(i)} className={`flex w-full items-center gap-3.5 rounded-2xl border-2 p-4 text-left transition ${goal === i ? 'border-[#d92835] bg-white shadow-[0_14px_30px_-18px_rgba(217,40,53,0.5)]' : 'border-[#e7ddcf] bg-white/60'}`}>
                    <span className={`grid h-11 w-11 shrink-0 place-items-center rounded-xl ${goal === i ? 'ember-btn' : 'bg-[#f4f1ec] text-[#9a8c80]'}`}><g.Icon size={20} /></span>
                    <span className="min-w-0 flex-1"><span className="block text-[15px] font-extrabold">{g.t}</span><span className="block text-xs font-medium text-[#9a8c80]">{g.d}</span></span>
                    <span className={`grid h-6 w-6 shrink-0 place-items-center rounded-full border-2 ${goal === i ? 'border-[#d92835] bg-[#d92835] text-white' : 'border-[#ddd0bd] text-transparent'}`}><Check size={14} strokeWidth={3} /></span>
                  </button>
                ))}
              </div>
            </>
          )}
          {step === 4 && (
            <>
              <p className="eyebrow text-[#d92835]">Adım 5 / 10 · Seviyen</p>
              <h2 className="font-display mt-2 text-[28px] font-extrabold leading-tight">Antrenman<br />geçmişin?</h2>
              <div className="mt-6 space-y-2.5">
                {['Başlangıç — 0–6 ay', 'Orta seviye — 6–24 ay', 'İleri seviye — 2+ yıl'].map((l, i) => (
                  <button key={l} onClick={() => setLevel(i)} className={`flex w-full items-center justify-between rounded-2xl border-2 p-4 text-left text-[15px] font-extrabold transition ${level === i ? 'border-[#d92835] bg-white' : 'border-[#e7ddcf] bg-white/60'}`}>
                    {l}
                    <span className={`grid h-6 w-6 place-items-center rounded-full border-2 ${level === i ? 'border-[#d92835] bg-[#d92835] text-white' : 'border-[#ddd0bd] text-transparent'}`}><Check size={14} strokeWidth={3} /></span>
                  </button>
                ))}
              </div>
            </>
          )}
          {step === 2 && (
            <>
              <p className="eyebrow text-[#d92835]">Adım 3 / 10 · Vücut ölçülerin</p>
              <h2 className="font-display mt-2 text-[28px] font-extrabold leading-tight">Boy, kilo ve<br />hedefin?</h2>
              <div className="card-paper mt-6 flex items-center justify-center gap-3 rounded-3xl p-6">
                <input value={heightCm} onChange={(e) => setHeightCm(e.target.value.replace(/[^\d.,]/g, '').slice(0, 3))} inputMode="decimal" className="font-display w-24 bg-transparent text-center text-5xl font-extrabold outline-none" />
                <span className="text-lg font-extrabold text-[#9a8c80]">cm boy</span>
              </div>
              <div className="card-paper mt-3 flex items-center justify-center gap-3 rounded-3xl p-6">
                <input value={weight} onChange={(e) => setWeight(e.target.value)} inputMode="decimal" className="font-display w-28 bg-transparent text-center text-5xl font-extrabold outline-none" />
                <span className="text-lg font-extrabold text-[#9a8c80]">kg</span>
              </div>
              <div className="card-paper mt-3 flex items-center justify-center gap-3 rounded-3xl p-6">
                <input value={targetWeight} onChange={(e) => setTargetWeight(e.target.value)} inputMode="decimal" className="font-display w-28 bg-transparent text-center text-5xl font-extrabold outline-none" />
                <span className="text-lg font-extrabold text-[#9a8c80]">hedef kg</span>
              </div>
              <div className="mt-4 flex items-center gap-2 rounded-2xl bg-[#1c1512] p-4 text-white">
                <UtensilsCrossed size={18} className="shrink-0 text-[#ff5a63]" />
                <p className="text-xs font-semibold leading-relaxed">Hedefine göre günlük <b>2200 kcal · 150g protein</b> planı hazırladım.</p>
              </div>
            </>
          )}
          {step === 5 && (
            <>
              <p className="eyebrow text-[#d92835]">Adım 6 / 10 · Antrenman</p>
              <h2 className="font-display mt-2 text-[28px] font-extrabold leading-tight">Haftada kaç gün<br />antrenman yaparsın?</h2>
              <div className="mt-6 grid grid-cols-5 gap-2">
                {[2, 3, 4, 5, 6].map((d) => (
                  <button key={d} onClick={() => setDays(d)} className={`rounded-2xl border-2 py-4 text-center transition ${days === d ? 'border-[#d92835] bg-white shadow-[0_14px_30px_-18px_rgba(217,40,53,0.5)]' : 'border-[#e7ddcf] bg-white/60'}`}>
                    <span className={`font-display block text-2xl font-extrabold ${days === d ? 'text-[#d92835]' : 'text-[#1c1512]'}`}>{d}</span>
                    <span className="mt-0.5 block text-[10px] font-bold text-[#9a8c80]">gün</span>
                  </button>
                ))}
              </div>
              <div className="mt-4 flex items-center gap-2 rounded-2xl bg-[#1c1512] p-4 text-white">
                <Dumbbell size={18} className="shrink-0 text-[#ff5a63]" />
                <p className="text-xs font-semibold leading-relaxed">Haftada <b>{days} gün</b> — {['', '', 'Full Body · 2 seans', 'Full Body + Üst/Alt', 'Üst / Alt bölme', 'Push / Pull / Legs', 'PPL + zayıf bölge seansı'][days]} kurgusu hazırlanacak.</p>
              </div>
            </>
          )}
          {step === 6 && (
            <>
              <p className="eyebrow text-[#d92835]">Adım 7 / 10 · Vücut analizi</p>
              <h2 className="font-display mt-2 text-[28px] font-extrabold leading-tight">Cihaz çıktın<br />varsa ekleyelim.</h2>
              <p className="mt-3 text-[12px] font-semibold leading-relaxed text-[#6f6259]">
                InBody / tanı cihazı çıktındaki değerleri girersen Jarvis antrenman ve beslenme
                kararlarını gerçek yağ–kas dağılımına göre kurar. <b>Tüm alanlar opsiyonel</b> —
                yalnızca okuyabildiklerini gir.
              </p>

              <div className="card-paper mt-4 rounded-3xl p-5">
                <p className="text-[13px] font-extrabold text-[#1c1512]">Genel</p>
                <p className="mt-0.5 text-[10.5px] font-bold text-[#b3a696]">Cihaz çıktısındaki toplam değerler</p>
                <div className="mt-3 grid grid-cols-2 gap-2.5">
                  {FORM_GROUPS[0].fields.map((f) => (
                    <label key={f.key} className="block">
                      <span className="block text-[10.5px] font-bold text-[#6f6259]">{f.label}</span>
                      <span className="mt-1 flex items-center gap-1 rounded-xl border border-[#e7ddcf] bg-white px-2.5 py-2 focus-within:border-[#d92835]">
                        <input
                          value={bodyValues[f.key] ?? ''}
                          onChange={(e) => setBodyValues((prev) => ({
                            ...prev,
                            [f.key]: e.target.value.replace(/[^\d.,]/g, '').slice(0, 6),
                          }))}
                          inputMode="decimal"
                          placeholder="—"
                          className="min-w-0 flex-1 bg-transparent text-sm font-bold outline-none"
                        />
                        <span className="shrink-0 text-[10px] font-extrabold text-[#b3a696]">{f.unit}</span>
                      </span>
                    </label>
                  ))}
                </div>

                <button
                  type="button"
                  onClick={() => setBodySegmentsOpen((v) => !v)}
                  className="mt-3.5 flex w-full items-center justify-between gap-2 rounded-xl border border-dashed border-[#ddd0bd] bg-[#f8f4ec] px-3.5 py-2.5 text-left text-[11.5px] font-extrabold text-[#6f6259]"
                >
                  Segmentel veriler (bacak / kol / gövde)
                  <ChevronRight size={15} className={`shrink-0 transition-transform ${bodySegmentsOpen ? 'rotate-90' : ''}`} />
                </button>

                {bodySegmentsOpen && (
                  <div className="mt-3.5 space-y-3.5">
                    {FORM_GROUPS.slice(1).map((group) => (
                      <div key={group.key}>
                        <p className="text-[11.5px] font-extrabold text-[#1c1512]">{group.label}</p>
                        <div className="mt-2 grid grid-cols-2 gap-2.5">
                          {group.fields.map((f) => (
                            <label key={f.key} className="block">
                              <span className="block text-[10.5px] font-bold text-[#6f6259]">{f.label}</span>
                              <span className="mt-1 flex items-center gap-1 rounded-xl border border-[#e7ddcf] bg-white px-2.5 py-2 focus-within:border-[#d92835]">
                                <input
                                  value={bodyValues[f.key] ?? ''}
                                  onChange={(e) => setBodyValues((prev) => ({
                                    ...prev,
                                    [f.key]: e.target.value.replace(/[^\d.,]/g, '').slice(0, 6),
                                  }))}
                                  inputMode="decimal"
                                  placeholder="—"
                                  className="min-w-0 flex-1 bg-transparent text-sm font-bold outline-none"
                                />
                                <span className="shrink-0 text-[10px] font-extrabold text-[#b3a696]">{f.unit}</span>
                              </span>
                            </label>
                          ))}
                        </div>
                      </div>
                    ))}
                  </div>
                )}

                <p className="mt-3.5 rounded-xl bg-[#1c1512] p-3 text-[11px] font-semibold leading-relaxed text-white">
                  {Object.values(bodyValues).filter((v) => v.trim() !== '').length} alan dolduruldu ·
                  girilen ilk ölçüm Kişisel Bilgiler sayfanın başlangıcı olur.
                </p>
              </div>

              <button
                type="button"
                onClick={() => { setBodyValues({}); setBodySegmentsOpen(false); }}
                className="mt-3 w-full rounded-2xl py-3 text-xs font-extrabold text-[#9a8c80] transition active:scale-[0.99]"
              >
                Atla — cihaz çıktım yanımda değil / sonra gireceğim
              </button>
            </>
          )}
          {step === 7 && (
            <>
              <p className="eyebrow text-[#d92835]">Adım 8 / 10 · Vücut videosu</p>
              <h2 className="font-display mt-2 text-[28px] font-extrabold leading-tight">Seni tanıyıp<br />programı ona göre<br />kurayım.</h2>
              <div className="card-paper mt-4 rounded-3xl p-5">
                <p className="mt-3 text-[12px] font-semibold leading-relaxed text-[#6f6259]">
                  İyi ışıkta, vücudunu gösterecek kıyafetlerle <b>10-15 saniyelik</b> kısa bir video çek —
                  önden durup yavaşça sağa dön, sonra sola dön. AI koçun fiziğini/formunu değerlendirir ve
                  <b>antrenman programını bu analize göre önceliklendirir</b>.
                </p>
                <div className="mt-3 rounded-2xl border border-dashed border-[#e2d7c6] bg-[#f8f4ec] p-4 text-center text-[11px] font-semibold text-[#9a8c80]">
                  Video yalnızca fizik/form analizi için kullanılır · en fazla 300MB · 10-15 saniye yeterli
                </div>
                {videoPreview && (
                  <video key={videoPreview} src={videoPreview} controls playsInline className="mt-3 aspect-video w-full rounded-2xl bg-black" />
                )}
                <input
                  ref={videoInputRef}
                  type="file"
                  accept="video/*"
                  capture="user"
                  className="hidden"
                  onChange={(e) => { const f = e.target.files?.[0]; if (f) void handleVideoFile(f); e.target.value = ''; }}
                />
                {videoState === 'busy' ? (
                  <p className="mt-3 flex items-center justify-center gap-2 rounded-xl bg-[#1c1512] px-3.5 py-3 text-xs font-extrabold text-white">
                    <span className="h-4 w-4 animate-spin rounded-full border-2 border-white/40 border-t-white" /> Videon analiz ediliyor… (10-20 saniye sürebilir)
                  </p>
                ) : (
                  <button type="button" onClick={() => videoInputRef.current?.click()} className="ember-btn mt-3 flex w-full items-center justify-center gap-2 rounded-2xl py-3.5 text-sm font-extrabold">
                    <Camera size={17} /> {videoName ? 'Videoyu değiştir' : 'Kamerayı aç / video seç'}
                  </button>
                )}
                {videoState === 'done' && videoAnalysis && (
                  <div className="mt-3 rounded-2xl border border-[#cfe3cd] bg-[#e8f6ee] p-3.5">
                    <p className="flex items-center gap-1.5 text-[10px] font-extrabold uppercase tracking-widest text-[#2e9e5b]"><Check size={12} strokeWidth={3} /> Analiz tamamlandı</p>
                    <p className="mt-1 text-[11.5px] font-medium leading-relaxed text-[#1c1512]">
                      {String(videoAnalysis.report ?? '').slice(0, 280)}{String(videoAnalysis.report ?? '').length > 280 ? '…' : ''}
                    </p>
                  </div>
                )}
                {videoErr && <p className="mt-2 rounded-xl bg-[#fde1df] px-3 py-2.5 text-xs font-bold text-[#8f1826]">{videoErr}</p>}
              </div>
              <button
                type="button"
                onClick={() => {
                  if (videoPreview) URL.revokeObjectURL(videoPreview);
                  setVideoState('skip'); setVideoName(''); setVideoPreview(''); setVideoAnalysis(null); setVideoErr('');
                }}
                className="mt-3 w-full rounded-2xl py-3 text-xs font-extrabold text-[#9a8c80] transition active:scale-[0.99]"
              >
                Atla — videomu şimdilik paylaşmak istemiyorum
              </button>
            </>
          )}
          {step === 8 && (
            <>
              <p className="eyebrow text-[#d92835]">Adım 9 / 10 · Beslenme</p>
              <h2 className="font-display mt-2 text-[28px] font-extrabold leading-tight">Beslenme<br />tercihin?</h2>
              <div className="mt-6 space-y-2.5">
                {['Dengeli', 'Akdeniz', 'Vejetaryen', 'Vegan', 'Keto'].map((dName, i) => (
                  <button key={dName} onClick={() => setDiet(i)} className={`flex w-full items-center justify-between rounded-2xl border-2 p-4 text-left text-[15px] font-extrabold transition ${diet === i ? 'border-[#d92835] bg-white' : 'border-[#e7ddcf] bg-white/60'}`}>
                    {dName}
                    <span className={`grid h-6 w-6 place-items-center rounded-full border-2 ${diet === i ? 'border-[#d92835] bg-[#d92835] text-white' : 'border-[#ddd0bd] text-transparent'}`}><Check size={14} strokeWidth={3} /></span>
                  </button>
                ))}
              </div>
              <div className="mt-4 flex items-center gap-2 rounded-2xl bg-[#1c1512] p-4 text-white">
                <UtensilsCrossed size={18} className="shrink-0 text-[#ff5a63]" />
                <p className="text-xs font-semibold leading-relaxed">Makro dağılımı ve öğün şablonları tercihe göre kurgulanır.</p>
              </div>
            </>
          )}
          {step === 9 && (
            <>
              <p className="eyebrow text-[#d92835]">Adım 10 / 10 · Özet</p>
              <h2 className="font-display mt-2 text-[28px] font-extrabold leading-tight">Her şey hazır,<br />planı kuralım.</h2>
              <div className="card-paper mt-6 space-y-2 rounded-3xl p-5">
                {[
                  ['Profil', `${name.trim() || 'Sporcu'} · ${gender}, ${age}`],
                  ['Vücut', `${heightCm} cm · ${weight} → ${targetWeight} kg`],
                  ['Hedef', GOALS[goal].t],
                  ['Seviye', ['Başlangıç', 'Orta seviye', 'İleri seviye'][level]],
                  ['Antrenman', `Haftada ${days} gün · ${splitLabel(days)}`],
                  ['Beslenme', ['Dengeli', 'Akdeniz', 'Vejetaryen', 'Vegan', 'Keto'][diet]],
                  ['Vücut analizi', Object.values(bodyValues).filter((v) => v.trim() !== '').length > 0
                    ? `${Object.values(bodyValues).filter((v) => v.trim() !== '').length} değer girildi (ilk kayıt)`
                    : 'Atlandı / sonra girilecek'],
                  ['Vücut videosu', videoState === 'done' ? `Analiz edildi · ${videoName}` : 'Atlandı / eklenmedi'],
                ].map(([k, v]) => (
                  <div key={k} className="flex items-center justify-between gap-3 rounded-xl bg-[#f8f4ec] px-3.5 py-2.5">
                    <span className="eyebrow text-[#9a8c80]">{k}</span>
                    <span className="truncate text-sm font-extrabold text-[#1c1512]">{v}</span>
                  </div>
                ))}
              </div>
              <div className="mt-4 flex items-center gap-2 rounded-2xl bg-[#1c1512] p-4 text-white">
                <Sparkles size={18} className="shrink-0 text-[#ff5a63]" />
                <p className="text-xs font-semibold leading-relaxed">Devam et — kalori/makro hedeflerin, <b>haftalık antrenman programın</b> ve <b>beslenme planın</b> kişiselleştirilecek.</p>
              </div>
            </>
          )}
        </div>
        <button onClick={next} className="ember-btn flex w-full items-center justify-center gap-2 rounded-2xl py-4 text-[15px] font-extrabold">
          {step === 9 ? <>Program Oluşturucuyu Başlat <Sparkles size={18} /></>
            : step === 7 && videoState === 'done' ? <>Analizle devam et <ChevronRight size={18} /></>
            : <>Devam et <ChevronRight size={18} /></>}
        </button>
      </div>
    </div>
  );
}
