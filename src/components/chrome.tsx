import type { ReactNode } from 'react';
import {
  CalendarDays, ChevronLeft, ChevronRight, Dumbbell, Flame,
  LayoutGrid, LineChart, Settings2, Sparkles, UtensilsCrossed,
} from 'lucide-react';
import type { TabKey } from '../lib/types';
import { dayLabelRelative, formatDayLong } from '../lib/utils';

export const NAV_ORDER: TabKey[] = ['flow', 'coach', 'daily', 'workout', 'nutrition', 'progress'];

const NAV_META: Array<{ key: TabKey; label: string; Icon: typeof LayoutGrid }> = [
  { key: 'flow', label: 'Akış', Icon: LayoutGrid },
  { key: 'coach', label: 'AI Koç', Icon: Sparkles },
  { key: 'daily', label: 'Günlük', Icon: CalendarDays },
  { key: 'workout', label: 'Antrenman', Icon: Dumbbell },
  { key: 'nutrition', label: 'Beslenme', Icon: UtensilsCrossed },
  { key: 'progress', label: 'Gelişim', Icon: LineChart },
];

export function Logo({ compact = false }: { compact?: boolean }) {
  return (
    <div className="flex min-w-0 items-center gap-2.5">
      <div className="ember-btn grid h-10 w-10 shrink-0 place-items-center rounded-2xl">
        <Flame size={19} strokeWidth={2.4} />
      </div>
      {!compact && (
        <div className="min-w-0 leading-none">
          <p className="font-display truncate text-[17px] font-extrabold tracking-tight text-[#1c1512]">LUMIERE</p>
          <p className="eyebrow mt-1 text-[#d92835]">Coaching</p>
        </div>
      )}
    </div>
  );
}

export function PageHeader({
  eyebrow, title, onOpenSettings, action,
}: {
  eyebrow: string; title: string; onOpenSettings?: () => void; action?: ReactNode;
}) {
  return (
    <header className="sticky top-0 z-30 -mx-5 border-b border-[#e7ddcf] bg-[#f4f1ec]/90 px-5 pb-3 pt-[max(1.25rem,env(safe-area-inset-top))] backdrop-blur-xl">
      <div className="flex items-center justify-between gap-3">
        <Logo />
        <div className="flex shrink-0 items-center gap-2">
          {action}
          {onOpenSettings && (
            <button
              type="button"
              onClick={onOpenSettings}
              aria-label="Ayarlar"
              className="grid h-10 w-10 place-items-center rounded-full border border-[#e2d7c6] bg-white/80 text-[#6f6259] transition active:scale-95"
            >
              <Settings2 size={18} />
            </button>
          )}
        </div>
      </div>
      <p className="eyebrow mt-4 text-[#d92835]">{eyebrow}</p>
      <h1 className="font-display mt-1 text-[26px] font-extrabold leading-tight text-[#1c1512]">{title}</h1>
    </header>
  );
}

export function BottomNav({ active, onNavigate }: { active: TabKey; onNavigate: (t: TabKey) => void }) {
  return (
    <nav className="fixed inset-x-0 bottom-0 z-40 px-4 pb-[max(0.9rem,env(safe-area-inset-bottom))]">
      <ul className="mx-auto grid max-w-md grid-cols-6 gap-0.5 rounded-[26px] border border-[#e7ddcf] bg-white/92 p-1.5 shadow-[0_18px_45px_-20px_rgba(60,32,28,0.4)] backdrop-blur-xl">
        {NAV_META.map(({ key, label, Icon }) => {
          const on = active === key;
          return (
            <li key={key} className="min-w-0">
              <button
                type="button"
                onClick={() => onNavigate(key)}
                aria-current={on ? 'page' : undefined}
                className={`flex w-full flex-col items-center justify-center gap-1 rounded-2xl px-0.5 py-2 transition-all ${on ? 'bg-[#1c1512] text-white shadow-[0_10px_22px_-10px_rgba(28,21,18,0.7)]' : 'text-[#9a8c80] active:scale-95'}`}
              >
                <span className="relative">
                  <Icon size={18} strokeWidth={on ? 2.5 : 2} />
                  {on && <span className="absolute -right-1.5 -top-1.5 h-2 w-2 rounded-full bg-[#ff5a63]" />}
                </span>
                <span className="w-full truncate text-center text-[9px] font-extrabold tracking-tight">{label}</span>
              </button>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}

export function Ring({
  value, target, label, unit, tone = 'red', size = 92,
}: {
  value: number; target: number; label: string; unit: string;
  tone?: 'red' | 'green' | 'amber'; size?: number;
}) {
  const pct = Math.max(0, Math.min(1, target > 0 ? value / target : 0));
  const stroke = 9;
  const r = (size - stroke) / 2;
  const c = 2 * Math.PI * r;
  const color = tone === 'red' ? '#d92835' : tone === 'green' ? '#2e9e5b' : '#d99a2b';
  return (
    <div className="flex min-w-0 flex-col items-center gap-1.5">
      <div className="relative" style={{ width: size, height: size }}>
        <svg width={size} height={size} className="-rotate-90">
          <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="#eadfd3" strokeWidth={stroke} />
          <circle
            cx={size / 2} cy={size / 2} r={r} fill="none"
            stroke={color} strokeWidth={stroke} strokeLinecap="round"
            strokeDasharray={c} strokeDashoffset={c * (1 - pct)}
            style={{ transition: 'stroke-dashoffset 700ms ease' }}
          />
        </svg>
        <div className="absolute inset-0 grid place-items-center">
          <span className="font-display text-[17px] font-extrabold leading-none text-[#1c1512]">{Math.round(pct * 100)}%</span>
        </div>
      </div>
      <p className="eyebrow text-[#9a8c80]">{label}</p>
      <p className="text-xs font-bold text-[#1c1512]">
        {value.toLocaleString('tr-TR')} <span className="font-semibold text-[#9a8c80]">/ {target.toLocaleString('tr-TR')} {unit}</span>
      </p>
    </div>
  );
}

export function HBar({ pct, tone = 'red', height = 8 }: { pct: number; tone?: 'red' | 'green' | 'amber' | 'ink'; height?: number }) {
  const bg = tone === 'red' ? 'linear-gradient(90deg,#ff5a63,#d92835)' : tone === 'green' ? 'linear-gradient(90deg,#4cc38a,#2e9e5b)' : tone === 'amber' ? 'linear-gradient(90deg,#e8b34b,#d99a2b)' : 'linear-gradient(90deg,#4a3d34,#1c1512)';
  return (
    <div className="w-full overflow-hidden rounded-full bg-[#eadfd3]" style={{ height }}>
      <div className="h-full rounded-full transition-all duration-700" style={{ width: `${Math.max(0, Math.min(100, pct))}%`, background: bg }} />
    </div>
  );
}

export function SectionHead({ kicker, title, right }: { kicker: string; title?: string; right?: ReactNode }) {
  return (
    <div className="mb-3 flex items-end justify-between gap-2">
      <div className="min-w-0">
        <p className="eyebrow text-[#b3a696]">{kicker}</p>
        {title && <h3 className="font-display mt-1 text-[17px] font-extrabold text-[#1c1512]">{title}</h3>}
      </div>
      {right && <div className="shrink-0">{right}</div>}
    </div>
  );
}

export function DayNavigator({
  iso, onChange, onShift, note,
}: {
  iso: string; onChange: (iso: string) => void; onShift: (d: number) => void; note?: string;
}) {
  return (
    <section className="card-paper rounded-3xl p-3">
      <div className="flex items-center justify-between gap-2">
        <button
          type="button" onClick={() => onShift(-1)} aria-label="Önceki gün"
          className="grid h-11 w-11 shrink-0 place-items-center rounded-full border border-[#e7ddcf] bg-white text-[#1c1512] transition active:scale-90"
        >
          <ChevronLeft size={19} />
        </button>
        <div className="min-w-0 flex-1 text-center">
          <span className="inline-block rounded-full bg-[#1c1512] px-2.5 py-0.5 text-[10px] font-extrabold uppercase tracking-widest text-white">
            {dayLabelRelative(iso)}
          </span>
          <p className="font-display mt-1 truncate text-[16px] font-extrabold capitalize text-[#1c1512]">{formatDayLong(iso)}</p>
          <input
            type="date" value={iso} max="2026-09-08"
            onChange={(e) => e.target.value && onChange(e.target.value)}
            className="mt-0.5 bg-transparent text-center text-[11px] font-semibold text-[#9a8c80] outline-none"
          />
        </div>
        <button
          type="button" onClick={() => onShift(1)} aria-label="Sonraki gün"
          className="grid h-11 w-11 shrink-0 place-items-center rounded-full border border-[#e7ddcf] bg-white text-[#1c1512] transition active:scale-90"
        >
          <ChevronRight size={19} />
        </button>
      </div>
      {note && <p className="mt-2 rounded-xl bg-[#f6efe4] px-3 py-2 text-center text-[11px] font-semibold text-[#8a7a6c]">{note}</p>}
    </section>
  );
}

export function Empty({ text }: { text: string }) {
  return <p className="rounded-2xl border border-dashed border-[#ddd0bd] bg-white/60 px-3 py-5 text-center text-xs font-semibold text-[#9a8c80]">{text}</p>;
}
