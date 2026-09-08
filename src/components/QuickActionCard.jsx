import { useCallback } from 'react';

/**
 * QuickActionCard - Mockup'taki ".quick" kartının birebir karşılığı (lp-quick).
 * Düz koyu kart + renkli ikon karesi + başlık + kısa açıklama.
 */
const ACCENT_CLASS = {
  red: 'lp-quick',
  emerald: 'lp-quick green',
  green: 'lp-quick green',
};

export default function QuickActionCard({
  icon: Icon,
  title,
  subtitle,
  accent = 'red',
  onPress,
  disabled = false,
  ariaLabel,
}) {
  const handleClick = useCallback(() => {
    if (disabled) return;
    onPress?.();
  }, [disabled, onPress]);

  return (
    <button
      type="button"
      className={ACCENT_CLASS[accent] || 'lp-quick'}
      onClick={handleClick}
      disabled={disabled}
      aria-label={ariaLabel || title}
    >
      <span className="lp-quick-icon">
        {Icon ? <Icon strokeWidth={2.25} /> : <span>＋</span>}
      </span>
      <strong>{title}</strong>
      <p>{subtitle}</p>
    </button>
  );
}
