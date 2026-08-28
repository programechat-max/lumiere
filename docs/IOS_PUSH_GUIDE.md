# iOS APNs Push Bildirimleri Kurulum Kılavuzu (PROMPT 9)

## 1. Apple Developer Portal Adımları

1. **Keys** → **+** → "Apple Push Notifications service (APNs)" seçin,
   bir isim verin, kaydedin. İndirilen `AuthKey_XXXXXXXXXX.p8` dosyasını
   **güvenli** bir yere kaydedin (sadece bir kez indirilebilir).
2. Key ID'yi not edin (`APNS_KEY_ID`).
3. Apple Developer hesabınızın Team ID'sini not edin (`APNS_TEAM_ID`,
   Membership sayfasında).
4. Uygulamanızın Bundle Identifier'ı `APNS_BUNDLE_ID` olarak kullanılır
   (örn. `com.lumiere.coaching`).
5. `.p8` dosyasını sunucuya güvenli şekilde taşıyın (örn. secrets manager,
   ya da salt-okunur bir volume) ve yolunu `APNS_AUTH_KEY_PATH` olarak
   ayarlayın. **Bu dosyayı asla git'e commit etmeyin.**

## 2. Backend Ortam Değişkenleri

```bash
APNS_KEY_ID=ABC123DEFG
APNS_TEAM_ID=TEAM123456
APNS_AUTH_KEY_PATH=/secure/path/AuthKey_ABC123DEFG.p8
APNS_BUNDLE_ID=com.lumiere.coaching
APNS_USE_SANDBOX=true   # TestFlight/Development build'lerde true, App Store'da false
```

Bu değişkenler tanımlanana kadar `backend/apns_client.py::is_configured()`
`False` döner ve push gönderimleri sessizce `PushNotificationLog` tablosuna
`failed` olarak kaydedilir — uygulama çökmez.

## 3. Xcode / Capacitor Tarafı

1. Xcode'da proje hedefi → **Signing & Capabilities** → **+ Capability** →
   **Push Notifications** ekleyin.
2. Aynı sekmede **Background Modes** → **Remote notifications** işaretleyin.
3. `@capacitor/push-notifications` paketini kurun:
   ```bash
   npm install @capacitor/push-notifications
   npx cap sync ios
   ```
4. Uygulama açılışında izin isteyip token'ı yakalayın:
   ```js
   import { PushNotifications } from '@capacitor/push-notifications';

   async function registerForPush() {
     const perm = await PushNotifications.requestPermissions();
     if (perm.receive !== 'granted') return;
     await PushNotifications.register();
   }

   PushNotifications.addListener('registration', async (token) => {
     await fetch(`${API_BASE}/api/v1/notifications/devices`, {
       method: 'POST',
       headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${accessToken}` },
       body: JSON.stringify({ token: token.value, platform: 'ios' }),
     });
   });

   PushNotifications.addListener('pushNotificationActionPerformed', (action) => {
     const deepLink = action.notification?.data?.deep_link;
     if (deepLink) router.navigate(deepLink); // örn. /workout/active
   });
   ```
5. Logout'ta token'ı geri kaydırın:
   ```js
   await fetch(`${API_BASE}/api/v1/notifications/devices/${token}`, {
     method: 'DELETE',
     headers: { Authorization: `Bearer ${accessToken}` },
   });
   ```

## 4. Bildirim Tercihleri

Kullanıcılar `GET/PUT /api/v1/notifications/settings` ile şunları
yönetebilir: günlük check-in, antrenman hatırlatmaları, haftalık rapor,
hareketsizlik uyarıları, faturalandırma uyarıları, sessiz saatler
(`quiet_hours_start/end`) ve saat dilimi.

**Not:** Faturalandırma uyarıları (ödeme başarısız vb.) kritik kabul edilir
ve sessiz saatlerde bile gönderilir (bkz. `notification_service.dispatch_to_user`).

## 5. Test Etme

Sandbox modunda (development/TestFlight build) gerçek bir cihaza push
gönderebilmek için:
```bash
curl -X POST http://localhost:8000/api/v1/notifications/devices \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{"token": "<cihazdan gelen APNs token>", "platform": "ios"}'
```
Ardından `tasks.send_push_notification_task` görevini tetikleyecek bir
işlem yapın (örn. `/api/v1/jobs/weekly-analysis/generate`) veya doğrudan
Python konsolunda `notification_service.dispatch_to_user(...)` çağırın.

## 6. Token Yaşam Döngüsü

Apple `BadDeviceToken`/`Unregistered`/`DeviceTokenNotForTopic` hatası
döndürdüğünde ilgili `UserDeviceToken` kaydı otomatik silinir
(`apns_client.INVALID_TOKEN_REASONS`, `notification_service.prune_invalid_token`).
Kullanıcı tarafında hiçbir manuel işlem gerekmez.
