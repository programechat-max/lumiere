import { Radar, Sparkles, CalendarDays, Dumbbell, UtensilsCrossed, LineChart } from 'lucide-react';

export const NAV_ITEMS = [
  { key: 'flow', label: 'Akış', Icon: Radar },
  { key: 'chat', label: 'Lumiere', Icon: Sparkles },
  { key: 'daily', label: 'Günlük', Icon: CalendarDays },
  { key: 'workout', label: 'Antrenman', Icon: Dumbbell },
  { key: 'nutrition', label: 'Beslenme', Icon: UtensilsCrossed },
  { key: 'progress', label: 'Gelişim', Icon: LineChart },
];
export const NAV_KEYS = NAV_ITEMS.map(({ key }) => key);

/**
 * Alt navigasyon çubuğu (love repo BottomNav port'u).
 * TanStack Link yerine state tabanlı `onNavigate(key)` kullanılır.
 */
export default function BottomNav({ activeTab, onNavigate }) {
  return (
    <nav className="fixed inset-x-0 bottom-0 z-40 border-t border-border bg-background/85 pad-safe-bottom backdrop-blur-xl">
      <ul className="mx-auto grid max-w-md grid-cols-6 px-1 py-1">
        {NAV_ITEMS.map(({ key, label, Icon }) => {
          const isActive = activeTab === key;
          return (
            <li key={key} className="min-w-0">
              <button
                type="button"
                onClick={() => onNavigate?.(key)}
                aria-current={isActive ? 'page' : undefined}
                className={`flex w-full flex-col items-center justify-center gap-0.5 rounded-lg px-0.5 py-1 transition-colors ${isActive ? 'text-primary-glow' : 'text-muted-foreground'}`}
              >
                <span className={`grid h-7 w-9 shrink-0 place-items-center rounded-full transition-colors ${isActive ? 'bg-primary/15' : ''}`}>
                  <Icon size={17} strokeWidth={isActive ? 2.6 : 2} />
                </span>
                <span className="w-full truncate text-center text-[9px] font-bold tracking-tight">{label}</span>
              </button>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}