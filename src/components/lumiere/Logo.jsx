import { Flame } from 'lucide-react';

/**
 * LUMIERE Logo markası (love repo'dan port).
 * size: sm | md | lg — showText ile marka yazısı açılır/kapanır.
 */
export default function Logo({ size = 'md', showText = true }) {
  const box = size === 'lg' ? 'h-16 w-16' : size === 'sm' ? 'h-9 w-9' : 'h-11 w-11';
  const icon = size === 'lg' ? 30 : size === 'sm' ? 17 : 21;

  return (
    <div className="flex min-w-0 items-center gap-3">
      <div className={`${box} ember ember-glow grid shrink-0 place-items-center rounded-2xl`}>
        <Flame size={icon} strokeWidth={2.4} />
      </div>
      {showText && (
        <div className="min-w-0">
          <p className="font-display truncate text-base font-extrabold tracking-tight">LUMIERE</p>
          <p className="eyebrow text-primary-glow">Coaching</p>
        </div>
      )}
    </div>
  );
}