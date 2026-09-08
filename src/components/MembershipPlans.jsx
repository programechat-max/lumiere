import { Check, Zap, Sparkles, Crown, ShieldCheck, ArrowRight, Table2, X } from 'lucide-react';

const MEMBERSHIP_PLANS = [
  {
    id: 'FREE',
    name: 'Free',
    badge: 'Başlangıç',
    price_try: 0,
    price_usd: 0,
    period: 'Süresiz',
    popular: false,
    color: 'neutral',
    icon: ShieldCheck,
    description: 'Temel fitness ve beslenme takibi için ideal başlangıç.',
    features: [
      'Temel Antrenman & Beslenme Günlüğü',
      'Standart Kalori ve Makro Hesaplama',
      'Aylık 1 Adet Yapay Zeka Planı',
      'Fotoğraftan Yemek Analizi (Temel)',
      'Mobil & Web Senkronizasyonu',
    ],
    limits: 'Günde 5 işlem',
  },
  {
    id: 'PRO',
    name: 'Pro',
    badge: 'En Popüler',
    price_try: 299,
    price_usd: 9.99,
    period: 'aylık',
    popular: true,
    color: 'red',
    icon: Zap,
    description: 'Lumiere AI koçu ile hipertrofi hedeflerine hızlı ulaş.',
    features: [
      'Lumiere AI Koç ile 7/24 Kesintisiz Sohbet',
      'Sınırsız Fotoğraftan Kalori & Makro Analizi',
      'Kişiselleştirilmiş Antrenman & Diyet Planı',
      'Haftalık Otomatik Gelişim Raporları',
      'Gelişmiş Makro & Kilo Takip Grafikleri',
    ],
    limits: 'Günde 50 AI işlemi',
  },
  {
    id: 'ELITE',
    name: 'Elite',
    badge: 'Gelişmiş Sporcu',
    price_try: 599,
    price_usd: 19.99,
    period: 'aylık',
    popular: false,
    color: 'emerald',
    icon: Sparkles,
    description: 'Fotoğraf ve video form analiziyle maksimum hipertrofi.',
    features: [
      'Pro\'daki Tüm Özellikler Dahil',
      'Fotoğraf & Videodan AI Hareket Form Analizi',
      'Postür, Simetri & Kas Gelişim Değerlendirmesi',
      'Anlık RPE ve Ağırlık Artış Progresyon Motoru',
      'Kas Isı Haritası & Akıllı Deload Yönetimi',
    ],
    limits: 'Günde 150 AI işlemi',
  },
  {
    id: 'ELITE_PLUS',
    name: 'Elite+',
    badge: 'VIP / Pro Koçluk',
    price_try: 999,
    price_usd: 39.99,
    period: 'aylık',
    popular: false,
    color: 'purple',
    icon: Crown,
    description: 'En üst düzey VIP deneyim ve öncelikli AI işlemci gücü.',
    features: [
      'Elite\'deki Tüm Özellikler Dahil',
      '7/24 Öncelikli Ultra Hızlı Lumiere Core Yanıtları',
      'Birebir Sesli Check-in & Sesli Koçluk Analitiği',
      'VIP Beslenme & Hassas Makro Optimizasyonu',
      'Özel Egzersiz Değişim & Sakatlık Önleme Motoru',
      'Öncelikli VIP Destek Hattı',
    ],
    limits: 'Sınırsız AI işlemi',
  },
];

// 4 planın TÜM özelliklerini tek tabloda karşılaştıran matris.
// Backend'deki billing_service.FEATURE_MATRIX ile tutarlı tutulur.
const COMPARISON_MATRIX = [
  { feature: 'Temel antrenman & beslenme günlüğü', values: [true, true, true, true] },
  { feature: 'Fotoğraftan kalori & makro hesaplayıcı', values: ['5/gün', 'Sınırsız', 'Sınırsız', 'Sınırsız'] },
  { feature: 'Lumiere AI koç ile sohbet', values: [false, true, true, 'Öncelikli + Ultra Hızlı'] },
  { feature: 'Kişiselleştirilmiş antrenman & diyet planı', values: ['Aylık 1', 'Sınırsız', 'Sınırsız', 'VIP optimizasyon'] },
  { feature: 'Haftalık gelişim raporu & grafikler', values: [false, true, true, true] },
  { feature: 'Fotoğraf & videodan hareket form analizi', values: [false, false, true, true] },
  { feature: 'Postür, simetri & kas dengesi değerlendirmesi', values: [false, false, true, true] },
  { feature: 'Kas ısı haritası & akıllı deload yönetimi', values: [false, false, true, true] },
  { feature: 'Birebir sesli check-in & sesli koçluk', values: [false, false, false, true] },
  { feature: 'Sakatlık önleme & egzersiz değişim motoru', values: [false, false, false, true] },
  { feature: 'Günlük AI işlem limiti', values: ['5', '50', '150', 'Sınırsız'] },
  { feature: 'Destek hattı', values: ['Topluluk', 'Standart', 'Öncelikli', 'VIP'] },
];

const PLAN_HEAD_STYLES = [
  'text-neutral-300',
  'text-red-400',
  'text-emerald-400',
  'text-purple-400',
];

function ComparisonTable() {
  return (
    <div className="w-full">
      <div className="flex items-center gap-2 mb-3 px-1">
        <Table2 className="w-4 h-4 text-neutral-500" />
        <h3 className="text-[10px] font-mono uppercase tracking-widest text-neutral-400">
          Planları Tek Tabloda Karşılaştır
        </h3>
      </div>
      <div className="overflow-x-auto rounded-lg border border-neutral-800/80 custom-scrollbar">
        <table className="w-full min-w-[460px] text-left border-collapse">
          <thead>
            <tr className="bg-neutral-900">
              <th className="px-1.5 py-1 text-[8px] font-mono uppercase tracking-wider text-neutral-500 border-b border-neutral-800">
                Özellik
              </th>
              {MEMBERSHIP_PLANS.map((plan, i) => (
                <th
                  key={plan.id}
                  className={`px-1.5 py-1 text-center text-[9px] font-mono font-medium border-b border-l border-neutral-800 ${PLAN_HEAD_STYLES[i]}`}
                >
                  {plan.name}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {COMPARISON_MATRIX.map((row, ri) => (
              <tr key={row.feature} className={ri % 2 === 0 ? 'bg-neutral-950/60' : 'bg-neutral-950/30'}>
                <td className="px-1.5 py-1 text-[10px] text-neutral-400 border-t border-neutral-800/60">{row.feature}</td>
                {row.values.map((val, vi) => (
                  <td
                    key={vi}
                    className={`px-1.5 py-1 text-center text-[9px] border-t border-l border-neutral-800/60 font-mono ${
                      vi === 0 ? 'text-neutral-500' : 'text-neutral-200'
                    }`}
                  >
                    {val === true ? (
                      <Check className={`w-3 h-3 mx-auto ${PLAN_HEAD_STYLES[vi]}`} strokeWidth={2.5} />
                    ) : val === false ? (
                      <X className="w-3 h-3 mx-auto text-neutral-700" />
                    ) : (
                      <span className={vi === 0 ? '' : 'text-[9px]'}>{val}</span>
                    )}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="text-[10px] text-neutral-600 font-mono mt-2 px-1">
        Tüm planlar taahhütsüzdür; istediğin zaman yükseltme, yenileme veya düşürme yapabilirsin.
      </p>
    </div>
  );
}

export default function MembershipPlans({
  selectedPlan = 'FREE',
  onSelectPlan,
  actionButtonLabel = 'Bu Planı Seç',
  isCurrentPlan = () => false,
  onUpgrade,
  loading = false,
  showComparison = true,
}) {
  return (
    <div className="w-full space-y-4">
      <div className="text-center max-w-2xl mx-auto space-y-2">
        <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-mono font-medium bg-red-500/10 text-red-400 border border-red-500/20">
          <Sparkles className="w-3.5 h-3.5" /> 4 Farklı Üyelik Seviyesi
        </span>
        <h2 className="text-xl sm:text-2xl font-bold font-mono tracking-tight text-white">
          Hedefine En Uygun <span className="text-red-500">Planı Seç</span>
        </h2>
        <p className="text-xs sm:text-sm text-neutral-400 font-sans">
          İstediğin zaman planını değiştirebilir veya yükseltebilirsin. Taahhüt yok.
        </p>
      </div>

      {/* 4 plan HER EKRAN BOYUTUNDA yan yana — kullanıcı kaydırmak zorunda kalmasın.
          Mobilde kartlar kompaktlaşır (ikon + isim + fiyat + buton), detaylar hemen
          altındaki karşılaştırma tablosunda sunulur. */}
      <div className="grid grid-cols-4 gap-1.5 sm:gap-4 items-stretch">
        {MEMBERSHIP_PLANS.map((plan) => {
          const isSelected = selectedPlan === plan.id;
          const isCurrent = isCurrentPlan(plan.id);
          const Icon = plan.icon;

          const borderStyle = isSelected
            ? 'border-red-500 ring-2 ring-red-500/30 bg-neutral-900/90 shadow-xl shadow-red-500/10'
            : plan.popular
            ? 'border-red-500/40 bg-neutral-900/60 hover:border-red-500/70'
            : 'border-neutral-800 bg-neutral-900/40 hover:border-neutral-700';

          return (
            <div
              key={plan.id}
              onClick={() => onSelectPlan && onSelectPlan(plan.id)}
              className={`relative rounded-2xl border p-5 flex flex-col justify-between transition-all duration-200 cursor-pointer ${borderStyle}`}
            >
              {plan.popular && (
                <div className="absolute -top-2 sm:-top-3 left-1/2 -translate-x-1/2 bg-gradient-to-r from-red-500 to-amber-500 text-black text-[7px] sm:text-[10px] font-bold font-mono uppercase tracking-widest px-1.5 sm:px-3 py-0.5 rounded-full shadow-md whitespace-nowrap">
                  {plan.badge}
                </div>
              )}

              <div>
                <div className="flex flex-col items-center gap-1.5 sm:flex-row sm:items-center sm:justify-between sm:gap-2 mb-2 sm:mb-3">
                  <div className={`w-7 h-7 sm:w-8 sm:h-8 rounded-lg flex items-center justify-center ${
                    plan.id === 'FREE' ? 'bg-neutral-800 text-neutral-300' :
                    plan.id === 'PRO' ? 'bg-red-500/10 text-red-400 border border-red-500/20' :
                    plan.id === 'ELITE' ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' :
                    'bg-purple-500/10 text-purple-400 border border-purple-500/20'
                  }`}>
                    <Icon className="w-3.5 h-3.5 sm:w-4 sm:h-4" />
                  </div>
                  <div className="text-center sm:text-left">
                    <h3 className="font-mono font-bold text-white text-xs sm:text-base leading-tight">{plan.name}</h3>
                    <span className="hidden sm:block text-[10px] font-mono text-neutral-500">{plan.badge}</span>
                  </div>
                </div>

                <div className="mb-2 sm:mb-4">
                  <div className="flex items-baseline justify-center sm:justify-start gap-1">
                    <span className="text-xs sm:text-base lg:text-lg font-normal font-mono text-neutral-100 whitespace-nowrap">
                      {plan.price_try === 0 ? 'Ücretsiz' : `${plan.price_try} ₺`}
                    </span>
                    {plan.price_try > 0 && (
                      <span className="text-[8px] sm:text-[10px] font-mono text-neutral-500">/{plan.period}</span>
                    )}
                  </div>
                  <p className="hidden sm:block text-xs text-neutral-400 mt-1 min-h-[32px] leading-relaxed">
                    {plan.description}
                  </p>
                </div>

                {/* Özellik listesi mobilde gizli — detaylar hemen altındaki karşılaştırma tablosunda */}
                <div className="hidden sm:block border-t border-neutral-800/80 pt-3 space-y-2 mb-6">
                  <p className="text-[10px] font-mono uppercase tracking-wider text-neutral-500 mb-2">Özellikler</p>
                  {plan.features.map((feat, idx) => (
                    <div key={idx} className="flex items-start gap-2 text-xs text-neutral-300">
                      <Check className={`w-3.5 h-3.5 shrink-0 mt-0.5 ${
                        plan.id === 'FREE' ? 'text-neutral-500' :
                        plan.id === 'PRO' ? 'text-red-400' :
                        plan.id === 'ELITE' ? 'text-emerald-400' : 'text-purple-400'
                      }`} strokeWidth={2.5} />
                      <span className="leading-snug">{feat}</span>
                    </div>
                  ))}
                </div>
              </div>

              <div className="pt-1 sm:pt-2">
                {isCurrent ? (
                  <div className="w-full py-1.5 sm:py-2.5 rounded-lg sm:rounded-xl bg-neutral-800 text-neutral-400 font-mono text-[9px] sm:text-xs font-bold text-center border border-neutral-700">
                    Mevcut Planınız
                  </div>
                ) : (
                  <button
                    type="button"
                    disabled={loading}
                    onClick={(e) => {
                      e.stopPropagation();
                      if (onUpgrade) onUpgrade(plan.id);
                      else if (onSelectPlan) onSelectPlan(plan.id);
                    }}
                    className={`w-full py-1.5 sm:py-2.5 px-1 sm:px-3 rounded-lg sm:rounded-xl font-mono text-[10px] sm:text-xs font-bold transition-all flex items-center justify-center gap-1 shadow-md ${
                      isSelected
                        ? 'bg-red-500 hover:bg-red-400 text-white shadow-red-500/20'
                        : 'bg-neutral-800 hover:bg-neutral-700 text-white border border-neutral-700 hover:border-neutral-600'
                    }`}
                  >
                    {isSelected ? (
                      <>
                        <span>Seçildi</span>
                        <Check className="w-3 h-3 sm:w-3.5 sm:h-3.5" />
                      </>
                    ) : (
                      <>
                        <span className="hidden sm:inline">{actionButtonLabel}</span>
                        <span className="sm:hidden">Seç</span>
                        <ArrowRight className="w-3 h-3 sm:w-3.5 sm:h-3.5" />
                      </>
                    )}
                  </button>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* Karşılaştırma tablosu — kartların HEMEN altında */}
      {showComparison && (
        <div className="mt-1 sm:mt-2">
          <ComparisonTable />
        </div>
      )}
    </div>
  );
}
