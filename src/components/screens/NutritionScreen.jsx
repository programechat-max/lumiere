import { Camera, Check, ChevronRight, Flame, Sparkles, Trash2, UtensilsCrossed, X } from 'lucide-react';
import PageHeader from '../lumiere/PageHeader';

/**
 * Beslenme ekranı — love repo `src/routes/app.nutrition.tsx` tasarımı.
 * Veriler gerçek backend'den gelir (App.jsx çekiyor):
 * nutritionPlans: /api/nutrition · mealPlan: /api/mealplan
 * Foto analizi: POST /api/nutrition/photo + /api/nutrition/photo/confirm
 * AI plan: POST /api/mealplan/generate · DELETE /api/mealplan
 */
export default function NutritionScreen({
  nutritionPlans,
  mealPlan,
  generatingPlan,
  onRegenerateMealPlan,
  onDeleteMealPlan,
  foodPhotoPreview,
  foodPhotoAnalyzing,
  foodPhotoError,
  foodPhotoInputRef,
  onFileSelect,
  onConfirmPhoto,
  onCancelPhoto,
  profile,
}) {
  const logs = nutritionPlans || [];
  const plan = mealPlan || [];

  const consumedCal = logs.reduce((s, m) => s + (m.calories || 0), 0);
  const consumedProt = logs.reduce((s, m) => s + (m.target_protein ?? m.protein ?? 0), 0);
  const targetCal = profile?.daily_calorie_target || 2200;
  const targetProt = profile?.daily_protein_target || 140;
  const planCal = plan.reduce((s, m) => s + (m.calories || 0), 0);
  const planProt = plan.reduce((s, m) => s + (m.protein || 0), 0);

  return (
    <main>
      <PageHeader eyebrow="Beslenme takibi" title="Beslenme" showSettings={false} />

      {/* Kalori özeti */}
      <section className="surface-card relative overflow-hidden p-5">
        <div className="hero-bg absolute inset-0 opacity-90" aria-hidden />
        <div className="relative">
          <p className="eyebrow text-primary-glow">Bugünün özeti</p>
          <div className="mt-2 grid grid-cols-[minmax(0,1fr)_auto] items-end gap-2">
            <p className="text-3xl font-extrabold leading-none">
              {Math.round(consumedCal)}
              <span className="text-base font-semibold text-muted-foreground"> / {targetCal} kcal</span>
            </p>
            <span className="rounded-full bg-success/15 px-3 py-1.5 text-xs font-bold text-success">
              {Math.round(consumedProt)} / {targetProt} g protein
            </span>
          </div>
          <div className="mt-4 h-2 overflow-hidden rounded-full bg-secondary">
            <div
              className="ember h-full rounded-full transition-all duration-500"
              style={{ width: `${Math.min((consumedCal / targetCal) * 100, 100)}%` }}
            />
          </div>
        </div>
      </section>

      {/* Foto ile öğün ekle */}
      <section className="surface-card mt-4 p-5">
        <div className="grid grid-cols-[auto_minmax(0,1fr)] items-center gap-3">
          <span className="grid h-11 w-11 shrink-0 place-items-center rounded-2xl bg-success/15 text-success">
            <Camera size={19} />
          </span>
          <div className="min-w-0">
            <p className="truncate text-sm font-bold">Fotoğraftan öğün ekle</p>
            <p className="truncate text-xs text-muted-foreground">Makroları otomatik bul</p>
          </div>
        </div>

        <input
          ref={foodPhotoInputRef}
          type="file"
          accept="image/*"
          className="hidden"
          onChange={(e) => {
            if (e.target.files?.[0]) onFileSelect?.(e.target.files[0]);
            e.target.value = '';
          }}
        />

        <button
          type="button"
          onClick={() => foodPhotoInputRef?.current?.click()}
          disabled={foodPhotoAnalyzing}
          className="ember ember-glow mt-4 flex h-12 w-full items-center justify-center gap-2 rounded-xl text-sm font-bold active:scale-[0.99] disabled:opacity-60"
        >
          {foodPhotoAnalyzing ? (
            <>
              <span className="h-4 w-4 animate-spin rounded-full border-2 border-background border-t-transparent" />
              Analiz ediliyor...
            </>
          ) : (
            <>
              <Camera size={16} /> Fotoğraf seç
            </>
          )}
        </button>

        {foodPhotoError && (
          <p className="mt-3 rounded-xl border border-warning/40 bg-warning/10 px-3 py-2 text-xs font-semibold text-warning">
            {foodPhotoError}
          </p>
        )}

        {foodPhotoPreview && (
          <div className="mt-4 rounded-2xl border border-border bg-surface p-4">
            <div className="grid grid-cols-[auto_minmax(0,1fr)] items-start gap-3">
              {foodPhotoPreview.previewUrl && (
                <img
                  src={foodPhotoPreview.previewUrl}
                  alt="Öğün"
                  className="h-16 w-16 shrink-0 rounded-xl object-cover"
                />
              )}
              <div className="min-w-0">
                <p className="truncate text-sm font-bold">{foodPhotoPreview.meal_name}</p>
                <p className="truncate text-xs text-muted-foreground">
                  {Math.round(foodPhotoPreview.calories || 0)} kcal · P {Math.round(foodPhotoPreview.protein || 0)} · K {Math.round(foodPhotoPreview.carbs || 0)} · Y {Math.round(foodPhotoPreview.fats || 0)}
                </p>
              </div>
            </div>
            <div className="mt-3 grid grid-cols-2 gap-2">
              <button
                type="button"
                onClick={onConfirmPhoto}
                className="ember flex h-11 items-center justify-center gap-1.5 rounded-xl text-sm font-bold active:scale-[0.98]"
              >
                <Check size={15} /> Kaydet
              </button>
              <button
                type="button"
                onClick={onCancelPhoto}
                className="flex h-11 items-center justify-center gap-1.5 rounded-xl border border-border text-sm font-bold text-muted-foreground active:scale-[0.98]"
              >
                <X size={15} /> İptal
              </button>
            </div>
          </div>
        )}
      </section>

      {/* Bugünün kayıtları */}
      <section className="surface-card mt-4 p-5">
        <div className="mb-3 grid grid-cols-[auto_minmax(0,1fr)_auto] items-center gap-2">
          <span className="grid h-9 w-9 place-items-center rounded-xl bg-primary/15 text-primary-glow">
            <UtensilsCrossed size={16} />
          </span>
          <p className="eyebrow text-muted-foreground">Bugünün kayıtları</p>
          <span className="rounded-full bg-secondary px-2.5 py-1 text-[11px] font-bold">{logs.length}</span>
        </div>
        {logs.length === 0 && (
          <p className="py-3 text-center text-xs text-muted-foreground">Henüz öğün kaydı yok.</p>
        )}
        <div className="space-y-2">
          {logs.map((m, i) => (
            <div key={m.id ?? i} className="flex items-center gap-3 rounded-xl border border-border bg-surface px-3.5 py-2.5">
              <span className="grid h-8 w-8 shrink-0 place-items-center rounded-lg bg-primary/15 text-primary-glow">
                <Flame size={14} />
              </span>
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm font-bold">{m.meal_name}</p>
                <p className="truncate text-xs text-muted-foreground">
                  P {Math.round(m.target_protein ?? m.protein ?? 0)} · K {Math.round(m.target_carbs ?? m.carbs ?? 0)} · Y {Math.round(m.target_fat ?? m.fats ?? 0)}
                </p>
              </div>
              <span className="shrink-0 text-sm font-extrabold">{Math.round(m.calories || 0)}</span>
            </div>
          ))}
        </div>
      </section>

      {/* AI öğün planı */}
      <section className="surface-card mt-4 p-5">
        <div className="grid grid-cols-[auto_minmax(0,1fr)_auto] items-center gap-2">
          <span className="grid h-9 w-9 place-items-center rounded-xl bg-success/15 text-success">
            <Sparkles size={16} />
          </span>
          <p className="eyebrow text-muted-foreground">AI öğün planı</p>
          {plan.length > 0 && (
            <button
              type="button"
              onClick={onDeleteMealPlan}
              aria-label="Planı sil"
              className="grid h-8 w-8 place-items-center rounded-lg border border-border text-muted-foreground active:scale-95"
            >
              <Trash2 size={14} />
            </button>
          )}
        </div>

        {plan.length === 0 ? (
          <p className="py-3 text-center text-xs text-muted-foreground">
            Koçun sana özel günlük bir öğün planı oluşturabilir.
          </p>
        ) : (
          <>
            <p className="mt-2 text-xs text-muted-foreground">
              Toplam: ~{Math.round(planCal)} kcal · {Math.round(planProt)} g protein
            </p>
            <div className="mt-3 space-y-2">
              {plan.map((m, i) => (
                <button
                  key={m.id ?? i}
                  type="button"
                  className="flex w-full items-center gap-3 rounded-xl border border-border bg-surface px-3.5 py-2.5 text-left"
                >
                  <span className="grid h-8 w-8 shrink-0 place-items-center rounded-lg bg-success/15 text-success">
                    <Flame size={14} />
                  </span>
                  <span className="min-w-0 flex-1">
                    <span className="block truncate text-sm font-bold">
                      {m.meal_name}{m.time_target ? ` · ${m.time_target}` : ''}
                    </span>
                    <span className="block truncate text-xs text-muted-foreground">
                      {m.description || `${Math.round(m.calories || 0)} kcal · P ${Math.round(m.protein || 0)}`}
                    </span>
                  </span>
                  <span className="shrink-0 text-sm font-extrabold">{Math.round(m.calories || 0)}</span>
                  <ChevronRight size={15} className="shrink-0 text-muted-foreground" />
                </button>
              ))}
            </div>
          </>
        )}

        <button
          type="button"
          onClick={onRegenerateMealPlan}
          disabled={generatingPlan}
          className="ember ember-glow mt-4 flex h-12 w-full items-center justify-center gap-2 rounded-xl text-sm font-bold active:scale-[0.99] disabled:opacity-60"
        >
          {generatingPlan ? (
            <>
              <span className="h-4 w-4 animate-spin rounded-full border-2 border-background border-t-transparent" />
              Plan oluşturuluyor...
            </>
          ) : (
            <>
              <Sparkles size={16} /> {plan.length > 0 ? 'Yeni plan oluştur' : 'AI ile plan oluştur'}
            </>
          )}
        </button>
      </section>
    </main>
  );
}
