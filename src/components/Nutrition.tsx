import { useState } from 'react';
import { Camera, Check, Flame, ImagePlus, Plus, ScanLine, Sparkles, Trash2, UtensilsCrossed, X } from 'lucide-react';
import { DayNavigator, Empty, HBar, SectionHead } from './chrome';
import type { Store } from '../lib/store';
import { isToday, todayISO } from '../lib/utils';

const QUICK_MEALS = [
  { name: 'Protein Bowl', calories: 540, protein: 45, carbs: 42, fats: 16 },
  { name: 'Tavuk + Pilav', calories: 620, protein: 50, carbs: 60, fats: 12 },
  { name: 'Yulaf Kasesi', calories: 420, protein: 20, carbs: 66, fats: 10 },
  { name: 'Protein Shake', calories: 220, protein: 30, carbs: 18, fats: 4 },
];

export function NutritionScreen({ store }: { store: Store }) {
  const iso = store.selectedDate;
  const meals = store.mealsFor(iso);
  const editable = isToday(iso);
  const t = store.profile.targets;
  const cal = meals.reduce((s, m) => s + m.calories, 0);
  const prot = meals.reduce((s, m) => s + m.protein, 0);
  const carbs = meals.reduce((s, m) => s + m.carbs, 0);
  const fats = meals.reduce((s, m) => s + m.fats, 0);
  const [open, setOpen] = useState(false);
  const [photo, setPhoto] = useState<null | { name: string; calories: number; protein: number; carbs: number; fats: number }>(null);
  const [analyzing, setAnalyzing] = useState(false);
  const [form, setForm] = useState({ name: '', calories: '', protein: '', carbs: '', fats: '' });

  const analyzePhoto = () => {
    setAnalyzing(true);
    setTimeout(() => {
      setAnalyzing(false);
      setPhoto({ name: 'Izgara Tavuk Tabağı (tahmini)', calories: 560, protein: 48, carbs: 38, fats: 14 });
    }, 1600);
  };

  const addForm = (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.name.trim()) return;
    store.addMeal(todayISO(), {
      name: form.name.trim(),
      calories: parseInt(form.calories, 10) || 0,
      protein: parseInt(form.protein, 10) || 0,
      carbs: parseInt(form.carbs, 10) || 0,
      fats: parseInt(form.fats, 10) || 0,
    });
    setForm({ name: '', calories: '', protein: '', carbs: '', fats: '' });
    setOpen(false);
  };

  const macros: Array<{ k: string; v: number; tgt: number; tone: 'red' | 'green' | 'amber' | 'ink'; unit: string }> = [
    { k: 'Kalori', v: cal, tgt: t.calories, tone: 'red', unit: 'kcal' },
    { k: 'Protein', v: prot, tgt: t.protein, tone: 'green', unit: 'g' },
    { k: 'Karb', v: carbs, tgt: t.carbs, tone: 'amber', unit: 'g' },
    { k: 'Yağ', v: fats, tgt: t.fats, tone: 'ink', unit: 'g' },
  ];

  return (
    <div>
      <div className="rise-in">
        <p className="eyebrow text-[#d92835]">Beslenme</p>
        <h1 className="font-display mt-1.5 text-[30px] font-extrabold leading-tight">Yakıt planı<span className="text-[#d92835]">.</span></h1>
      </div>
      <div className="rise-in stagger-1 mt-4">
        <DayNavigator iso={iso} onChange={store.setSelectedDate} onShift={store.shiftSelectedDate} note={isToday(iso) ? 'Bugünün öğünleri — ekleme açık' : 'Yalnızca seçili günün öğünleri · ekleme kapalı'} />
      </div>
      {/* macro summary */}
      <section className="rise-in stagger-2 card-paper mt-3 rounded-3xl p-5">
        <SectionHead kicker="Seçili günün makroları" title={`${Math.round(cal).toLocaleString('tr-TR')} / ${t.calories} kcal`} />
        <div className="space-y-3">
          {macros.map((m) => (
            <div key={m.k}>
              <div className="mb-1 flex items-center justify-between text-xs font-extrabold">
                <span className="text-[#1c1512]">{m.k}</span>
                <span className="text-[#9a8c80]">{Math.round(m.v)} / {m.tgt} {m.unit} · %{Math.min(999, Math.round((m.v / Math.max(1, m.tgt)) * 100))}</span>
              </div>
              <HBar pct={(m.v / Math.max(1, m.tgt)) * 100} tone={m.tone} />
            </div>
          ))}
        </div>
      </section>
      {/* photo analysis */}
      {editable && (
        <section className="rise-in stagger-3 mt-3 overflow-hidden rounded-3xl bg-[#1c1512] p-5 text-white">
          <div className="flex items-center gap-3">
            <span className="ember-btn grid h-12 w-12 shrink-0 place-items-center rounded-2xl"><Camera size={22} /></span>
            <div className="min-w-0 flex-1">
              <p className="text-[15px] font-extrabold">Fotoğrafla öğün analizi</p>
              <p className="text-xs font-medium text-white/60">Tabağı çek, makroları otomatik çıkarayım.</p>
            </div>
          </div>
          {!photo && !analyzing && (
            <button onClick={analyzePhoto} className="mt-4 flex w-full items-center justify-center gap-2 rounded-2xl bg-white py-3.5 text-sm font-extrabold text-[#1c1512] transition active:scale-[0.98]">
              <ImagePlus size={17} /> Fotoğraf yükle (demo)
            </button>
          )}
          {analyzing && (
            <div className="mt-4 rounded-2xl bg-white/8 p-4">
              <div className="flex items-center gap-2 text-sm font-bold"><ScanLine size={17} className="animate-pulse text-[#ff8a7a]" /> Analiz ediliyor…</div>
              <div className="shimmer-line mt-3 h-2 rounded-full" />
            </div>
          )}
          {photo && (
            <div className="mt-4 rounded-2xl bg-white/8 p-4">
              <p className="flex items-center gap-1.5 text-sm font-extrabold"><Sparkles size={15} className="text-[#ff8a7a]" /> {photo.name}</p>
              <p className="mt-1 text-xs font-semibold text-white/60">{photo.calories} kcal · P {photo.protein}g · K {photo.carbs}g · Y {photo.fats}g</p>
              <div className="mt-3 flex gap-2">
                <button
                  onClick={() => { store.addMeal(todayISO(), { name: photo.name, calories: photo.calories, protein: photo.protein, carbs: photo.carbs, fats: photo.fats }); setPhoto(null); }}
                  className="ember-btn flex flex-1 items-center justify-center gap-1.5 rounded-xl py-3 text-sm font-extrabold"
                >
                  <Check size={16} /> Kaydet
                </button>
                <button onClick={() => setPhoto(null)} className="grid w-12 place-items-center rounded-xl bg-white/12 transition active:scale-95" aria-label="Vazgeç"><X size={17} /></button>
              </div>
            </div>
          )}
        </section>
      )}
      {/* quick add */}
      {editable && (
        <section className="card-paper rise-in stagger-3 mt-3 rounded-3xl p-5">
          <SectionHead kicker="Hızlı ekle" />
          <div className="grid grid-cols-2 gap-2">
            {QUICK_MEALS.map((q) => (
              <button
                key={q.name}
                onClick={() => store.addMeal(todayISO(), { name: q.name, calories: q.calories, protein: q.protein, carbs: q.carbs, fats: q.fats })}
                className="rounded-2xl border border-[#ece2d2] bg-white p-3 text-left transition active:scale-[0.97]"
              >
                <p className="truncate text-[13px] font-extrabold text-[#1c1512]">{q.name}</p>
                <p className="mt-0.5 text-[11px] font-semibold text-[#9a8c80]">{q.calories} kcal · P{q.protein}</p>
              </button>
            ))}
          </div>
          <button onClick={() => setOpen((o) => !o)} className="mt-2.5 flex w-full items-center justify-center gap-1.5 rounded-2xl border-2 border-dashed border-[#ddd0bd] py-3 text-sm font-extrabold text-[#6f6259] transition active:scale-[0.99]">
            <Plus size={17} /> Özel öğün yaz
          </button>
          {open && (
            <form onSubmit={addForm} className="rise-in mt-3 space-y-2 rounded-2xl bg-[#f8f4ec] p-3">
              <input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="Öğün adı (örn. Mercimek çorbası)" className="h-12 w-full rounded-xl border border-[#e2d7c6] bg-white px-3 text-sm font-bold outline-none focus:border-[#d92835]" />
              <div className="grid grid-cols-4 gap-2">
                {[['calories', 'kcal'], ['protein', 'prot'], ['carbs', 'karb'], ['fats', 'yağ']].map(([k, ph]) => (
                  <input
                    key={k} value={(form as Record<string, string>)[k]}
                    onChange={(e) => setForm({ ...form, [k]: e.target.value })}
                    inputMode="numeric" placeholder={ph}
                    className="h-12 w-full rounded-xl border border-[#e2d7c6] bg-white px-2 text-center text-sm font-bold outline-none focus:border-[#d92835]"
                  />
                ))}
              </div>
              <button type="submit" className="ember-btn w-full rounded-xl py-3 text-sm font-extrabold">Öğünü kaydet</button>
            </form>
          )}
        </section>
      )}
      {/* meal list (selected day only) */}
      <section className="card-paper rise-in stagger-4 mt-3 rounded-3xl p-5">
        <SectionHead kicker="Öğün kayıtları · seçili gün" right={<span className="rounded-full bg-[#f1ece2] px-2.5 py-1 text-[11px] font-extrabold text-[#6f6259]">{meals.length} kayıt</span>} />
        {meals.length === 0 ? <Empty text={editable ? 'Bugün henüz öğün yok — yukarıdan ekle.' : 'Bu güne ait öğün kaydı yok.'} /> : (
          <div className="space-y-2">
            {meals.map((m) => (
              <div key={m.id} className="flex items-center gap-3 rounded-2xl border border-[#ece2d2] bg-white px-3.5 py-3">
                <span className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-[#fde1df] text-[#d92835]"><UtensilsCrossed size={16} /></span>
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-extrabold text-[#1c1512]">{m.name}</p>
                  <p className="truncate text-[11px] font-semibold text-[#9a8c80]">{m.time} · P {Math.round(m.protein)} · K {Math.round(m.carbs)} · Y {Math.round(m.fats)}</p>
                </div>
                <span className="font-display shrink-0 text-[15px] font-extrabold text-[#1c1512]">{Math.round(m.calories)}</span>
                {editable && (
                  <button onClick={() => store.removeMeal(iso, m.id)} aria-label="Öğünü sil" className="grid h-9 w-9 shrink-0 place-items-center rounded-xl bg-[#f8f4ec] text-[#b3a696] transition active:scale-90"><Trash2 size={15} /></button>
                )}
              </div>
            ))}
          </div>
        )}
      </section>
      {/* plan */}
      <section className="card-paper mt-3 rounded-3xl p-5">
        <SectionHead kicker="Günün planı" title="Önerilen akış" right={<span className="flex items-center gap-1 rounded-full bg-[#e8f6ee] px-2.5 py-1 text-[10px] font-extrabold text-[#2e9e5b]"><Flame size={11} /> 2200 kcal</span>} />
        <div className="space-y-2">
          {[
            ['08:30', 'Kahvaltı', 'Yulaf + muz + fıstık ezmesi', '520 kcal'],
            ['13:00', 'Öğle', 'Izgara tavuk + bulgur + salata', '640 kcal'],
            ['16:30', 'Ara öğün', 'Yoğurt + granola + bal', '380 kcal'],
            ['19:30', 'Akşam', 'Somon + kinoa + brokoli', '590 kcal'],
          ].map(([time, tag, name, kcal]) => (
            <div key={time} className="flex items-center gap-3 rounded-2xl bg-[#f8f4ec] px-3.5 py-3">
              <span className="w-11 shrink-0 text-xs font-extrabold text-[#9a8c80]">{time}</span>
              <div className="min-w-0 flex-1">
                <p className="text-[10px] font-extrabold uppercase tracking-widest text-[#d92835]">{tag}</p>
                <p className="truncate text-sm font-extrabold text-[#1c1512]">{name}</p>
              </div>
              <span className="shrink-0 text-xs font-extrabold text-[#6f6259]">{kcal}</span>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
