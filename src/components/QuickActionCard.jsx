import { useState, useRef, forwardRef, useImperativeHandle, useCallback } from 'react';
import { Zap, Sparkles, CheckCircle, Loader2 } from 'lucide-react';

/**
 * QuickActionCard - Hızlı Aksiyon Kartı
 *
 * Özellikler:
 * - Glassmorphism tasarım (cam efekti, yumuşak gölgeler)
 * - Micro-interactions: press ripple, hover lift, icon pulse
 * - Loading/success states
 * - Accessibility: keyboard nav, ARIA, focus visible
 * - Responsive: mobilde yan yana, tablet/desktop'ta grid
 * - Icon + gradient background, premium his
 */
const QuickActionCard = forwardRef(function QuickActionCard({
  icon: Icon,
  title,
  subtitle,
  accent = 'orange',
  onPress,
  disabled = false,
  ariaLabel,
  showSparkle = false,
  className = ''
}, ref) {
  const [isPressed, setIsPressed] = useState(false);
  const [isHovered, setIsHovered] = useState(false);
  const [state, setState] = useState('idle'); // idle, loading, success
  const cardRef = useRef(null);
  const rippleRef = useRef(null);

  // Expose methods
  useImperativeHandle(ref, () => ({
    trigger: () => onPress?.(),
    setLoading: (loading) => setState(loading ? 'loading' : 'idle'),
    setSuccess: () => {
      setState('success');
      setTimeout(() => setState('idle'), 2000);
    }
  }));

  // Accent color configurations
  const accentColors = {
    orange: {
      primary: '#f97316',
      primaryHover: '#ea580c',
      glow: 'rgba(249, 115, 22, 0.3)',
      glowStrong: 'rgba(249, 115, 22, 0.5)',
      ring: 'rgba(249, 115, 22, 0.2)',
      bg: 'rgba(249, 115, 22, 0.05)',
    },
    emerald: {
      primary: '#10b981',
      primaryHover: '#059669',
      glow: 'rgba(16, 185, 129, 0.3)',
      glowStrong: 'rgba(16, 185, 129, 0.5)',
      ring: 'rgba(16, 185, 129, 0.2)',
      bg: 'rgba(16, 185, 129, 0.05)',
    },
    blue: {
      primary: '#3b82f6',
      primaryHover: '#2563eb',
      glow: 'rgba(59, 130, 246, 0.3)',
      glowStrong: 'rgba(59, 130, 246, 0.5)',
      ring: 'rgba(59, 130, 246, 0.2)',
      bg: 'rgba(59, 130, 246, 0.05)',
    },
    purple: {
      primary: '#a855f7',
      primaryHover: '#9333ea',
      glow: 'rgba(168, 85, 247, 0.3)',
      glowStrong: 'rgba(168, 85, 247, 0.5)',
      ring: 'rgba(168, 85, 247, 0.2)',
      bg: 'rgba(168, 85, 247, 0.05)',
    },
  };

  const colors = accentColors[accent] || accentColors.orange;

  // Handle press with ripple effect
  const handlePress = useCallback(async (e) => {
    if (disabled || state !== 'idle') return;

    // Create ripple at click position
    const rect = cardRef.current?.getBoundingClientRect();
    if (rect && rippleRef.current) {
      const x = e.clientX - rect.left;
      const y = e.clientY - rect.top;
      rippleRef.current.style.setProperty('--ripple-x', `${x}px`);
      rippleRef.current.style.setProperty('--ripple-y', `${y}px`);
      rippleRef.current.classList.add('ripple-active');
      setTimeout(() => rippleRef.current?.classList.remove('ripple-active'), 400);
    }

    // Press animation
    setIsPressed(true);
    setTimeout(() => setIsPressed(false), 150);

    // Execute action
    setState('loading');
    try {
      await onPress?.(e);
      setState('success');
      setTimeout(() => setState('idle'), 1500);
    } catch (error) {
      console.error('QuickActionCard error:', error);
      setState('idle');
    }
  }, [disabled, state, onPress]);

  // Keyboard support
  const handleKeyDown = useCallback((e) => {
    if ((e.key === 'Enter' || e.key === ' ') && !disabled && state === 'idle') {
      e.preventDefault();
      handlePress(e);
    }
  }, [disabled, state, handlePress]);

  // Press handlers for mouse/touch
  const handleMouseDown = useCallback(() => {
    if (!disabled) setIsPressed(true);
  }, [disabled]);

  const handleMouseUp = useCallback(() => {
    setIsPressed(false);
  }, []);

  const handleMouseLeave = useCallback(() => {
    setIsPressed(false);
    setIsHovered(false);
  }, []);

  const handleMouseEnter = useCallback(() => {
    if (!disabled) setIsHovered(true);
  }, [disabled]);

  // Dynamic styles
  const cardStyle = {
    transform: isPressed ? 'scale(0.97)' : isHovered ? 'translateY(-2px)' : 'none',
    boxShadow: isHovered
      ? `0 12px 40px -10px ${colors.glowStrong}, 0 4px 20px -5px ${colors.glow}`
      : `0 4px 20px -5px ${colors.glow}`,
    borderColor: isHovered ? `${colors.primary}40` : 'transparent',
  };

  const iconStyle = {
    background: `linear-gradient(135deg, ${colors.primary}, ${colors.primaryHover})`,
    boxShadow: `0 4px 20px -5px ${colors.glowStrong}`,
    transform: isHovered ? 'scale(1.05) rotate(3deg)' : isPressed ? 'scale(0.95)' : 'none',
  };

  return (
    <button
      ref={cardRef}
      onClick={handlePress}
      onKeyDown={handleKeyDown}
      onMouseDown={handleMouseDown}
      onMouseUp={handleMouseUp}
      onMouseLeave={handleMouseLeave}
      onMouseEnter={handleMouseEnter}
      onTouchStart={handleMouseDown}
      onTouchEnd={handleMouseUp}
      onTouchCancel={handleMouseUp}
      disabled={disabled || state !== 'idle'}
      aria-label={ariaLabel || `${title}: ${subtitle}`}
      aria-busy={state === 'loading'}
      aria-disabled={disabled || state !== 'idle'}
      className={`flow-quick-action-card relative overflow-hidden group ${className}`}
      style={cardStyle}
      tabIndex={disabled ? -1 : 0}
      type="button"
    >
      {/* Ripple Effect */}
      <div
        ref={rippleRef}
        className="absolute inset-0 overflow-hidden pointer-events-none"
        style={{
          '--ripple-x': '50%',
          '--ripple-y': '50%',
        }}
      >
        <div className="ripple" />
      </div>

      {/* Background Layers */}
      <div className="absolute inset-0 bg-gradient-to-br from-neutral-900/60 via-neutral-900/40 to-neutral-950/60" />
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,_var(--tw-gradient-stops))] from-transparent via-transparent to-neutral-900/30" />

      {/* Accent glow when hovered */}
      <div
        className="absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity duration-300"
        style={{
          background: `radial-gradient(circle at var(--ripple-x, 50%) var(--ripple-y, 50%), ${colors.bg} 0%, transparent 70%)`,
        }}
      />

      {/* Top accent bar */}
      <div
        className="absolute top-0 left-1/4 right-1/4 h-0.5 opacity-0 group-hover:opacity-100 transition-all duration-300"
        style={{ background: `linear-gradient(90deg, transparent, ${colors.primary}, transparent)` }}
      />

      {/* Content */}
      <div className="relative flex flex-col items-center justify-center p-3.5 sm:p-5 h-full min-h-[108px] sm:min-h-[140px] text-center">
        {/* Icon Wrapper */}
        <div className="relative mb-4">
          {/* Sparkle decoration */}
          {showSparkle && (
            <Sparkles
              className="absolute -top-1.5 -right-1.5 w-3.5 h-3.5 text-orange-400/60 animate-pulse"
              style={{ animationDelay: '0ms' }}
            />
          )}

          {/* Icon Button */}
          <div
            className={`
              w-12 h-12 sm:w-16 sm:h-16 rounded-xl sm:rounded-2xl flex items-center justify-center
              transition-all duration-300 ease-out
              ${state === 'loading' ? 'animate-pulse' : ''}
              ${state === 'success' ? 'animate-bounce' : ''}
            `}
            style={iconStyle}
          >
            {state === 'loading' ? (
              <Loader2 className="w-5 h-5 sm:w-7 sm:h-7 text-white animate-spin" strokeWidth={2.5} />
            ) : state === 'success' ? (
              <CheckCircle className="w-5 h-5 sm:w-7 sm:h-7 text-white" strokeWidth={2.5} />
            ) : (
              <Icon className="w-5 h-5 sm:w-7 sm:h-7 text-white" strokeWidth={2} />
            )}

            {/* Pulse ring when hovered */}
            <div
              className="absolute inset-0 rounded-2xl border-2 opacity-0 group-hover:opacity-100 transition-all duration-300"
              style={{ borderColor: colors.primary, boxShadow: `0 0 20px ${colors.glow}` }}
            />
          </div>
        </div>

        {/* Text Content */}
        <div className="w-full">
          <h3 className="text-sm font-bold text-white tracking-tight mb-1 group-hover:tracking-normal transition-all duration-200">
            {title}
          </h3>
          <p className="text-[11px] font-mono text-neutral-500 leading-snug group-hover:text-neutral-400 transition-colors">
            {subtitle}
          </p>
        </div>

        {/* State indicator */}
        {(state === 'loading' || state === 'success') && (
          <div className="mt-4 flex items-center justify-center gap-2 animate-fadeIn">
            {state === 'loading' && (
              <>
                <Loader2 className="w-4 h-4 text-white/70 animate-spin" strokeWidth={2.5} />
                <span className="text-[10px] font-mono text-white/70">İşleniyor...</span>
              </>
            )}
            {state === 'success' && (
              <>
                <CheckCircle className="w-4 h-4 text-emerald-400" strokeWidth={2.5} />
                <span className="text-[10px] font-mono text-emerald-400">Hazır!</span>
              </>
            )}
          </div>
        )}

        {/* Chevron indicator */}
        <div className="mt-3 opacity-0 group-hover:opacity-100 transition-all duration-300 translate-y-1 group-hover:translate-y-0">
          <Zap className="w-4 h-4" strokeWidth={2} style={{ color: colors.primary }} />
        </div>
      </div>

      {/* Focus ring for keyboard navigation */}
      <div
        className="absolute inset-0 rounded-2xl pointer-events-none opacity-0 focus-visible:opacity-100 transition-opacity"
        style={{ boxShadow: `0 0 0 3px ${colors.ring}` }}
      />

      <style jsx>{`
        .ripple {
          position: absolute;
          width: 200px;
          height: 200px;
          border-radius: 50%;
          background: radial-gradient(circle, var(--accent-primary) 0%, transparent 70%);
          transform: translate(-50%, -50%) scale(0);
          opacity: 0;
          pointer-events: none;
          left: var(--ripple-x, 50%);
          top: var(--ripple-y, 50%);
        }
        .ripple-active .ripple {
          animation: rippleExpand 0.4s ease-out forwards;
        }
        @keyframes rippleExpand {
          0% { transform: translate(-50%, -50%) scale(0); opacity: 0.3; }
          100% { transform: translate(-50%, -50%) scale(2.5); opacity: 0; }
        }
        @keyframes fadeIn {
          from { opacity: 0; transform: translateY(4px); }
          to { opacity: 1; transform: translateY(0); }
        }
        .animate-fadeIn { animation: fadeIn 0.3s ease-out both; }
        @keyframes bounce {
          0%, 100% { transform: scale(1); }
          50% { transform: scale(1.1); }
        }
        .animate-bounce { animation: bounce 0.4s ease-out; }
      `}</style>
    </button>
  );
});

QuickActionCard.displayName = 'QuickActionCard';

export default QuickActionCard;