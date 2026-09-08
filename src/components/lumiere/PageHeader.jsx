import { Settings2 } from 'lucide-react';

/**
 * Yapışkan üst başlık — alt çizgili, blur'lı, sağda isteğe bağlı aksiyon + ayarlar.
 * Love repo `app` layout'undan port.
 */
export default function PageHeader({ eyebrow, title, action = null, showSettings = true, onOpenSettings = null }) {
  return (
    <header className="sticky top-0 z-30 -mx-5 mb-4 grid grid-cols-[minmax(0,1fr)_auto] items-center gap-3 border-b border-border bg-background/85 px-5 pb-3 pad-safe-top backdrop-blur-xl">
      <div className="min-w-0">
        <p className="eyebrow text-primary-glow">{eyebrow}</p>
        <h1 className="truncate text-xl font-extrabold sm:text-2xl">{title}</h1>
      </div>
      <div className="flex shrink-0 items-center gap-2">
        {action}
        {showSettings && onOpenSettings && (
          <button
            type="button"
            onClick={onOpenSettings}
            aria-label="Ayarlar"
            className="grid h-10 w-10 place-items-center rounded-full border border-border bg-surface text-muted-foreground active:scale-95"
          >
            <Settings2 size={18} />
          </button>
        )}
      </div>
    </header>
  );
}