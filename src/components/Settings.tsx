import { useState } from 'react';
import { Bell, ChevronRight, Download, LogOut, MoonStar, ShieldCheck, Trash2, UserRound, X } from 'lucide-react';
import { Logo } from './chrome';
import type { Store } from '../lib/store';

export function SettingsSheet({ store, open, onClose, onLogout }: { store: Store; open: boolean; onClose: () => void; onLogout: () => void }) {
  const [name, setName] = useState(store.profile.name);
  const [notif, setNotif] = useState(true);
  if (!open) return null;
  const handleLogout = () => { void store.logout(); onLogout(); };
  return (
    <div className="fixed inset-0 z-50">
      <div className="absolute inset-0 bg-black/45 backdrop-blur-sm" onClick={onClose} />
      <div className="rise-in absolute inset-x-0 bottom-0 mx-auto max-h-[88dvh] w-full max-w-md overflow-y-auto rounded-t-[28px] bg-[#f4f1ec] p-6 pb-10 text-[#1c1512]">
        <div className="mx-auto mb-4 h-1.5 w-12 rounded-full bg-[#ddd0bd]" />
        <div className="flex items-center justify-between">
          <Logo />
          <button onClick={onClose} aria-label="Kapat" className="grid h-10 w-10 place-items-center rounded-full border border-[#e2d7c6] bg-white"><X size={18} /></button>
        </div>
        <p className="eyebrow mt-5 text-[#d92835]">Ayarlar</p>
        <h2 className="font-display mt-1 text-2xl font-extrabold">Profil & uygulama</h2>
        <div className="card-paper mt-4 rounded-3xl p-5">
          <p className="eyebrow text-[#b3a696]">Profil</p>
          <div className="mt-2.5 flex items-center gap-3">
            <span className="ember-btn grid h-12 w-12 shrink-0 place-items-center rounded-2xl"><UserRound size={22} /></span>
            <input value={name} onChange={(e) => setName(e.target.value)} className="h-12 min-w-0 flex-1 rounded-xl border border-[#e2d7c6] bg-white px-3 text-sm font-extrabold outline-none focus:border-[#d92835]" />
          </div>
          <button onClick={() => store.setProfile({ ...store.profile, name: name.trim() || store.profile.name })} className="mt-2.5 w-full rounded-xl bg-[#1c1512] py-3 text-sm font-extrabold text-white active:scale-[0.99]">İsmi kaydet</button>
          <div className="mt-3 grid grid-cols-2 gap-2 text-xs font-bold text-[#6f6259]">
            <div className="rounded-xl bg-[#f8f4ec] p-3">Hedef<br /><span className="text-[13px] font-extrabold text-[#1c1512]">{store.profile.goal}</span></div>
            <div className="rounded-xl bg-[#f8f4ec] p-3">Seviye<br /><span className="text-[13px] font-extrabold text-[#1c1512]">{store.profile.level}</span></div>
          </div>
        </div>
        <div className="card-paper mt-3 rounded-3xl p-2">
          {[
            { Icon: Bell, t: 'Bildirimler', d: notif ? 'Açık' : 'Kapalı', fn: () => setNotif((n) => !n) },
            { Icon: MoonStar, t: 'Karanlık tema', d: 'Yakında', fn: () => {} },
            { Icon: Download, t: 'Verilerimi indir', d: 'JSON', fn: () => {} },
            { Icon: ShieldCheck, t: 'Gizlilik', d: 'KVKK uyumlu', fn: () => {} },
          ].map((r) => (
            <button key={r.t} onClick={r.fn} className="flex w-full items-center gap-3 rounded-2xl px-3 py-3 text-left transition active:bg-[#f8f4ec]">
              <span className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-[#f1ece2] text-[#6f6259]"><r.Icon size={18} /></span>
              <span className="min-w-0 flex-1"><span className="block text-sm font-extrabold">{r.t}</span><span className="block text-[11px] font-semibold text-[#9a8c80]">{r.d}</span></span>
              <ChevronRight size={16} className="shrink-0 text-[#b3a696]" />
            </button>
          ))}
        </div>
        <button
          onClick={() => { ['lumiere.vitals.v1', 'lumiere.done.v1', 'lumiere.onboarded.v1', 'lumiere.streak.v1'].forEach((k) => localStorage.removeItem(k)); onClose(); }}
          className="mt-3 flex w-full items-center justify-center gap-2 rounded-2xl border border-[#f0c9c4] bg-[#fdeceb] py-3.5 text-sm font-extrabold text-[#8f1826]"
        >
          <Trash2 size={16} /> Yerel verileri sıfırla
        </button>
        <button onClick={handleLogout} className="mt-2.5 flex w-full items-center justify-center gap-2 rounded-2xl bg-[#1c1512] py-3.5 text-sm font-extrabold text-white">
          <LogOut size={16} /> Çıkış yap
        </button>
      </div>
    </div>
  );
}
