// Lumiere Kişisel Bilgiler — InBody benzeri vücut kompozisyonu sayfası.
//
// Veri sözleşmesi: sayfa hiçbir hesap yapmaz, yalnızca sunucunun ürettiği
// özeti gösterir. Değişim etiketleri (+%2,3 / -1,4 kg) ve rozet RENGİ
// /api/body-composition yanıtındaki metrics[].delta_label / direction / tone
// alanlarından gelir; tone daima Jarvis'in yorumundan (review.sentiment) türetilir.
// Bu yüzden kas kaybı gibi bir düşüş, değer azalsa bile kırmızı görünür.
import { useEffect, useMemo, useState } from 'react';
import {
  Activity, AlertTriangle, ArrowDownRight, ArrowUpRight, Check, Minus, Plus, Sparkles, TrendingUp, X,
} from 'lucide-react';
import { PageHeader, SectionHead } from './chrome';
import type { BodyCompositionMetric, BodyCompositionSegment } from '../lib/types';
import type { Store } from '../lib/store';
import { formatDayShort } from '../lib/utils';

/** Ölçüm formundaki alan tanımı — sunucudaki metrik anahtarlarıyla birebir.
 *  Onboarding "Vücut Analizi" adımı da aynı sözlüğü kullanır (tek doğruluk kaynağı). */
export const FORM_GROUPS: Array<{
  key: string; label: string; hint: string;
  fields: Array<{ key: string; label: string; unit: string }>;
}> = [
  {
    key: 'general',
    label: 'Genel',
    hint: 'Cihaz çıktısındaki toplam değerler',
    fields: [
      { key: 'body_fat_percent', label: 'Yağ oranı', unit: '%' },
      { key: 'total_fat_kg', label: 'Toplam yağ', unit: 'kg' },
      { key: 'lean_mass_kg', label: 'Yağ dışı', unit: 'kg' },
      { key: 'muscle_kg', label: 'Kas', unit: 'kg' },
      { key: 'bone_mass_kg', label: 'Kemik', unit: 'kg' },
      { key: 'body_water_kg', label: 'Sıvı', unit: 'kg' },
    ],
  },
  {
    key: 'segment_fat_percent',
    label: 'Segmentel yağ oranı',
    hint: 'Bacak / kol / gövde yağ yüzdesi',
    fields: [
      { key: 'right_leg_fat_percent', label: 'Sağ bacak', unit: '%' },
      { key: 'left_leg_fat_percent', label: 'Sol bacak', unit: '%' },
      { key: 'right_arm_fat_percent', label: 'Sağ kol', unit: '%' },
      { key: 'left_arm_fat_percent', label: 'Sol kol', unit: '%' },
      { key: 'trunk_fat_percent', label: 'Gövde', unit: '%' },
    ],
  },
  {
    key: 'segment_muscle_kg',
    label: 'Segmentel kas',
    hint: 'Bölgesel kas kütlesi',
    fields: [
      { key: 'right_leg_muscle_kg', label: 'Sağ bacak', unit: 'kg' },
      { key: 'left_leg_muscle_kg', label: 'Sol bacak', unit: 'kg' },
      { key: 'right_arm_muscle_kg', label: 'Sağ kol', unit: 'kg' },
      { key: 'left_arm_muscle_kg', label: 'Sol kol', unit: 'kg' },
      { key: 'trunk_muscle_kg', label: 'Gövde', unit: 'kg' },
    ],
  },
  {
    key: 'segment_fat_kg',
    label: 'Segmentel yağ',
    hint: 'Bölgesel yağ kütlesi',
    fields: [
      { key: 'right_leg_fat_kg', label: 'Sağ bacak', unit: 'kg' },
      { key: 'left_leg_fat_kg', label: 'Sol bacak', unit: 'kg' },
      { key: 'right_arm_fat_kg', label: 'Sağ kol', unit: 'kg' },
      { key: 'left_arm_fat_kg', label: 'Sol kol', unit: 'kg' },
      { key: 'trunk_fat_kg', label: 'Gövde', unit: 'kg' },
    ],
  },
];

const TONE_CLASS: Record<string, string> = {
  positive: 'bg-[#e8f6ee] text-[#2e9e5b] border-[#cfe3cd]',
  negative: 'bg-[#fde1df] text-[#8f1826] border-[#f3c4c0]',
  neutral: 'bg-[#f4f1ec] text-[#9a8c80] border-[#e7ddcf]',
};

function fmt(value: number | null | undefined, decimals = 1): string {
  if (value == null) return '—';
  return value.toLocaleString('tr-TR', { minimumFractionDigits: decimals, maximumFractionDigits: decimals });
}

/** Değişim rozeti: ok yönü değişimden (arttı/azaldı), renk Jarvis'in yorumundan gelir. */
function DeltaBadge({ metric }: { metric: BodyCompositionMetric }) {
  if (metric.delta_label == null) {
    return <span className="rounded-full border border-[#e7ddcf] bg-[#f4f1ec] px-2 py-0.5 text-[10px] font-extrabold text-[#b3a696]">ilk ölçüm</span>;
  }
  const Icon = metric.direction === 'up' ? ArrowUpRight : metric.direction === 'down' ? ArrowDownRight : Minus;
  return (
    <span className={`inline-flex items-center gap-0.5 rounded-full border px-2 py-0.5 text-[10px] font-extrabold ${TONE_CLASS[metric.tone] ?? TONE_CLASS.neutral}`}>
      <Icon size={11} strokeWidth={3} />
      {metric.delta_label}
    </span>
  );
}

/** Güncel değer kartı — sayfanın modern "hero" bloğu (değer + değişim rozeti). */
function MetricCard({ metric, hero = false }: { metric: BodyCompositionMetric; hero?: boolean }) {
  return (
    <div className={`card-paper rounded-2xl border p-3.5 ${hero ? 'border-[#1c1512]/10' : 'border-transparent'}`}>
      <p className="eyebrow text-[#9a8c80]">{metric.label}</p>
      <div className="mt-1.5 flex items-end justify-between gap-2">
        <p className={`font-display font-extrabold leading-none ${hero ? 'text-[26px]' : 'text-[19px]'}`}>
          {fmt(metric.current, metric.decimals)}
          <span className="ml-0.5 text-[11px] font-bold text-[#9a8c80]">{metric.unit}</span>
        </p>
        {metric.previous != null && (
          <span className="text-[10px] font-bold text-[#b3a696]">önce {fmt(metric.previous, metric.decimals)}</span>
        )}
      </div>
      <div className="mt-2"><DeltaBadge metric={metric} /></div>
    </div>
  );
}

/** Segment kartı: yağ oranı / kas / yağ üçlüsü tek kartta. */
function SegmentCard({ segment }: { segment: BodyCompositionSegment }) {
  const rows = [
    { field: 'fat_percent' as const, label: 'Yağ oranı', unit: '%' },
    { field: 'muscle_kg' as const, label: 'Kas', unit: 'kg' },
    { field: 'fat_kg' as const, label: 'Yağ', unit: 'kg' },
  ];
  return (
    <div className="card-paper rounded-2xl p-3.5">
      <p className="text-[13px] font-extrabold text-[#1c1512]">{segment.label}</p>
      <div className="mt-2.5 space-y-1.5">
        {rows.map((r) => (
          <div key={r.field} className="flex items-center justify-between gap-2">
            <span className="text-[10.5px] font-bold text-[#9a8c80]">{r.label}</span>
            <span className="text-[13px] font-extrabold text-[#1c1512]">
              {fmt(segment[r.field])}<span className="ml-0.5 text-[10px] font-bold text-[#9a8c80]">{r.unit}</span>
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

/** Haftalık karşılaştırma tablosu: satır = metrik, kolon = ölçüm tarihi. */
function WeeklyTable({ store }: { store: Store }) {
  const history = store.bodyComposition?.history ?? [];
  const rows = useMemo(
    () => FORM_GROUPS.flatMap((g) => g.fields.map((f) => ({ ...f, group: g.label }))),
    [],
  );
  // Tablo sonsuz genişlemesin: en yeni 6 ölçüm (eskiden yeniye) gösterilir.
  const window = history.slice(-6);
  if (window.length === 0) return null;
  const cell = 'whitespace-nowrap px-2.5 py-2 text-[11px] font-bold';

  return (
    <div className="card-paper overflow-hidden rounded-2xl">
      <div className="no-scrollbar overflow-x-auto">
        <table className="w-full border-collapse">
          <thead>
            <tr className="bg-[#1c1512] text-white">
              <th className={`${cell} text-left text-[10px] uppercase tracking-wider`}>Ölçüm</th>
              {window.map((h) => (
                <th key={h.id} className={`${cell} text-right text-[10px] uppercase tracking-wider`}>
                  {formatDayShort(h.date)}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row, i) => {
              const values = window.map((h) => (h[row.key] == null ? null : Number(h[row.key])));
              // Hiç girilmemiş metrik tabloyu boş satırla kirletmesin.
              if (values.every((v) => v == null || Number.isNaN(v))) return null;
              return (
                <tr key={row.key} className={i % 2 ? 'bg-[#f8f4ec]/60' : ''}>
                  <td className={`${cell} text-left`}>
                    <span className="block text-[11.5px] font-extrabold text-[#1c1512]">{row.label}</span>
                    <span className="block text-[9.5px] font-bold text-[#b3a696]">{row.group}</span>
                  </td>
                  {values.map((v, idx) => (
                    <td key={idx} className={`${cell} text-right text-[#1c1512]`}>
                      {v == null || Number.isNaN(v) ? <span className="text-[#d5cabd]">—</span> : fmt(v)}
                    </td>
                  ))}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

/**
 * Yeni ölçüm giriş formu — TÜM alanlar opsiyonel.
 *
 * Boş bırakılan alanlar isteğe hiç eklenmez; sunucu da yalnızca gönderilenleri
 * yazar. Aynı güne ikinci giriş yapılırsa o günün kaydı güncellenir (upsert),
 * böylece kullanıcı sadece yağ oranını düzeltip segmentleri koruyabilir.
 */
function EntrySheet({ store, onClose }: { store: Store; onClose: () => void }) {
  const [values, setValues] = useState<Record<string, string>>({});
  const [date, setDate] = useState<string>('');
  const [note, setNote] = useState('');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  const filled = Object.values(values).filter((v) => v.trim() !== '').length;

  const submit = async () => {
    const payload: Record<string, number | string | null> = {};
    Object.entries(values).forEach(([key, raw]) => {
      const cleaned = raw.trim().replace(',', '.');
      if (cleaned === '') return;
      const parsed = Number(cleaned);
      if (Number.isFinite(parsed)) payload[key] = parsed;
    });
    if (Object.keys(payload).length === 0) {
      setError('En az bir ölçüm değeri girmelisin.');
      return;
    }
    if (date) payload.date = date;
    if (note.trim()) payload.note = note.trim();
    setSaving(true);
    setError('');
    try {
      await store.addBodyComposition(payload);
      onClose();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Ölçüm kaydedilemedi.');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center bg-[#1c1512]/45 backdrop-blur-sm">
      <div className="rise-in max-h-[92dvh] w-full max-w-md overflow-y-auto rounded-t-[28px] border-t border-[#e7ddcf] bg-[#f4f1ec] pb-[max(1.5rem,env(safe-area-inset-bottom))]">
        <div className="sticky top-0 z-10 flex items-center justify-between gap-3 border-b border-[#e7ddcf] bg-[#f4f1ec]/95 px-5 py-4 backdrop-blur-xl">
          <div>
            <p className="eyebrow text-[#d92835]">Yeni ölçüm</p>
            <p className="font-display text-[18px] font-extrabold">Cihaz çıktını gir</p>
          </div>
          <button onClick={onClose} aria-label="Kapat" className="grid h-9 w-9 place-items-center rounded-full border border-[#e2d7c6] bg-white/80 text-[#6f6259] active:scale-95">
            <X size={17} />
          </button>
        </div>
        <div className="space-y-4 px-5 py-4">
          <p className="rounded-2xl bg-[#1c1512] p-3.5 text-[11.5px] font-semibold leading-relaxed text-white">
            Tüm alanlar <b>opsiyonel</b> — yalnızca okuyabildiğin değerleri doldur, gerisini boş bırak.
            Girilen veriler anında güncel değerlere işlenir ve Jarvis yorumlar.
          </p>
          <div className="card-paper rounded-2xl p-4">
            <label className="eyebrow text-[#9a8c80]">Ölçüm tarihi</label>
            <input
              type="date"
              value={date}
              onChange={(e) => setDate(e.target.value)}
              className="mt-2 w-full rounded-xl border border-[#e7ddcf] bg-white px-3 py-2.5 text-sm font-bold outline-none focus:border-[#d92835]"
            />
            <p className="mt-1.5 text-[10.5px] font-bold text-[#b3a696]">
              Boş bırakırsan bugün sayılır · aynı güne ikinci giriş o günü günceller
            </p>
          </div>

          {FORM_GROUPS.map((group) => (
            <div key={group.key} className="card-paper rounded-2xl p-4">
              <p className="text-[13px] font-extrabold text-[#1c1512]">{group.label}</p>
              <p className="mt-0.5 text-[10.5px] font-bold text-[#b3a696]">{group.hint}</p>
              <div className="mt-3 grid grid-cols-2 gap-2.5">
                {group.fields.map((f) => (
                  <label key={f.key} className="block">
                    <span className="block text-[10.5px] font-bold text-[#6f6259]">{f.label}</span>
                    <span className="mt-1 flex items-center gap-1 rounded-xl border border-[#e7ddcf] bg-white px-2.5 py-2 focus-within:border-[#d92835]">
                      <input
                        value={values[f.key] ?? ''}
                        onChange={(e) => setValues((prev) => ({
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

          <div className="card-paper rounded-2xl p-4">
            <label className="eyebrow text-[#9a8c80]">Not</label>
            <textarea
              value={note}
              onChange={(e) => setNote(e.target.value.slice(0, 300))}
              rows={2}
              placeholder="Kahvaltıdan önce, aç karnına…"
              className="mt-2 w-full resize-none rounded-xl border border-[#e7ddcf] bg-white px-3 py-2.5 text-[12.5px] font-semibold outline-none focus:border-[#d92835]"
            />
          </div>

          {error && (
            <p className="flex items-center gap-1.5 rounded-xl bg-[#fde1df] px-3 py-2.5 text-xs font-bold text-[#8f1826]">
              <AlertTriangle size={14} /> {error}
            </p>
          )}
        </div>

        <div className="px-5">
          <button
            type="button"
            onClick={submit}
            disabled={saving}
            className="ember-btn flex w-full items-center justify-center gap-2 rounded-2xl py-4 text-[15px] font-extrabold disabled:opacity-60"
          >
            {saving
              ? <span className="h-5 w-5 animate-spin rounded-full border-2 border-white/40 border-t-white" />
              : <><Check size={18} strokeWidth={3} /> Kaydet ({filled} alan)</>}
          </button>
        </div>
      </div>
    </div>
  );
}

/** Kişisel Bilgiler sekmesi: güncel değerler, segmentler, gelişim ve ölçüm girişi. */
export function BioDataScreen({ store }: { store: Store }) {
  const [entryOpen, setEntryOpen] = useState(false);
  const summary = store.bodyComposition;

  // Sayfa açıldığında güncel özeti çek; ölçüm girişi zaten kendi yanıtını işler.
  useEffect(() => { void store.fetchBodyComposition(); }, [store.fetchBodyComposition]);

  const hero = useMemo(
    () => (summary?.metrics ?? []).filter((m) => m.group === 'general'),
    [summary],
  );
  const segmentMetrics = useMemo(
    () => (summary?.metrics ?? []).filter((m) => m.group !== 'general'),
    [summary],
  );
  const review = summary?.review;
  const tone = review?.sentiment ?? 'neutral';

  return (
    <div>
      <PageHeader eyebrow="Kişisel Bilgiler" title="Vücut analizin" />

      {summary?.has_data ? (
        <div className="mt-5 space-y-5">
          <div className="flex flex-wrap items-center gap-2">
            <span className="inline-flex items-center gap-1.5 rounded-full border border-[#e7ddcf] bg-white/80 px-3 py-1.5 text-[10.5px] font-extrabold text-[#6f6259]">
              <Activity size={12} className="text-[#d92835]" />
              İlk kayıt: {summary.first_record_date ? formatDayShort(summary.first_record_date) : '—'}
            </span>
            <span className="inline-flex items-center gap-1.5 rounded-full border border-[#e7ddcf] bg-white/80 px-3 py-1.5 text-[10.5px] font-extrabold text-[#6f6259]">
              <TrendingUp size={12} className="text-[#b97a1a]" /> {summary.record_count} ölçüm
            </span>
          </div>

          {review?.summary && (
            <div className={`rounded-2xl border p-4 ${TONE_CLASS[tone] ?? TONE_CLASS.neutral}`}>
              <p className="flex items-center gap-1.5 text-[10px] font-extrabold uppercase tracking-widest">
                <Sparkles size={12} strokeWidth={2.6} />
                Jarvis yorumu{review.source === 'rule' ? ' · kural tabanlı' : ''}
              </p>
              <p className="mt-1.5 text-[12.5px] font-semibold leading-relaxed">{review.summary}</p>
              {!!review.highlights?.length && (
                <div className="mt-2.5 flex flex-wrap gap-1.5">
                  {review.highlights.map((h) => (
                    <span key={h} className="rounded-full border border-current/25 bg-white/70 px-2 py-0.5 text-[10.5px] font-extrabold">{h}</span>
                  ))}
                </div>
              )}
            </div>
          )}

          <SectionHead kicker="Güncel değerler" title="Yağ, kas ve sıvı" />
          <div className="grid grid-cols-2 gap-2.5">
            {hero.map((m) => <MetricCard key={m.key} metric={m} hero />)}
          </div>

          <SectionHead kicker="Segmentel dağılım" title="Bölgesel kas ve yağ" />
          <div className="grid grid-cols-2 gap-2.5">
            {(summary.segments ?? []).map((s) => <SegmentCard key={s.key} segment={s} />)}
          </div>

          {segmentMetrics.length > 0 && (
            <>
              <p className="eyebrow text-[#9a8c80]">Segment değişimleri</p>
              <div className="grid grid-cols-2 gap-2.5">
                {segmentMetrics.map((m) => <MetricCard key={m.key} metric={m} />)}
              </div>
            </>
          )}

          <SectionHead kicker="Gelişim" title="Haftalık karşılaştırma" />
          <WeeklyTable store={store} />

          <button
            type="button"
            onClick={() => setEntryOpen(true)}
            className="flex w-full items-center justify-center gap-2 rounded-2xl border-2 border-dashed border-[#ddd0bd] bg-white/70 py-3.5 text-[13px] font-extrabold text-[#6f6259] transition active:scale-[0.99]"
          >
            <Plus size={16} strokeWidth={3} /> Yeni ölçüm gir
          </button>
        </div>
      ) : (
        <div className="mt-6 space-y-4">
          <div className="card-paper rounded-3xl p-6 text-center">
            <span className="ember-btn mx-auto grid h-14 w-14 place-items-center rounded-2xl"><Activity size={24} /></span>
            <p className="font-display mt-4 text-[19px] font-extrabold leading-tight">Henüz ölçüm girmedin</p>
            <p className="mx-auto mt-2 max-w-[19rem] text-[12.5px] font-semibold leading-relaxed text-[#6f6259]">
              InBody / tanı cihazı çıktındaki yağ oranı, kas, kemik, sıvı ve bölgesel değerleri gir —
              Jarvis antrenman ve beslenme kararlarını bu veriye göre kişiselleştirir.
            </p>
            <button
              type="button"
              onClick={() => setEntryOpen(true)}
              disabled={store.bodyCompositionBusy}
              className="ember-btn mt-5 flex w-full items-center justify-center gap-2 rounded-2xl py-4 text-[15px] font-extrabold disabled:opacity-60"
            >
              {store.bodyCompositionBusy
                ? <span className="h-5 w-5 animate-spin rounded-full border-2 border-white/40 border-t-white" />
                : <><Plus size={18} strokeWidth={3} /> İlk ölçümü gir</>}
            </button>
          </div>
          <p className="rounded-2xl bg-[#1c1512] p-4 text-[11.5px] font-semibold leading-relaxed text-white">
            Tüm alanlar opsiyoneldir; yalnızca okuyabildiğin değerleri girsen de olur. Ölçümü
            tekrarladıkça gelişim tablosu ve Jarvis'in değişim yorumu otomatik oluşur.
          </p>
        </div>
      )}

      {entryOpen && <EntrySheet store={store} onClose={() => setEntryOpen(false)} />}
    </div>
  );
}