import { useCallback, useEffect, useState } from 'react';
import { Activity, Database, RefreshCw, Search, Server, Users, X } from 'lucide-react';
import { apiFetch } from '../services/apiClient';

function Status({ value }) {
  const ok = value === 'ok';
  return <span className={`text-[10px] font-mono ${ok ? 'text-emerald-400' : 'text-amber-400'}`}>{ok ? 'ÇALIŞIYOR' : String(value || 'BİLİNMİYOR').toUpperCase()}</span>;
}

export default function AdminPanel({ open, onClose }) {
  const [kpis, setKpis] = useState(null);
  const [health, setHealth] = useState(null);
  const [users, setUsers] = useState(null);
  const [query, setQuery] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const load = useCallback(async () => {
    setLoading(true); setError('');
    try {
      const [nextKpis, nextHealth, nextUsers] = await Promise.all([
        apiFetch('/api/v1/admin/analytics/kpis'),
        apiFetch('/api/v1/admin/system/health'),
        apiFetch(`/api/v1/admin/users?limit=25${query ? `&q=${encodeURIComponent(query)}` : ''}`),
      ]);
      setKpis(nextKpis); setHealth(nextHealth); setUsers(nextUsers);
    } catch (err) {
      setError(err?.message || 'Admin verileri yüklenemedi.');
    } finally { setLoading(false); }
  }, [query]);

  useEffect(() => {
    if (!open) return undefined;
    // Defer the initial network refresh one tick so opening the modal does not
    // synchronously cascade state updates during the effect commit.
    const refreshTimer = setTimeout(() => { void load(); }, 0);
    return () => clearTimeout(refreshTimer);
  }, [open, load]);
  if (!open) return null;

  return (
    <div className="admin-panel-overlay fixed inset-0 z-[70] bg-black/75 backdrop-blur-sm p-4 sm:p-8 overflow-y-auto">
      <div className="admin-panel-surface lp-column bg-[#121218] border border-white/[0.1] rounded-[28px] min-h-full p-5 sm:p-7 text-neutral-100 shadow-2xl shadow-black/50">
        <div className="flex items-center justify-between gap-3 mb-7">
          <div><p className="lp-section-kicker">Lumiere operations</p><h1 className="mt-1 text-2xl font-black tracking-[-0.06em]">Kontrol <span className="text-red-400">merkezi.</span></h1></div>
          <div className="flex gap-2"><button onClick={load} disabled={loading} className="p-2.5 rounded-xl border border-white/[0.1] bg-white/[0.035] text-neutral-400 hover:text-white hover:border-red-400/40"><RefreshCw className={loading ? 'w-4 h-4 animate-spin' : 'w-4 h-4'} /></button><button onClick={onClose} className="p-2.5 rounded-xl border border-white/[0.1] bg-white/[0.035] text-neutral-400 hover:text-white hover:border-red-400/40"><X className="w-4 h-4" /></button></div>
        </div>
        {error && <div className="mb-5 rounded-xl border border-red-500/30 bg-red-500/10 text-red-300 px-4 py-3 text-sm">{error}</div>}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-7">
          {[['Kullanıcı', kpis?.total_users ?? '—', Users], ['Aktif kullanıcı', kpis?.active_users ?? '—', Activity], ['Bekleyen AI işi', health?.pending_jobs ?? '—', Server], ['Son 24s hata', health?.failed_jobs_24h ?? '—', Database]].map(([label, value, Icon]) => <div key={label} className="border border-white/[0.09] rounded-2xl p-4 bg-white/[0.035]"><Icon className="w-4 h-4 text-red-300 mb-3" /><p className="text-2xl font-black tracking-[-0.05em]">{value}</p><p className="text-[10px] text-neutral-500 font-semibold uppercase tracking-wider">{label}</p></div>)}
        </div>
        <div className="grid lg:grid-cols-[1fr_1.4fr] gap-5">
          <section className="lp-panel"><h2 className="text-[11px] font-bold tracking-[.13em] text-neutral-400 uppercase mb-4">Sistem durumu</h2><div className="space-y-3 text-sm"><div className="flex justify-between"><span>PostgreSQL</span><Status value={health?.database?.status} /></div><div className="flex justify-between"><span>Redis</span><Status value={health?.redis?.status} /></div><div className="flex justify-between"><span>API</span><Status value="ok" /></div></div><p className="text-[11px] text-neutral-600 mt-5">Servis kapatma işlemleri bu panelden shell erişimiyle yapılmaz; yalnızca güvenli supervisor komutları eklenebilir.</p></section>
          <section className="lp-panel"><div className="flex items-center justify-between gap-3 mb-4"><h2 className="text-[11px] font-bold tracking-[.13em] text-neutral-400 uppercase">Kullanıcılar</h2><div className="relative"><Search className="absolute left-2.5 top-2.5 w-3.5 h-3.5 text-neutral-600" /><input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Ara..." className="bg-black/20 border border-white/[0.1] rounded-xl text-xs py-2 pl-8 pr-3 w-44 focus:outline-none focus:border-red-400" /></div></div><div className="space-y-2">{(users?.data || []).map((user) => <div key={user.id} className="flex items-center justify-between gap-3 border-t border-white/[0.07] py-2.5"><div><p className="text-sm">{user.full_name || 'İsimsiz'}</p><p className="text-[10px] text-neutral-500 font-mono">{user.email}</p></div><span className={`text-[10px] font-mono ${user.is_suspended ? 'text-red-400' : 'text-emerald-400'}`}>{user.is_suspended ? 'ASKIDA' : user.role}</span></div>)}</div></section>
        </div>
      </div>
    </div>
  );
}
