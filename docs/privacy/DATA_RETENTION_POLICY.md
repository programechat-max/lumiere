# Veri Saklama Politikası (PROMPT 11)

| Veri Kategorisi | Saklama Süresi | Silme Mekanizması |
|---|---|---|
| Hesap silme sonrası kişisel veri | 30 gün ödül süresi, sonra kalıcı silme | `AccountDeletionRequest` + `tasks.delete_account_task` |
| Aktif kullanıcı verisi (antrenman/beslenme/hafıza) | Hesap aktif olduğu sürece | Kullanıcı talebiyle (`/api/v1/privacy/delete-account`) |
| Fatura kayıtları (`Invoice`) | **7 yıl** (vergi/muhasebe yasal zorunluluğu) | Hesap silinse bile korunur, kullanıcıdan "koparılmaz" (anonimleştirilmez, çünkü denetim izi gerekli) |
| Audit log (`AuditLog`) | 1 yıl (öneri) | Periyodik arşivleme/temizlik görevi (henüz otomasyona bağlanmadı — takip görevi) |
| Push bildirim logları (`PushNotificationLog`) | 90 gün (öneri) | Periyodik temizlik görevi (takip görevi) |
| Onboarding video/ses (S3/yerel disk) | Analiz tamamlandıktan sonra 90 gün, sonra Glacier/silme | S3 lifecycle policy (bkz. `docs/AWS_SETUP.md` - S3 bucket lifecycle) |
| Veri dışa aktarma talepleri (`DataExportRequest`) | 30 gün (indirme linki geçerliliği) | Periyodik temizlik görevi (takip görevi) |
| Yedekler (S3 cross-region) | 30 gün minimum | Bulut sağlayıcı lifecycle politikası |

## Notlar

- Yukarıdaki "takip görevi" olarak işaretlenen otomatik temizlik cron job'ları
  şema/servis seviyesinde HAZIRDIR (`JobStatus`, `PushNotificationLog` vb.
  tabloların hepsinde `created_at` indeksli) ancak periyodik silme
  Celery Beat görevi olarak henüz zamanlanmadı — üretime çıkmadan önce
  eklenmesi önerilir (`tasks.py`'ye `purge_old_audit_logs_task` gibi bir
  görev eklemek yeterlidir).
- Fatura kayıtları asla otomatik silinmez (yasal risk).
