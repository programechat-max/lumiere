import { useEffect } from 'react';
import { Send, Settings2, Sparkles } from 'lucide-react';

const quick = ['Protein hedefim?', 'Bugün ne yemeliyim?', 'Kaslarım ağrıyor'];

/**
 * Chat ekranı — love repo `src/routes/app.chat.tsx` tasarımı.
 * Backend: /api/chat + /api/chat/history (App.jsx'te çekilir).
 */
export default function ChatScreen({ messages, input, sending, onInputChange, onSubmit, chatEndRef, onOpenSettings }) {
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' });
  }, [messages]);

  const send = (text) => onSubmit(null, text);

  return (
    <main className="flex min-h-dvh flex-col">
      <header className="sticky top-0 z-30 -mx-5 grid grid-cols-[auto_minmax(0,1fr)_auto] items-center gap-3 border-b border-border bg-background/85 px-5 pb-3 pad-safe-top backdrop-blur-xl">
        <span className="ember grid h-11 w-11 shrink-0 place-items-center rounded-2xl">
          <Sparkles size={19} />
        </span>
        <div className="min-w-0">
          <p className="truncate text-sm font-bold">Lumiere AI Koç</p>
          <p className="flex items-center gap-1.5 text-xs text-success">
            <span className="h-1.5 w-1.5 rounded-full bg-success" /> Çevrimiçi
          </p>
        </div>
        <button
          type="button"
          onClick={onOpenSettings}
          aria-label="Ayarlar"
          className="grid h-10 w-10 shrink-0 place-items-center rounded-full border border-border bg-surface text-muted-foreground active:scale-95"
        >
          <Settings2 size={18} />
        </button>
      </header>

      <div className="flex-1 space-y-3 py-5">
        {messages.map((m, i) => (
          <div key={i} className={m.role === 'user' ? 'flex justify-end' : 'flex justify-start'}>
            <div
              className={`max-w-[85%] rounded-2xl px-4 py-3 text-sm leading-relaxed ${
                m.role === 'user'
                  ? 'ember rounded-br-md'
                  : 'rounded-bl-md border border-border bg-surface'
              }`}
            >
              {m.text}
              {m.role === 'jarvis' && m.intent && m.intent !== 'chat' && (
                <span className="block text-[10px] font-mono uppercase tracking-wide text-primary-glow">
                  {m.intent.replace(/_/g, ' ')}
                </span>
              )}
            </div>
          </div>
        ))}

        {sending && (
          <div className="flex justify-start">
            <div className="rounded-2xl rounded-bl-md border border-border bg-surface px-4 py-3">
              <div className="flex items-center gap-1.5">
                <span className="h-1.5 w-1.5 rounded-full bg-primary animate-bounce [animation-delay:-0.3s]" />
                <span className="h-1.5 w-1.5 rounded-full bg-primary animate-bounce [animation-delay:-0.15s]" />
                <span className="h-1.5 w-1.5 rounded-full bg-primary animate-bounce" />
              </div>
            </div>
          </div>
        )}
        <div ref={chatEndRef} />
      </div>

      <div className="sticky bottom-24 -mx-5 px-5">
        <div className="no-scrollbar mb-2 flex gap-2 overflow-x-auto">
          {quick.map((q) => (
            <button
              key={q}
              type="button"
              onClick={() => send(q)}
              className="shrink-0 rounded-full border border-border bg-surface px-3.5 py-2 text-xs font-semibold text-muted-foreground"
            >
              {q}
            </button>
          ))}
        </div>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            send(input);
          }}
          className="surface-card flex items-center gap-2 p-2"
        >
          <input
            value={input}
            onChange={(e) => onInputChange(e.target.value)}
            placeholder="Koçuna bir şey sor..."
            className="h-11 min-w-0 flex-1 bg-transparent px-3 text-base outline-none placeholder:text-muted-foreground"
          />
          <button type="submit" aria-label="Gönder" className="ember grid h-11 w-11 shrink-0 place-items-center rounded-xl active:scale-95">
            <Send size={17} />
          </button>
        </form>
      </div>
    </main>
  );
}