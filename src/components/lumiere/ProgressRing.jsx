const toneVar = {
  primary: 'var(--primary)',
  success: 'var(--success)',
  warning: 'var(--warning)',
};

/**
 * SVG ilerleme halkası — Kalori / Protein / Antrenman gibi hedef sütunları.
 */
export default function ProgressRing({ value, target, label, unit, tone = 'primary', size = 96 }) {
  const pct = Math.max(0, Math.min(1, target > 0 ? value / target : 0));
  const stroke = 8;
  const r = (size - stroke) / 2;
  const c = 2 * Math.PI * r;

  return (
    <div className="flex min-w-0 flex-col items-center gap-2">
      <div className="relative" style={{ width: size, height: size }}>
        <svg width={size} height={size} className="-rotate-90">
          <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="var(--border)" strokeWidth={stroke} />
          <circle
            cx={size / 2}
            cy={size / 2}
            r={r}
            fill="none"
            stroke={toneVar[tone]}
            strokeWidth={stroke}
            strokeLinecap="round"
            strokeDasharray={c}
            strokeDashoffset={c * (1 - pct)}
            style={{ transition: 'stroke-dashoffset 700ms ease' }}
          />
        </svg>
        <div className="absolute inset-0 grid place-items-center">
          <span className="font-display text-lg font-extrabold leading-none">{Math.round(pct * 100)}%</span>
        </div>
      </div>
      <div className="text-center">
        <p className="eyebrow text-muted-foreground">{label}</p>
        <p className="text-xs font-semibold">
          {value}
          <span className="text-muted-foreground"> / {target} {unit}</span>
        </p>
      </div>
    </div>
  );
}