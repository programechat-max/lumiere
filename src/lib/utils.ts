export function toISODate(d: Date): string {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${y}-${m}-${day}`;
}

export function todayISO(): string {
  return toISODate(new Date());
}

export function shiftISO(iso: string, deltaDays: number): string {
  const d = new Date(`${iso}T12:00:00`);
  d.setDate(d.getDate() + deltaDays);
  return toISODate(d);
}

export function formatDayLong(iso: string): string {
  try {
    return new Date(`${iso}T12:00:00`).toLocaleDateString('tr-TR', {
      weekday: 'long',
      day: 'numeric',
      month: 'long',
    });
  } catch {
    return iso;
  }
}

export function formatDayShort(iso: string): string {
  try {
    const d = new Date(`${iso}T12:00:00`);
    return d.toLocaleDateString('tr-TR', { day: 'numeric', month: 'short' });
  } catch {
    return iso;
  }
}

export function isToday(iso: string): boolean {
  return iso === todayISO();
}

export function isFuture(iso: string): boolean {
  return iso > todayISO();
}

export function dayLabelRelative(iso: string): string {
  const t = todayISO();
  if (iso === t) return 'Bugün';
  if (iso === shiftISO(t, -1)) return 'Dün';
  if (iso === shiftISO(t, 1)) return 'Yarın';
  return formatDayShort(iso);
}

export function formatMemberSince(iso: string | null): string | null {
  if (!iso) return null;
  try {
    const start = new Date(iso);
    if (Number.isNaN(start.getTime())) return null;
    const dayCount = Math.max(Math.floor((Date.now() - start.getTime()) / 86400000) + 1, 1);
    const dateLabel = start.toLocaleDateString('tr-TR', { day: 'numeric', month: 'short', year: 'numeric' });
    return `${dateLabel} · ${dayCount}. gün`;
  } catch {
    return null;
  }
}

export function uid(prefix = 'id'): string {
  return `${prefix}_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 8)}`;
}

export function stepsToKm(steps: number): number {
  return steps * 0.00072;
}

export function stepsToKcal(steps: number): number {
  return steps * 0.042;
}

// Deterministic pseudo-random (stable demo seed data)
export function mulberry32(seed: number): () => number {
  let a = seed >>> 0;
  return () => {
    a |= 0;
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}
