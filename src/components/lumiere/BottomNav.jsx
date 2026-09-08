import { Radar, Sparkles, CalendarDays, Dumbbell, UtensilsCrossed } from 'lucide-react';

export const NAV_ITEMS = [
  { key: 'flow', label: 'Akış', Icon: Radar },
  { key: 'chat', label: 'Lumiere', Icon: Sparkles },
  { key: 'daily', label: 'Günlük', Icon: CalendarDays },
  { key: 'workout', label: 'Antrenman', Icon: Dumbbell },
  { key: 'nutrition', label: 'Beslenme', Icon: UtensilsCrossed },
];
export const NAV_KEYS = NAV_ITEMS.map(({ key }) => key);

/**
 * Alt navigasyon çubuğu (love repo BottomNav port'u).
 * TanStack Link yerine state tabanlı `onNavigate(key)` kullanılır.
 */
export default function BottomNav({ activeTab, onNavigate }) {
  return (
    <nav className="fixed inset-x-0 bottom-0 z-40 border-t border-border bg-background/85 pad-safe-bottom backdrop-blur-xl">
      <ul className="mx-auto grid max-w-md grid-cols-5 px-1 pt-1.5">
        {NAV_ITEMS.map(({ key, label, Icon }) => {
          const isActive = activeTab === key;
          return (
            <li key={key} className="min-w-0">
              <button
                type="button"
                onClick={() => onNavigate?.(key)}
                aria-current={isActive ? 'page' : undefined}
                className={`flex min-h-12 flex-col items-center justify-center gap-1 rounded-xl px-1 py-1.5 transition-colors ${isActive ? 'text-primary-glow' : 'text-muted-foreground'}`}
              >
                <span className={`grid h-8 w-12 shrink-0 place-items-center rounded-full transition-colors ${isActive ? 'bg-primary/15' : ''}`}>
                  <Icon size={19} strokeWidth={isActive ? 2.6 : 2} />
                </span>
                <span className="w-full truncate text-center text-[10px] font-bold tracking-tight">{label}</span>
              </button>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}