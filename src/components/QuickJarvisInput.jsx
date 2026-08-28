import { useState, useRef, useEffect, useCallback, useImperativeHandle, forwardRef } from 'react';
import { Send, Mic, MicOff, Sparkles, X } from 'lucide-react';

/**
 * QuickJarvisInput - Hızlı Jarvis Mesajlaşma Kısayulu
 *
 * Özellikler:
 * - Glassmorphism tasarım, premium his
 * - Mikrofon desteği (Web Speech API)
 * - Auto-resize textarea
 * - Enter gönderir, Shift+Enter yeni satır
 * - Focus/typing animasyonları
 * - Loading/processing state
 * - Accessibility: ARIA labels, keyboard nav
 */
const QuickJarvisInput = forwardRef(function QuickJarvisInput({
  value,
  onChange,
  onSubmit,
  disabled = false,
  placeholder = "Jarvis'e sor...",
  className = '',
  autoFocus = false
}, ref) {
  const [isExpanded, setIsExpanded] = useState(false);
  const [isListening, setIsListening] = useState(false);
  const [showClear, setShowClear] = useState(false);
  const [inputHeight, setInputHeight] = useState(52); // min height

  const textareaRef = useRef(null);
  const micButtonRef = useRef(null);
  const recognitionRef = useRef(null);
  const finalTranscriptRef = useRef('');

  // Expose focus method to parent
  useImperativeHandle(ref, () => ({
    focus: () => textareaRef.current?.focus(),
    clear: () => {
      onChange('');
      setShowClear(false);
    }
  }));

  // Auto-resize textarea
  const adjustHeight = useCallback(() => {
    const textarea = textareaRef.current;
    if (!textarea) return;

    textarea.style.height = 'auto';
    const newHeight = Math.min(textarea.scrollHeight, 140); // max 140px
    setInputHeight(newHeight);
    textarea.style.height = `${newHeight}px`;
  }, []);

  useEffect(() => {
    adjustHeight();
  }, [value, adjustHeight]);

  // Handle input change
  const handleChange = useCallback((e) => {
    const newValue = e.target.value;
    onChange(newValue);
    setShowClear(newValue.length > 0);
    adjustHeight();
  }, [onChange, adjustHeight]);

  // Handle submit
  const handleSubmit = useCallback((e) => {
    e.preventDefault();
    if (!value.trim() || disabled) return;
    onSubmit(value.trim());
  }, [value, disabled, onSubmit]);

  // Handle keydown
  const handleKeyDown = useCallback((e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      if (value.trim() && !disabled) {
        onSubmit(value.trim());
      }
    }
  }, [value, disabled, onSubmit]);

  // Clear input
  const handleClear = useCallback(() => {
    onChange('');
    setShowClear(false);
    textareaRef.current?.focus();
    adjustHeight();
  }, [onChange, adjustHeight]);

  // Speech Recognition
  const startListening = useCallback(() => {
    if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
      console.warn('Speech Recognition not supported');
      return;
    }

    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    const recognition = new SpeechRecognition();
    recognition.lang = 'tr-TR';
    recognition.interimResults = true;
    recognition.continuous = true;

    finalTranscriptRef.current = value || '';

    recognition.onstart = () => {
      setIsListening(true);
    };

    recognition.onresult = (event) => {
      let interimTranscript = '';
      for (let i = event.resultIndex; i < event.results.length; i++) {
        const transcript = event.results[i][0].transcript;
        if (event.results[i].isFinal) {
          finalTranscriptRef.current += transcript + ' ';
        } else {
          interimTranscript += transcript;
        }
      }
      const fullText = (finalTranscriptRef.current + interimTranscript).trim();
      onChange(fullText);
      setShowClear(fullText.length > 0);
      adjustHeight();
    };

    recognition.onerror = (event) => {
      console.error('Speech recognition error:', event.error);
      setIsListening(false);
    };

    recognition.onend = () => {
      setIsListening(false);
    };

    recognitionRef.current = recognition;
    recognition.start();
  }, [value, onChange, adjustHeight]);

  const stopListening = useCallback(() => {
    if (recognitionRef.current) {
      recognitionRef.current.stop();
      recognitionRef.current = null;
    }
    setIsListening(false);
  }, []);

  const toggleListening = useCallback(() => {
    if (isListening) {
      stopListening();
    } else {
      startListening();
    }
  }, [isListening, startListening, stopListening]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (recognitionRef.current) {
        recognitionRef.current.stop();
      }
    };
  }, []);

  // Focus effect
  useEffect(() => {
    if (autoFocus && textareaRef.current) {
      textareaRef.current.focus();
    }
  }, [autoFocus]);

  const isActive = isExpanded || isListening || value.length > 0;

  return (
    <div className={`flow-jarvis-input ${className}`}>
      <form onSubmit={handleSubmit} className="w-full">
        <div className={`relative group transition-all duration-300 ${isActive ? 'jarvis-active' : ''}`}>
          {/* Background glow when active */}
          <div className={`absolute inset-0 rounded-2xl bg-gradient-to-r from-orange-500/5 via-transparent to-emerald-500/5 opacity-0 group-has-[:focus-within]:opacity-100 group-has-[.jarvis-listening]:opacity-100 transition-opacity duration-300 pointer-events-none`} />

          {/* Border glow */}
          <div className={`absolute inset-0 rounded-2xl border transition-all duration-300 ${
            isListening
              ? 'border-emerald-500/50 shadow-[0_0_20px_-5px_rgba(16,185,129,0.3)]'
              : isExpanded
              ? 'border-orange-500/30 shadow-[0_0_15px_-5px_rgba(249,115,22,0.2)]'
              : 'border-neutral-800/50'
          }`} />

          {/* Input Wrapper */}
          <div className="relative flex items-end gap-2 p-1 bg-neutral-900/40 backdrop-blur-xl rounded-2xl">
            {/* Sparkles decoration when empty */}
            {!value && !isListening && (
              <div className="absolute left-4 top-1/2 -translate-y-1/2 flex items-center gap-1 pointer-events-none opacity-50 transition-opacity duration-200 group-has-[:focus-within]:opacity-0">
                <Sparkles className="w-4 h-4 text-orange-400/70 animate-pulse" />
                <Sparkles className="w-3 h-3 text-emerald-400/70 animate-pulse" style={{ animationDelay: '200ms' }} />
                <Sparkles className="w-4 h-4 text-orange-400/70 animate-pulse" style={{ animationDelay: '400ms' }} />
              </div>
            )}

            {/* Textarea */}
            <textarea
              ref={textareaRef}
              value={value}
              onChange={handleChange}
              onKeyDown={handleKeyDown}
              onFocus={() => setIsExpanded(true)}
              onBlur={() => setTimeout(() => setIsExpanded(false), 100)}
              placeholder={placeholder}
              disabled={disabled || isListening}
              rows={1}
              style={{
                height: `${inputHeight}px`,
                minHeight: '52px',
                maxHeight: '140px'
              }}
              className={`
                flex-1 bg-transparent border-none outline-none resize-none
                text-sm sm:text-base text-white placeholder:text-neutral-500
                font-sans leading-relaxed
                pr-16 pl-1 ${!value && !isListening ? 'pl-12' : 'pl-4'}
                disabled:opacity-50 disabled:cursor-not-allowed
                scrollbar-hide
              `}
              aria-label="Jarvis'e mesaj yazın"
              aria-expanded={isExpanded}
            />

            {/* Action Buttons */}
            <div className="flex items-center gap-1 shrink-0">
              {/* Clear Button */}
              {showClear && !isListening && (
                <button
                  type="button"
                  onClick={handleClear}
                  className="p-2 rounded-xl bg-neutral-800/50 hover:bg-neutral-700/50 text-neutral-400 hover:text-white transition-all duration-200 active:scale-95"
                  aria-label="Temizle"
                >
                  <X className="w-4 h-4" strokeWidth={2.5} />
                </button>
              )}

              {/* Mic Button */}
              <button
                ref={micButtonRef}
                type="button"
                onClick={toggleListening}
                disabled={disabled}
                className={`
                  p-2.5 rounded-xl transition-all duration-200 active:scale-95
                  flex items-center justify-center shrink-0
                  ${isListening
                    ? 'bg-emerald-500 text-black shadow-[0_0_15px_rgba(16,185,129,0.4)] animate-pulse jarvis-listening'
                    : 'bg-neutral-800/50 hover:bg-neutral-700/50 text-neutral-300 hover:text-white'
                  }
                  ${disabled ? 'opacity-30 cursor-not-allowed' : ''}
                `}
                aria-label={isListening ? 'Dinlemeyi durdur' : 'Sesli mesaj kaydet'}
                aria-pressed={isListening}
              >
                {isListening ? (
                  <MicOff className="w-5 h-5" strokeWidth={2.5} />
                ) : (
                  <Mic className="w-5 h-5" strokeWidth={2.5} />
                )}
              </button>

              {/* Send Button */}
              <button
                type="submit"
                disabled={disabled || !value.trim() || isListening}
                className={`
                  p-2.5 rounded-xl transition-all duration-200 active:scale-95
                  flex items-center justify-center shrink-0
                  ${value.trim() && !disabled && !isListening
                    ? 'bg-orange-500 text-black hover:bg-orange-400 shadow-[0_0_15px_rgba(249,115,22,0.4)]'
                    : 'bg-neutral-800/50 text-neutral-500 cursor-not-allowed'
                  }
                `}
                aria-label="Gönder"
              >
                <Send className="w-5 h-5" strokeWidth={2.5} />
              </button>
            </div>
          </div>
        </div>

        {/* Listening indicator */}
        {isListening && (
          <div className="mt-2 flex items-center gap-2 text-[10px] font-mono text-emerald-400 animate-slideUp">
            <span className="flex items-center gap-1">
              <span className="w-1.5 h-1.5 bg-emerald-500 rounded-full animate-pulse" />
              <span className="w-1.5 h-1.5 bg-emerald-500 rounded-full animate-pulse" style={{ animationDelay: '100ms' }} />
              <span className="w-1.5 h-1.5 bg-emerald-500 rounded-full animate-pulse" style={{ animationDelay: '200ms' }} />
            </span>
            <span>Dinleniyor... Konuşmaya devam edin</span>
            <kbd className="px-1.5 py-0.5 bg-neutral-800 rounded text-[9px] font-mono text-neutral-400 border border-neutral-700">Enter</kbd> ile gönder
          </div>
        )}

        {/* Hint when empty */}
        {!value && !isListening && !isExpanded && (
          <p className="mt-2 text-[10px] font-mono text-neutral-500 text-center animate-fadeIn whitespace-nowrap overflow-hidden text-ellipsis px-2">
            Örn: <span className="text-neutral-400">"Bugün sırtım nasıl olmalı?"</span> ·{" "}
            <span className="text-neutral-400">"Protein hedefim kaç?"</span>
          </p>
        )}
      </form>

      <style jsx>{`
        .jarvis-active textarea {
          background: rgba(249, 115, 22, 0.02);
        }
        @keyframes slideUp {
          from { opacity: 0; transform: translateY(8px); }
          to { opacity: 1; transform: translateY(0); }
        }
        .animate-slideUp {
          animation: slideUp 0.3s ease-out both;
        }
        @keyframes fadeIn {
          from { opacity: 0; transform: translateY(4px); }
          to { opacity: 1; transform: translateY(0); }
        }
        .animate-fadeIn {
          animation: fadeIn 0.3s ease-out both;
        }
      `}</style>
    </div>
  );
});

QuickJarvisInput.displayName = 'QuickJarvisInput';

export default QuickJarvisInput;