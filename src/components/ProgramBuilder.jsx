import { useEffect, useState } from 'react';
import {
  Dumbbell, Salad, ArrowLeft, ArrowRight, Sparkles, RefreshCw,
  AlertTriangle, Check, Home, Building2, Trees, Clock, Zap,
  HeartPulse, ChefHat, Moon, Gauge, UtensilsCrossed, Pill, ShieldCheck,
} from 'lucide-react';
import { apiFetch } from '../services/apiClient';

/**
 * PROGRAM OLUŞTURUCU (onboarding sonrası).
 *
 * Onboarding sihirbazı profili kaydettikten sonra açılır. Kullanıcıya iki ayrı
 * detaylı anket sunar:
 *   🏋️ ANTRENMAN PROGRAMI OLUŞTURUCU (6 adım)
 *   🥗 BESLENME PROGRAMI OLUŞTURUCU (6 adım)
 *
 * Son adımda kullanıcı açıkça üretimi başlatır
 * (POST /api/program-builder/workout | /api/program-builder/nutrition).
 * Cevaplar ve varsa medya analizleri backend'de AI prompt'una zengin bağlam olarak enjekte edilir ve
 * profilin serbest metin sütunlarına işlenir (kalıcılık).
 *
 * Her iki üretici de atlanabilir; dashboard'daki manuel üretim butonları yedektir.
 */

// ---------------- ANTRENMAN ANKETİ SEÇENEKLERİ ----------------
const ENVIRONMENTS = [
  { id: 'gym', label: 'Spor Salonu', desc: 'Tam ekipmanlı salon', Icon: Building2 },
  { id: 'home', label: 'Ev', desc: 'Evde, kendi ekipmanlarımla', Icon: Home },
  { id: 'outdoor', label: 'Açık Alan', desc: 'Park / açık hava', Icon: Trees },
];

const EQUIPMENT = [
  'Barbell', 'Dumbbell', 'Makineler', 'Kablolar', 'Kettlebell',
  'Direnç bandı', 'Barfiks barı', 'Bench', 'Sadece vücut ağırlığı',
];

const DAYS = ['Pzt', 'Sal', 'Çar', 'Per', 'Cum', 'Cmt', 'Paz'];

const TIMES = [
  { id: 'morning', label: 'Sabah', desc: '06:00 - 10:00' },
  { id: 'noon', label: 'Öğlen', desc: '11:00 - 15:00' },
  { id: 'evening', label: 'Akşam', desc: '16:00 - 20:00' },
  { id: 'night', label: 'Gece', desc: '20:00 sonrası' },
];

const SESSION_MINUTES = [30, 45, 60, 75, 90];

const TRAINING_STYLES = [
  { id: 'hypertrophy', label: 'Hipertrofi', desc: 'Kas büyümesi odaklı, 8-15 tekrar' },
  { id: 'strength', label: 'Güç', desc: 'Büyük kaldırışlar, düşük tekrar (3-6)' },
  { id: 'hybrid', label: 'Hibrit', desc: 'Hem güç hem kas gelişimi' },
  { id: 'general', label: 'Genel Fitness', desc: 'Dengeli, sürdürülebilir kondisyon' },
];

const FOCUS_GROUPS = [
  { id: 'general', label: 'Genel' },
  { id: 'chest', label: 'Göğüs' },
  { id: 'back', label: 'Sırt' },
  { id: 'legs', label: 'Bacak' },
  { id: 'shoulders', label: 'Omuz' },
  { id: 'arms', label: 'Kol' },
  { id: 'core', label: 'Karın' },
];

const CARDIO_PREFS = [
  { id: 'none', label: 'Hiç istemiyorum', desc: 'Sadece ağırlık antrenmanı' },
  { id: 'light', label: 'Az miktarda', desc: 'Haftada 1-2 hafif seans' },
  { id: 'moderate', label: 'Orta', desc: 'Haftada 2-3 seans' },
  { id: 'high', label: 'Yoğun', desc: 'Kondisyonum da önemli' },
];

const INJURY_CHIPS = ['Diz', 'Omuz', 'Bel', 'Boyun', 'Bilek', 'Dirsek', 'Kalça', 'Sağlıklıyım'];

// ---------------- BESLENME ANKETİ SEÇENEKLERİ ----------------
const MEAL_COUNTS = [2, 3, 4, 5, 6];

const FASTING_STYLES = [
  { id: 'none', label: 'Yok', desc: 'Normal öğün düzeni' },
  { id: '16_8', label: '16:8', desc: '16 saat oruç, 8 saat yeme penceresi' },
  { id: '14_10', label: '14:10', desc: 'Hafif oruç penceresi' },
  { id: 'omad', label: 'OMAD', desc: 'Günde tek ana öğün' },
];

const ALLERGIES = [
  'Laktoz/Süt', 'Gluten', 'Fındık', 'Yumurta',
  'Soya', 'Deniz ürünü', 'Susam', 'Çilek',
];

const DIET_STYLES = [
  { id: 'none', label: 'Kısıt yok', desc: 'Her şeyi yerim' },
  { id: 'vegetarian', label: 'Vejetaryen', desc: 'Et yok, süt-yumurta var' },
  { id: 'vegan', label: 'Vegan', desc: 'Hiçbir hayvansal ürün yok' },
  { id: 'halal', label: 'Helal', desc: 'Helal sertifikalı / domuz yok' },
  { id: 'keto', label: 'Keto', desc: 'Düşük karbonhidrat, yüksek yağ' },
  { id: 'gluten_free', label: 'Glutensiz', desc: 'Buğday ürünleri yok' },
];

const COOKING_SKILLS = [
  { id: 'none', label: 'Hiç pişirmem', desc: 'Hazır/pratik çözümler' },
  { id: 'basic', label: 'Basit', desc: 'Temel tarifler yapabilirim' },
  { id: 'good', label: 'İyiyim', desc: 'Çoğu tarifi yaparım' },
  { id: 'loves', label: 'Severim', desc: 'Mutfakta mutluyum' },
];

const MEAL_PREPS = [
  { id: 'weekly', label: 'Haftalık hazırlarım', desc: 'Pazar günü toplu pişiririm' },
  { id: 'sometimes', label: 'Bazen', desc: 'Müsait olduğumda hazırlarım' },
  { id: 'none', label: 'Hiç', desc: 'Her öğünü o gün çözerim' },
];

const BUDGETS = [
  { id: 'low', label: 'Düşük', desc: 'Ekonomik besinler ağırlıklı' },
  { id: 'medium', label: 'Orta', desc: 'Dengeli bütçe' },
  { id: 'high', label: 'Yüksek', desc: 'Kalite öncelikli' },
];

const EATING_OUTS = [
  { id: 'rarely', label: 'Nadiren', desc: 'Ayda 1-2 kez' },
  { id: 'weekly', label: 'Haftada 1-2', desc: 'Düzenli dışarıda yerim' },
  { id: 'often', label: 'Sık sık', desc: 'Haftada 3+ kez' },
];

const SUPPLEMENTS = [
  'Whey', 'Kreatin', 'Multivitamin', 'Omega-3',
  'D Vitamini', 'Magnezyum', 'Pre-workout', 'Kullanmıyorum',
];

const JOB_ACTIVITIES = [
  { id: 'desk', label: 'Masabaşı', desc: 'Günümü oturarak geçiriyorum' },
  { id: 'light', label: 'Hafif hareketli', desc: 'Ara ara ayağa kalkarım' },
  { id: 'physical', label: 'Fiziksel', desc: 'Gün boyu ayaktayım/üretimdeyim' },
];

const PACES = [
  { id: 'aggressive', label: 'Agresif', desc: 'Hızlı sonuç, sıkı düzen' },
  { id: 'balanced', label: 'Dengeli', desc: 'Sürdürülebilir orta tempo' },
  { id: 'slow', label: 'Yavaş', desc: 'Esnek, konforlu ilerleme' },
];

const CHEAT_MEALS = [
  { id: 'none', label: 'Hiç istemiyorum' },
  { id: 'weekly', label: 'Haftada 1' },
  { id: 'biweekly', label: '2 haftada 1' },
  { id: 'flexible', label: 'Esnek olsun', desc: 'Özel günlerde serbest' },
];

// Üretim sırasında gösterilen canlı durum mesajları (~2 dk bekleme artık "donmuş" görünmez)
const WORKOUT_STATUS_MSGS = [
  'Profilin ve anket cevapların analiz ediliyor...',
  'Deneyim seviyene göre hacim hedefleri hesaplanıyor...',
  'Periodizasyon modeli kuruluyor...',
  'Kas grubu başına set dağılımı optimize ediliyor...',
  'Sakatlık geçmişine göre güvenli hareketler seçiliyor...',
  'Program yazılıyor — neredeyse hazır...',
];

const NUTRITION_STATUS_MSGS = [
  'Kalori ve makro hedeflerin hesaplanıyor...',
  'Alerji ve kısıtların plana uygulanıyor...',
  'Mutfak alışkanlıklarına uygun öğünler seçiliyor...',
  'Öğün saatlerin plana yerleştiriliyor...',
  'Porsiyonlar ve makrolar dengele oluyor...',
  'Plan yazılıyor — neredeyse hazır...',
];

// ---------------- ANA BİLEŞEN ----------------
export default function ProgramBuilder({ onFinish, mediaContext: initialMediaContext = null }) {
  const [mode, setMode] = useState('menu'); // menu | workout | nutrition
  const [wStep, setWStep] = useState(0);    // 0..5 antrenman adımı
  const [nStep, setNStep] = useState(0);    // 0..5 beslenme adımı
  const [wq, setWq] = useState({});         // antrenman anketi cevapları
  const [nq, setNq] = useState({});         // beslenme anketi cevapları
  const [generating, setGenerating] = useState(null); // 'workout' | 'nutrition'
  const [genMsgIdx, setGenMsgIdx] = useState(0);
  const [genError, setGenError] = useState('');
  const [errKind, setErrKind] = useState(null); // hatayı hangi üretici verdi → tekrar dene hedefi
  const [wDone, setWDone] = useState(false);
  const [nDone, setNDone] = useState(false);
  const [mediaContext, setMediaContext] = useState(initialMediaContext);

  useEffect(() => {
    let cancelled = false;
    // Ebeveyn boş bir context göndermiş olsa bile önceki oturumdaki kalıcı
    // analizleri kaçırmamak için yalnızca gerçekten veri varsa fetch'i atla.
    if (initialMediaContext?.videoReport || initialMediaContext?.voiceResult) return undefined;
    apiFetch('/api/onboarding/context', { timeoutMs: 20_000, retries: 1 })
      .then((ctx) => { if (!cancelled) setMediaContext(ctx); })
      .catch((err) => console.warn('[ProgramBuilder] medya bağlamı alınamadı:', err));
    return () => { cancelled = true; };
  }, [initialMediaContext]);

  const videoAnalysis = mediaContext?.videoReport || mediaContext?.video_analysis || null;
  const voiceAnalysis = mediaContext?.voiceResult || mediaContext?.voice_analysis || null;
  const videoInstruction = videoAnalysis?.training_instruction || videoAnalysis?.report || '';
  const voiceInstruction = voiceAnalysis?.summary || voiceAnalysis?.transcript || '';
  const hasVideoAnalysis = Boolean(videoAnalysis);
  const hasVoiceAnalysis = Boolean(voiceAnalysis);

  const updW = (k, v) => setWq((f) => ({ ...f, [k]: v }));
  const updN = (k, v) => setNq((f) => ({ ...f, [k]: v }));

  // Üretim sırasında canlı durum mesajı döngüsü
  useEffect(() => {
    if (!generating) return;
    const t = setInterval(() => setGenMsgIdx((i) => i + 1), 7000);
    return () => clearInterval(t);
  }, [generating]);

  // Anket cevaplarıyla üretimi tetikler (backend AI'ya bağlamı enjekte eder)
  const runGeneration = async (kind) => {
    setGenerating(kind);
    setErrKind(kind);
    setGenError('');
    setGenMsgIdx(0);
    const payload = { ...(kind === 'workout' ? wq : nq) };
    // Analiz bağlamı DB'de de mevcut; ayrıca bu isteğe açıkça ekleyerek
    // questionnaire prompt'unda kesin görünmesini sağla.
    if (kind === 'workout' && videoInstruction && !payload.notes) {
      payload.notes = `VIDEO ANALİZİNE GÖRE ÖNCELİKLER: ${videoInstruction}`;
    }
    if (kind === 'nutrition' && voiceInstruction && !payload.notes) {
      payload.notes = `SES KAYDINDAN ANLAŞILAN TERCİHLER/RUTİN: ${voiceInstruction}`;
    }
    try {
      await apiFetch(`/api/program-builder/${kind}`, {
        method: 'POST',
        body: JSON.stringify(payload),
        timeoutMs: 180_000,
        retries: 1,
      });
      if (kind === 'workout') setWDone(true);
      else setNDone(true);
      setMode('menu');
    } catch (e) {
      console.error(`[ProgramBuilder:${kind}]`, e);
      setGenError(e?.message || 'Program üretilirken bir hata oluştu, tekrar dener misin?');
      setMode('menu');
    } finally {
      setGenerating(null);
    }
  };

  const toggleListItem = (kind, key, item) => {
    const upd = kind === 'workout' ? updW : updN;
    const cur = (kind === 'workout' ? wq : nq)[key] || [];
    upd(key, cur.includes(item) ? cur.filter((x) => x !== item) : [...cur, item]);
  };

  const genMsgs = generating === 'workout' ? WORKOUT_STATUS_MSGS : NUTRITION_STATUS_MSGS;
  const genMsg = genMsgs[Math.min(genMsgIdx, genMsgs.length - 1)];

  // ---------------- EKRAN: ÜRETİM SÜRÜYOR ----------------
  if (generating) {
    return (
      <div className="lumiere-app-shell safe-page text-white flex items-center justify-center p-4">
        <div
          className="absolute inset-0 pointer-events-none"
          style={{ background: 'radial-gradient(ellipse 60% 40% at 50% 0%, rgba(239,51,64,0.08), transparent 70%)' }}
        />
        <div className="relative w-full max-w-md text-center space-y-6 animate-fadeIn">
          <div className="w-16 h-16 mx-auto rounded-3xl bg-gradient-to-br from-red-400/20 to-red-900/30 border border-red-400/30 flex items-center justify-center shadow-xl shadow-red-950/20">
            <RefreshCw className="w-8 h-8 text-red-300 animate-spin" />
          </div>
          <p className="lp-section-kicker">Lumiere planını işliyor</p>
          <h1 className="text-2xl font-black tracking-[-0.055em]">
            {generating === 'workout' ? 'Antrenman programın hazırlanıyor.' : 'Beslenme planın hazırlanıyor.'}
          </h1>
          <p className="text-sm text-neutral-400 font-mono min-h-[20px]">{genMsg}</p>
          <div className="h-1.5 bg-neutral-800 rounded-full overflow-hidden">
            <div className="h-full w-1/3 bg-red-500 rounded-full animate-[loading_2.5s_ease-in-out_infinite]" />
          </div>
          <p className="text-[11px] text-neutral-600 leading-relaxed">
            AI senin cevaplarına göre sıfırdan tasarlıyor — bu işlem 1-2 dakika sürebilir.
            Sayfayı kapatma, bittiğinde burada olacaksın.
          </p>
        </div>
      </div>
    );
  }

    // ---------------- EKRAN: ÜRETİCİ SEÇİM MENÜSÜ ----------------
  if (mode === 'menu') {
    const cards = [
      {
        kind: 'workout', Icon: Dumbbell, title: 'Antrenman Programı Oluşturucu',
        desc: hasVideoAnalysis
          ? 'Video analizindeki kas/form öncelikleriyle birlikte ekipman, güvenlik ve zamanın sorulacak — program buna göre yazılacak.'
          : 'Ekipmanın, programın, sakatlıkların ve hedeflerin sorulacak — sonra programın sıfırdan yazılacak.',
        done: wDone, accent: 'red',
      },
      {
        kind: 'nutrition', Icon: Salad, title: 'Beslenme Programı Oluşturucu',
        desc: hasVoiceAnalysis
          ? 'Ses kaydındaki beslenme/rutin tercihleri temel alınarak alerji, bütçe ve öğün ayrıntıların sorulacak.'
          : 'Alerjilerin, bütçen, mutfak alışkanlıkların ve damak zevkin sorulacak — sonra günlük planın kurulacak.',
        done: nDone, accent: 'emerald',
      },
    ];

    return (
      <div className="lumiere-app-shell safe-page text-white flex items-center justify-center p-4 sm:p-6">
        <div
          className="absolute inset-0 pointer-events-none"
          style={{ background: 'radial-gradient(ellipse 60% 40% at 50% 0%, rgba(239,51,64,0.07), transparent 70%)' }}
        />
        <div className="relative w-full max-w-xl space-y-5 animate-fadeIn">
          <div className="text-center space-y-2">
            <div className="w-14 h-14 mx-auto rounded-3xl bg-gradient-to-br from-red-400/20 to-red-900/30 border border-red-400/30 flex items-center justify-center shadow-xl shadow-red-950/20">
              <Sparkles className="w-7 h-7 text-red-300" />
            </div>
            <p className="lp-section-kicker">Kişisel plan stüdyosu</p>
            <h1 className="text-3xl font-black tracking-[-0.06em]">Planlarını <span className="text-red-400">oluşturalım.</span></h1>
            <p className="text-sm text-neutral-400 leading-relaxed max-w-md mx-auto">
              Profilin hazır. Şimdi iki ayrı detaylı anketle programlarını tamamen
              sana özel kuracağım — <span className="text-white font-bold">rastgele şablon yok</span>.
            </p>
            {(hasVideoAnalysis || hasVoiceAnalysis) && (
              <div className="mx-auto max-w-md text-left bg-red-500/5 border border-red-500/20 rounded-xl px-3 py-2.5 text-[11px] text-neutral-300">
                <p className="font-mono text-red-400 mb-1">AKTİF AI BAĞLAMI</p>
                <p>{hasVideoAnalysis ? '✓ Video fizik/form analizi antrenmana aktarılacak.' : '○ Video analizi yok; antrenman soruları genel profil üzerinden.'}</p>
                <p>{hasVoiceAnalysis ? '✓ Ses kaydı tercihleri beslenme planına aktarılacak.' : '○ Ses kaydı yok; beslenme soruları genel profil üzerinden.'}</p>
              </div>
            )}
          </div>

          {genError && (
            <div className="bg-red-500/10 border border-red-500/30 text-red-400 text-xs px-4 py-3 rounded-xl font-mono space-y-2.5">
              <div className="flex items-start gap-2">
                <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" />
                <span>{genError}</span>
              </div>
              <button
                onClick={() => { setGenError(''); setMode(errKind || 'workout'); }}
                className="w-full bg-red-500/20 hover:bg-red-500/30 text-red-200 font-bold font-mono text-xs py-2.5 rounded-lg transition-colors cursor-pointer flex items-center justify-center gap-2"
              >
                <RefreshCw className="w-3.5 h-3.5" /> TEKRAR DENE
              </button>
            </div>
          )}

          <div className="grid sm:grid-cols-2 gap-4">
            {cards.map(({ kind, Icon, title, desc, done, accent }) => (
              <button
                key={kind}
                onClick={() => setMode(kind)}
                disabled={done}
                className={`text-left p-5 rounded-2xl border transition-all cursor-pointer ${
                  done
                    ? 'bg-emerald-500/5 border-emerald-500/30 opacity-80 cursor-default'
                    : 'bg-[#1a1a23]/80 border-white/[0.1] hover:border-red-400/40 hover:bg-[#22222d] shadow-xl shadow-black/10'
                }`}
              >
                <div className="flex items-center justify-between mb-3">
                  <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${
                    accent === 'red' ? 'bg-red-500/10 border border-red-500/20' : 'bg-emerald-500/10 border border-emerald-500/20'
                  }`}>
                    <Icon className={`w-5 h-5 ${accent === 'red' ? 'text-red-400' : 'text-emerald-400'}`} />
                  </div>
                  {done ? (
                    <span className="flex items-center gap-1 text-[10px] font-mono uppercase tracking-widest text-emerald-400 bg-emerald-500/10 border border-emerald-500/30 px-2 py-1 rounded-full">
                      <Check className="w-3 h-3" /> Üretildi
                    </span>
                  ) : (
                    <span
                      className="text-[10px] font-mono uppercase tracking-widest px-2 py-1 rounded-full border"
                      style={(kind === 'workout' ? hasVideoAnalysis : hasVoiceAnalysis)
                        ? { color: kind === 'workout' ? 'var(--lp-green)' : 'var(--lp-yellow)', borderColor: 'currentColor', background: 'rgba(255,255,255,.03)' }
                        : { color: '#85858f', borderColor: 'rgba(255,255,255,.14)', background: 'rgba(255,255,255,.03)' }}
                    >
                      {kind === 'workout'
                        ? (hasVideoAnalysis ? 'Video bağlamı' : 'Genel profil')
                        : (hasVoiceAnalysis ? 'Ses bağlamı' : 'Genel profil')}
                    </span>
                  )}
                </div>
                <p className="text-sm font-black font-mono tracking-wide">{title}</p>
                <p className="text-[11px] text-neutral-500 leading-relaxed mt-1.5">{desc}</p>
                {!done && (
                  <p className={`text-[10px] font-mono mt-3 flex items-center gap-1 ${
                    accent === 'red' ? 'text-red-400' : 'text-emerald-400'
                  }`}>
                    BAŞLA <ArrowRight className="w-3 h-3" />
                  </p>
                )}
              </button>
            ))}
          </div>

          <div className="space-y-2 pt-1">
            <button
              onClick={onFinish}
              className="lp-primary w-full font-bold text-sm tracking-wide py-3.5 rounded-xl transition-all flex items-center justify-center gap-2 cursor-pointer"
            >
              PANEL'E GİT <ArrowRight className="w-4 h-4" />
            </button>
            <p className="text-center text-[10px] text-neutral-600 leading-relaxed">
              İkisini birden tamamlamak zorunda değilsin — atladıklarını paneldeki üretim butonlarından her zaman yeniden oluşturabilirsin.
            </p>
          </div>
        </div>
      </div>
    );
  }

    // ---------------- EKRAN: ANTRENMAN ANKETİ ----------------
  if (mode === 'workout') {
    return (
      <div className="lumiere-app-shell text-white flex items-center justify-center p-4 sm:p-6">
        <div
          className="absolute inset-0 pointer-events-none"
          style={{ background: 'radial-gradient(ellipse 60% 40% at 50% 0%, rgba(239,51,64,0.07), transparent 70%)' }}
        />
        <div className="relative w-full max-w-xl">
          <div className="mb-5">
            <div className="flex items-center justify-between mb-2">
              <button
                onClick={() => (wStep === 0 ? setMode('menu') : setWStep(wStep - 1))}
                className="text-xs text-neutral-500 hover:text-white transition-colors cursor-pointer flex items-center gap-1"
              >
                <ArrowLeft className="w-3.5 h-3.5" /> Geri
              </button>
              <span className="text-[10px] font-mono uppercase tracking-widest text-neutral-500">
                Antrenman Anketi · {wStep + 1}/6
              </span>
            </div>
            <div className="lp-stepper">
              {Array.from({ length: 6 }).map((_, i) => (
                <b key={i} className={i <= wStep ? 'on' : ''} />
              ))}
            </div>
          </div>

          <div className="lp-panel rounded-[28px] p-6 sm:p-8 shadow-2xl shadow-black/60 animate-fadeIn space-y-5">
            {/* W0: ORTAM + EKİPMAN */}
            {wStep === 0 && (
              <>
                <StepHeader Icon={Building2} title="NEREDE ANTRENMAN YAPACAKSIN?" desc="Hareket seçimi tamamen buna göre yapılacak." />
                <div className="grid grid-cols-3 gap-3">
                  {ENVIRONMENTS.map(({ id, label, desc, Icon }) => (
                    <OptionCard key={id} selected={wq.environment === id} onClick={() => updW('environment', id)}>
                      <Icon className="w-5 h-5 text-red-400 mb-2" />
                      <p className="text-xs font-bold">{label}</p>
                      <p className="text-[10px] text-neutral-500 mt-0.5 leading-snug">{desc}</p>
                    </OptionCard>
                  ))}
                </div>
                <FieldShell label="Hangi ekipmanlara erişimin var? (birden fazla seçebilirsin)">
                  <ChipGroup
                    items={EQUIPMENT}
                    selected={wq.equipment || []}
                    onToggle={(item) => toggleListItem('workout', 'equipment', item)}
                  />
                </FieldShell>
                <StepNav onNext={() => setWStep(1)} nextLabel="DEVAM ET" />
              </>
            )}

            {/* W1: ZAMAN PROGRAMI */}
            {wStep === 1 && (
              <>
                <StepHeader Icon={Clock} title="HAFTALIK PROGRAMIN NE?" desc="Program, gerçek zamanına göre kurulacak." />
                <FieldShell label="Haftada kaç gün antrenman yapabilirsin?">
                  <div className="grid grid-cols-5 gap-2">
                    {[2, 3, 4, 5, 6].map((d) => (
                      <OptionCard key={d} selected={wq.days_per_week === d} onClick={() => updW('days_per_week', d)} compact>
                        <p className="text-base font-black font-mono">{d}</p>
                        <p className="text-[9px] text-neutral-500">gün</p>
                      </OptionCard>
                    ))}
                  </div>
                </FieldShell>
                <FieldShell label="Gün başına ne kadar süren var?">
                  <ChipGroup
                    items={SESSION_MINUTES.map((m) => `${m} dk`)}
                    selected={(wq.session_minutes ? [`${wq.session_minutes} dk`] : [])}
                    onToggle={(item) => updW('session_minutes', parseInt(item, 10))}
                  />
                </FieldShell>
                <FieldShell label="Hangi günler? (opsiyonel)">
                  <ChipGroup
                    items={DAYS}
                    selected={wq.preferred_days || []}
                    onToggle={(item) => toggleListItem('workout', 'preferred_days', item)}
                  />
                </FieldShell>
                <FieldShell label="Günün hangi saatinde?">
                  <div className="grid grid-cols-4 gap-2">
                    {TIMES.map(({ id, label, desc }) => (
                      <OptionCard key={id} selected={wq.preferred_time === id} onClick={() => updW('preferred_time', id)} compact>
                        <p className="text-xs font-bold">{label}</p>
                        <p className="text-[9px] text-neutral-500 mt-0.5">{desc}</p>
                      </OptionCard>
                    ))}
                  </div>
                </FieldShell>
                <StepNav onBack={() => setWStep(0)} onNext={() => setWStep(2)} nextLabel="DEVAM ET" />
              </>
            )}

            {/* W2: SAKATLIK & KISITLAR */}
            {wStep === 2 && (
              <>
                <StepHeader Icon={ShieldCheck} title="SAKATLIK VE KISITLAR" desc={hasVideoAnalysis ? 'Video analizindeki form/güvenlik notlarını da doğrula; program buna göre güvenli kurulacak.' : 'Bu bölüm çok önemli — programın güvenli olması için.'} />
                {hasVideoAnalysis && videoInstruction && (
                  <div className="bg-red-500/5 border border-red-500/20 rounded-xl px-3.5 py-3 text-xs text-red-200 leading-relaxed">
                    <span className="font-bold text-red-400">Video analizinden gelen öncelik:</span> {videoInstruction}
                  </div>
                )}
                <FieldShell label="Ağrıyan veya sakat bölgelerin var mı? (seç veya yaz)">
                  <ChipGroup
                    items={INJURY_CHIPS}
                    selected={wq._injuryChips || []}
                    onToggle={(item) => {
                      const chips = wq._injuryChips || [];
                      const next = chips.includes(item) ? chips.filter((x) => x !== item) : [...chips, item];
                      updW('_injuryChips', next);
                      updW('injuries', next.filter((x) => x !== 'Sağlıklıyım').join(', ') || null);
                    }}
                  />
                  <input
                    type="text"
                    value={wq.injuries || ''}
                    onChange={(e) => updW('injuries', e.target.value || null)}
                    placeholder="Örn: sağ dizde menisküs hassasiyeti"
                    className="w-full mt-2 bg-neutral-950 border border-neutral-800 rounded-xl px-3.5 py-3 text-sm text-white placeholder-neutral-600 focus:outline-none focus:border-red-500 focus:ring-1 focus:ring-red-500 transition-colors"
                  />
                </FieldShell>
                <FieldShell label="Kaçınmanı istediğin hareketler var mı? (opsiyonel)">
                  <input
                    type="text"
                    value={wq.avoid_exercises || ''}
                    onChange={(e) => updW('avoid_exercises', e.target.value || null)}
                    placeholder="Örn: arkadan çekişli lat pulldown, derin squat"
                    className="w-full bg-neutral-950 border border-neutral-800 rounded-xl px-3.5 py-3 text-sm text-white placeholder-neutral-600 focus:outline-none focus:border-red-500 focus:ring-1 focus:ring-red-500 transition-colors"
                  />
                </FieldShell>
                <StepNav onBack={() => setWStep(1)} onNext={() => setWStep(3)} nextLabel="DEVAM ET" />
              </>
            )}

            {/* W3: STİL + ODAK */}
            {wStep === 3 && (
              <>
                <StepHeader Icon={Zap} title="NASIL BİR PROGRAM İSTİYORSUN?" desc="Stil ve odak, set/tekrar dağılımını belirler." />
                <FieldShell label="Antrenman stili">
                  <div className="grid grid-cols-2 gap-2.5">
                    {TRAINING_STYLES.map(({ id, label, desc }) => (
                      <OptionCard key={id} selected={wq.training_style === id} onClick={() => updW('training_style', id)} compact>
                        <p className="text-xs font-bold">{label}</p>
                        <p className="text-[10px] text-neutral-500 mt-0.5 leading-snug">{desc}</p>
                      </OptionCard>
                    ))}
                  </div>
                </FieldShell>
                <FieldShell label="Öncelik vermek istediğin kas grubu?">
                  <ChipGroup
                    items={FOCUS_GROUPS.map((f) => f.label)}
                    selected={(wq.focus_muscle_group ? [FOCUS_GROUPS.find((f) => f.id === wq.focus_muscle_group)?.label].filter(Boolean) : [])}
                    onToggle={(item) => {
                      const found = FOCUS_GROUPS.find((f) => f.label === item);
                      updW('focus_muscle_group', found ? found.id : null);
                    }}
                  />
                </FieldShell>
                <StepNav onBack={() => setWStep(2)} onNext={() => setWStep(4)} nextLabel="DEVAM ET" />
              </>
            )}

            {/* W4: HAREKET TERCİHLERİ */}
            {wStep === 4 && (
              <>
                <StepHeader Icon={HeartPulse} title="HAREKET TERCİHLERİN" desc="Sevdiğin hareketleri programda önceliklendireceğim." />
                <FieldShell label="Sevdiğin / mutlaka görmek istediğin hareketler (opsiyonel)">
                  <input
                    type="text"
                    value={wq.liked_exercises || ''}
                    onChange={(e) => updW('liked_exercises', e.target.value || null)}
                    placeholder="Örn: incline bench, ağırlıklı şınav, hip thrust"
                    className="w-full bg-neutral-950 border border-neutral-800 rounded-xl px-3.5 py-3 text-sm text-white placeholder-neutral-600 focus:outline-none focus:border-red-500 focus:ring-1 focus:ring-red-500 transition-colors"
                  />
                </FieldShell>
                <FieldShell label="Hiç istemediğin hareketler (opsiyonel)">
                  <input
                    type="text"
                    value={wq.disliked_exercises || ''}
                    onChange={(e) => updW('disliked_exercises', e.target.value || null)}
                    placeholder="Örn: burpee, behind-the-neck press"
                    className="w-full bg-neutral-950 border border-neutral-800 rounded-xl px-3.5 py-3 text-sm text-white placeholder-neutral-600 focus:outline-none focus:border-red-500 focus:ring-1 focus:ring-red-500 transition-colors"
                  />
                </FieldShell>
                <StepNav onBack={() => setWStep(3)} onNext={() => setWStep(5)} nextLabel="SON ADIM" />
              </>
            )}

            {/* W5: KARDİYO + NOT → SEÇİM YAPILINCA ÜRETİM OTOMATİK BAŞLAR */}
            {wStep === 5 && (
              <>
                <StepHeader Icon={Gauge} title="SON SORU!" desc="Kardiyo tercihini seç, hazır olduğunda aşağıdaki düğmeyle programı oluştur." />
                <div className="grid grid-cols-2 gap-2.5">
                  {CARDIO_PREFS.map(({ id, label, desc }) => (
                    <OptionCard
                      key={id}
                      selected={wq.cardio_preference === id}
                      onClick={() => {
                        updW('cardio_preference', id);
                      }}
                      compact
                    >
                      <p className="text-xs font-bold">{label}</p>
                      <p className="text-[10px] text-neutral-500 mt-0.5 leading-snug">{desc}</p>
                    </OptionCard>
                  ))}
                </div>
                <FieldShell label="Eklemek istediğin bir şey var mı? (opsiyonel)">
                  <textarea
                    value={wq.notes || ''}
                    onChange={(e) => updW('notes', e.target.value || null)}
                    rows={2}
                    placeholder="Örn: haftada 1 basketbol oynuyorum, sabahları enerjik oluyorum..."
                    className="w-full bg-neutral-950 border border-neutral-800 rounded-xl px-3.5 py-3 text-sm text-white placeholder-neutral-600 focus:outline-none focus:border-red-500 focus:ring-1 focus:ring-red-500 transition-colors resize-none"
                  />
                </FieldShell>
                <p className="text-[10px] text-neutral-600 font-mono text-center">
                  Seçimini değiştirebilir, hazır olduğunda program üretimini başlatabilirsin.
                </p>
                <button
                  type="button"
                  onClick={() => runGeneration('workout')}
                  disabled={!wq.cardio_preference || !!generating}
                  className="w-full bg-red-500 hover:bg-red-400 text-white font-bold font-mono text-sm py-3 rounded-xl transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
                >
                  PROGRAMI OLUŞTUR
                </button>
              </>
            )}
          </div>
        </div>
      </div>
    );
  }

    // ---------------- EKRAN: BESLENME ANKETİ ----------------
  if (mode === 'nutrition') {
    return (
      <div className="lumiere-app-shell text-white flex items-center justify-center p-4 sm:p-6">
        <div
          className="absolute inset-0 pointer-events-none"
          style={{ background: 'radial-gradient(ellipse 60% 40% at 50% 0%, rgba(16,185,129,0.06), transparent 70%)' }}
        />
        <div className="relative w-full max-w-xl">
          <div className="mb-5">
            <div className="flex items-center justify-between mb-2">
              <button
                onClick={() => (nStep === 0 ? setMode('menu') : setNStep(nStep - 1))}
                className="text-xs text-neutral-500 hover:text-white transition-colors cursor-pointer flex items-center gap-1"
              >
                <ArrowLeft className="w-3.5 h-3.5" /> Geri
              </button>
              <span className="text-[10px] font-mono uppercase tracking-widest text-neutral-500">
                Beslenme Anketi · {nStep + 1}/6
              </span>
            </div>
            <div className="lp-stepper">
              {Array.from({ length: 6 }).map((_, i) => (
                <b key={i} className={i <= nStep ? 'on' : ''} />
              ))}
            </div>
          </div>

          <div className="lp-panel rounded-[28px] p-6 sm:p-8 shadow-2xl shadow-black/60 animate-fadeIn space-y-5">
            {/* N0: ÖĞÜN YAPISI */}
            {nStep === 0 && (
              <>
                <StepHeader Icon={UtensilsCrossed} title="ÖĞÜN DÜZENİN NASIL?" desc={hasVoiceAnalysis ? 'Ses kaydında anlattığın rutin ve tercihler burada doğrulanacak.' : 'Plan, senin gerçek rutine göre kurulacak.'} />
                {hasVoiceAnalysis && voiceInstruction && (
                  <div className="bg-emerald-500/5 border border-emerald-500/20 rounded-xl px-3.5 py-3 text-xs text-emerald-200 leading-relaxed">
                    <span className="font-bold text-emerald-400">Ses kaydından gelen bağlam:</span> {voiceInstruction}
                  </div>
                )}
                <FieldShell label="Günde kaç öğün yemek istersin?">
                  <div className="grid grid-cols-5 gap-2">
                    {MEAL_COUNTS.map((m) => (
                      <OptionCard key={m} selected={nq.meals_per_day === m} onClick={() => updN('meals_per_day', m)} compact>
                        <p className="text-base font-black font-mono">{m}</p>
                        <p className="text-[9px] text-neutral-500">öğün</p>
                      </OptionCard>
                    ))}
                  </div>
                </FieldShell>
                <FieldShell label="Aralıklı oruç yapar mısın?">
                  <div className="grid grid-cols-4 gap-2">
                    {FASTING_STYLES.map(({ id, label, desc }) => (
                      <OptionCard key={id} selected={nq.fasting_style === id} onClick={() => updN('fasting_style', id)} compact>
                        <p className="text-xs font-bold">{label}</p>
                        <p className="text-[9px] text-neutral-500 mt-0.5 leading-snug">{desc}</p>
                      </OptionCard>
                    ))}
                  </div>
                </FieldShell>
                <FieldShell label="Öğün saatleri hakkında notun (opsiyonel)">
                  <input
                    type="text"
                    value={nq.meal_times || ''}
                    onChange={(e) => updN('meal_times', e.target.value || null)}
                    placeholder="Örn: kahvaltı 09:00, akşam yemeği 20:00'den önce"
                    className="w-full bg-neutral-950 border border-neutral-800 rounded-xl px-3.5 py-3 text-sm text-white placeholder-neutral-600 focus:outline-none focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500 transition-colors"
                  />
                </FieldShell>
                <StepNav onNext={() => setNStep(1)} nextLabel="DEVAM ET" />
              </>
            )}

            {/* N1: ALERJİ + DİYET STİLİ */}
            {nStep === 1 && (
              <>
                <StepHeader Icon={ShieldCheck} title="ALERJİ VE KISITLAR" desc="Bunlar KESİN kural — plana asla dahil edilmeyecek." />
                <FieldShell label="Alerjilerin / intoleransların neler? (birden fazla seçebilirsin)">
                  <ChipGroup
                    items={ALLERGIES}
                    selected={nq.allergies || []}
                    onToggle={(item) => toggleListItem('nutrition', 'allergies', item)}
                    accent="emerald"
                  />
                </FieldShell>
                <FieldShell label="Diyet stilin">
                  <div className="grid grid-cols-3 gap-2">
                    {DIET_STYLES.map(({ id, label, desc }) => (
                      <OptionCard key={id} selected={nq.diet_style === id} onClick={() => updN('diet_style', id)} compact accent="emerald">
                        <p className="text-xs font-bold">{label}</p>
                        <p className="text-[9px] text-neutral-500 mt-0.5 leading-snug">{desc}</p>
                      </OptionCard>
                    ))}
                  </div>
                </FieldShell>
                <StepNav onBack={() => setNStep(0)} onNext={() => setNStep(2)} nextLabel="DEVAM ET" />
              </>
            )}

            {/* N2: MUTFAK GERÇEĞİ */}
            {nStep === 2 && (
              <>
                <StepHeader Icon={ChefHat} title="MUTFAK GERÇEĞİN" desc="Plan, gerçek hayata uygun olmalı — idealist değil." />
                <FieldShell label="Yemek pişirme becerin">
                  <div className="grid grid-cols-4 gap-2">
                    {COOKING_SKILLS.map(({ id, label, desc }) => (
                      <OptionCard key={id} selected={nq.cooking_skill === id} onClick={() => updN('cooking_skill', id)} compact accent="emerald">
                        <p className="text-xs font-bold">{label}</p>
                        <p className="text-[9px] text-neutral-500 mt-0.5 leading-snug">{desc}</p>
                      </OptionCard>
                    ))}
                  </div>
                </FieldShell>
                <FieldShell label="Meal-prep (toplu yemek hazırlığı) yapar mısın?">
                  <div className="grid grid-cols-3 gap-2">
                    {MEAL_PREPS.map(({ id, label, desc }) => (
                      <OptionCard key={id} selected={nq.meal_prep === id} onClick={() => updN('meal_prep', id)} compact accent="emerald">
                        <p className="text-xs font-bold">{label}</p>
                        <p className="text-[9px] text-neutral-500 mt-0.5 leading-snug">{desc}</p>
                      </OptionCard>
                    ))}
                  </div>
                </FieldShell>
                <FieldShell label="Gıda bütçen">
                  <div className="grid grid-cols-3 gap-2">
                    {BUDGETS.map(({ id, label, desc }) => (
                      <OptionCard key={id} selected={nq.budget === id} onClick={() => updN('budget', id)} compact accent="emerald">
                        <p className="text-xs font-bold">{label}</p>
                        <p className="text-[9px] text-neutral-500 mt-0.5">{desc}</p>
                      </OptionCard>
                    ))}
                  </div>
                </FieldShell>
                <FieldShell label="Dışarıda ne sıklıkla yersin?">
                  <div className="grid grid-cols-3 gap-2">
                    {EATING_OUTS.map(({ id, label, desc }) => (
                      <OptionCard key={id} selected={nq.eating_out === id} onClick={() => updN('eating_out', id)} compact accent="emerald">
                        <p className="text-xs font-bold">{label}</p>
                        <p className="text-[9px] text-neutral-500 mt-0.5">{desc}</p>
                      </OptionCard>
                    ))}
                  </div>
                </FieldShell>
                <StepNav onBack={() => setNStep(1)} onNext={() => setNStep(3)} nextLabel="DEVAM ET" />
              </>
            )}

            {/* N3: DAMAK TADI */}
            {nStep === 3 && (
              <>
                <StepHeader Icon={Salad} title="DAMAK TADIN" desc="Planı severse uygularsın — bu yüzden önemli." />
                <FieldShell label="Sevdiğin besinler / yemekler / mutfaklar (opsiyonel)">
                  <input
                    type="text"
                    value={nq.liked_foods || ''}
                    onChange={(e) => updN('liked_foods', e.target.value || null)}
                    placeholder="Örn: tavuk göğsü, mercimek çorbası, Türk mutfağı, yoğurt"
                    className="w-full bg-neutral-950 border border-neutral-800 rounded-xl px-3.5 py-3 text-sm text-white placeholder-neutral-600 focus:outline-none focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500 transition-colors"
                  />
                </FieldShell>
                <FieldShell label="Hiç yemediğin / sevmediğin besinler (opsiyonel)">
                  <input
                    type="text"
                    value={nq.disliked_foods || ''}
                    onChange={(e) => updN('disliked_foods', e.target.value || null)}
                    placeholder="Örn: ton balığı, karnabahar, protein bar"
                    className="w-full bg-neutral-950 border border-neutral-800 rounded-xl px-3.5 py-3 text-sm text-white placeholder-neutral-600 focus:outline-none focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500 transition-colors"
                  />
                </FieldShell>
                <StepNav onBack={() => setNStep(2)} onNext={() => setNStep(4)} nextLabel="DEVAM ET" />
              </>
            )}

            {/* N4: YAŞAM TARZI + HEDEF HIZI */}
            {nStep === 4 && (
              <>
                <StepHeader Icon={Moon} title="YAŞAM TARZIN" desc="Kalori hedefi, günlük gerçeklerine göre ayarlanacak." />
                <FieldShell label="Ortalama kaç saat uyuyorsun?">
                  <ChipGroup
                    items={['5 saatten az', '5-6 saat', '7-8 saat', '9+ saat']}
                    selected={(nq.sleep_hours ? [{ '5 saatten az': 4.5, '5-6 saat': 5.5, '7-8 saat': 7.5, '9+ saat': 9 }[nq.sleepLabel]] : []).filter(Boolean)}
                    onToggle={(item) => {
                      const val = { '5 saatten az': 4.5, '5-6 saat': 5.5, '7-8 saat': 7.5, '9+ saat': 9 }[item];
                      updN('sleep_hours', val);
                      updN('sleepLabel', item);
                    }}
                    accent="emerald"
                  />
                </FieldShell>
                <FieldShell label="İşin / okulun ne kadar hareketli?">
                  <div className="grid grid-cols-3 gap-2">
                    {JOB_ACTIVITIES.map(({ id, label, desc }) => (
                      <OptionCard key={id} selected={nq.job_activity === id} onClick={() => updN('job_activity', id)} compact accent="emerald">
                        <p className="text-xs font-bold">{label}</p>
                        <p className="text-[9px] text-neutral-500 mt-0.5 leading-snug">{desc}</p>
                      </OptionCard>
                    ))}
                  </div>
                </FieldShell>
                <FieldShell label="Hedefine ne hızda ilerlemek istersin?">
                  <div className="grid grid-cols-3 gap-2">
                    {PACES.map(({ id, label, desc }) => (
                      <OptionCard key={id} selected={nq.pace === id} onClick={() => updN('pace', id)} compact accent="emerald">
                        <p className="text-xs font-bold">{label}</p>
                        <p className="text-[9px] text-neutral-500 mt-0.5 leading-snug">{desc}</p>
                      </OptionCard>
                    ))}
                  </div>
                </FieldShell>
                <StepNav onBack={() => setNStep(3)} onNext={() => setNStep(5)} nextLabel="SON ADIM" />
              </>
            )}

            {/* N5: SUPPLEMENT + CHEAT MEAL → SEÇİM YAPILINCA ÜRETİM OTOMATİK BAŞLAR */}
            {nStep === 5 && (
              <>
                <StepHeader Icon={Pill} title="SON SORU!" desc="Tercihini seç, hazır olduğunda aşağıdaki düğmeyle beslenme planını oluştur." />
                <FieldShell label="Kullandığın supplementler (birden fazla seçebilirsin)">
                  <ChipGroup
                    items={SUPPLEMENTS}
                    selected={nq.supplements || []}
                    onToggle={(item) => toggleListItem('nutrition', 'supplements', item)}
                    accent="emerald"
                  />
                </FieldShell>
                <FieldShell label="Cheat meal (serbest öğün) istersin mi?">
                  <div className="grid grid-cols-4 gap-2">
                    {CHEAT_MEALS.map(({ id, label, desc }) => (
                      <OptionCard
                        key={id}
                        selected={nq.cheat_meal === id}
                        onClick={() => {
                          updN('cheat_meal', id);
                        }}
                        compact
                        accent="emerald"
                      >
                        <p className="text-xs font-bold">{label}</p>
                        {desc && <p className="text-[9px] text-neutral-500 mt-0.5 leading-snug">{desc}</p>}
                      </OptionCard>
                    ))}
                  </div>
                </FieldShell>
                <FieldShell label="Eklemek istediğin bir şey var mı? (opsiyonel)">
                  <textarea
                    value={nq.notes || ''}
                    onChange={(e) => updN('notes', e.target.value || null)}
                    rows={2}
                    placeholder="Örn: günde 2 kahve içiyorum, akşamları tatlı krizi olur..."
                    className="w-full bg-neutral-950 border border-neutral-800 rounded-xl px-3.5 py-3 text-sm text-white placeholder-neutral-600 focus:outline-none focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500 transition-colors resize-none"
                  />
                </FieldShell>
                <button
                  type="button"
                  onClick={() => runGeneration('nutrition')}
                  disabled={!nq.cheat_meal || !!generating}
                  className="w-full bg-emerald-500 hover:bg-emerald-400 text-black font-bold font-mono text-sm py-3 rounded-xl transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
                >
                  BESLENME PLANINI OLUŞTUR
                </button>
                <p className="text-[10px] text-neutral-600 font-mono text-center">
                  ⚡ Cevapladığın an üretim başlar — bilgilerin eksiksiz kaydedilecek.
                </p>
              </>
            )}
          </div>
        </div>
      </div>
    );
  }

}

/* ---------------- Yardımcı alt bileşenler ---------------- */

function StepHeader({ Icon, title, desc }) {
  return (
    <div className="flex items-start gap-3">
      <div className="w-10 h-10 shrink-0 rounded-xl bg-red-500/10 border border-red-500/20 flex items-center justify-center">
        <Icon className="w-5 h-5 text-red-400" />
      </div>
      <div>
        <h2 className="text-base font-black font-mono tracking-wide">{title}</h2>
        <p className="text-xs text-neutral-500 leading-relaxed mt-0.5">{desc}</p>
      </div>
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

function OptionCard({ selected, onClick, children, compact, accent }) {
  const border = accent === 'emerald' ? 'emerald' : 'red';
  return (
    <button
      type="button"
      onClick={onClick}
      className={`text-left rounded-xl border transition-all cursor-pointer ${
        compact ? 'p-3' : 'p-3.5'
      } ${
        selected
          ? border === 'emerald'
            ? 'bg-emerald-500/10 border-emerald-500/50 ring-1 ring-emerald-500/40'
            : 'bg-red-500/10 border-red-500/50 ring-1 ring-red-500/40'
          : 'bg-neutral-950 border-neutral-800 hover:border-neutral-600'
      }`}
    >
      {children}
    </button>
  );
}

function ChipGroup({ items, selected, onToggle, accent }) {
  const active = accent === 'emerald'
    ? 'bg-emerald-500/15 border-emerald-500/50 text-emerald-300'
    : 'bg-red-500/15 border-red-500/50 text-red-300';
  return (
    <div className="flex flex-wrap gap-2">
      {items.map((item) => {
        const isSel = selected.includes(item);
        return (
          <button
            key={item}
            type="button"
            onClick={() => onToggle(item)}
            className={`px-3 py-1.5 rounded-full border text-xs font-medium transition-all cursor-pointer ${
              isSel ? active : 'bg-neutral-950 border-neutral-800 text-neutral-400 hover:border-neutral-600'
            }`}
          >
            {item}
          </button>
        );
      })}
    </div>
  );
}

function StepNav({ onBack, onNext, nextLabel }) {
  return (
    <div className="flex items-center justify-between pt-2">
      {onBack ? (
        <button onClick={onBack} className="text-xs text-neutral-500 hover:text-white transition-colors cursor-pointer flex items-center gap-1">
          <ArrowLeft className="w-3.5 h-3.5" /> Geri
        </button>
      ) : (
        <span />
      )}
      <button
        onClick={onNext}
        className="bg-red-500 hover:bg-red-400 text-white font-bold font-mono text-xs tracking-wide px-6 py-2.5 rounded-xl transition-all flex items-center gap-1.5 cursor-pointer"
      >
        {nextLabel} <ArrowRight className="w-3.5 h-3.5" />
      </button>
    </div>
  );
}
