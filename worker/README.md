# /hava komutu (Cloudflare Worker)

Telegram'da botuna `/hava` yazınca anında hava durumunu gönderir. Ücretsiz Cloudflare Workers
üzerinde çalışır; sunucu veya açık bilgisayar gerekmez. Her sabahki otomatik mesaj bundan
bağımsız olarak GitHub Actions'ta çalışmaya devam eder.

| Komut | Ne yapar |
| --- | --- |
| `/hava` | Varsayılan şehirler (Bursa, Pattaya) |
| `/hava İzmir` | İstediğin şehir |
| `/hava Bursa, Antalya` | Birden fazla şehir (en fazla 5) |
| `/start` | Yardım mesajı |

## Kurulum (yaklaşık 10 dakika, tamamen tarayıcıdan)

1. **Cloudflare hesabı aç:** <https://dash.cloudflare.com/sign-up> (ücretsiz plan yeterli).
2. **Worker oluştur:** Sol menüden **Compute (Workers) → Workers & Pages → Create → Create Worker**.
   Adını `hava-botu` yap ve **Deploy**'a bas.
3. **Kodu yapıştır:** **Edit code**'a bas, editördeki her şeyi sil, bu klasördeki
   [`worker.js`](worker.js) dosyasının tamamını yapıştır ve **Deploy**'a bas.
4. **Ayarları ekle:** Worker sayfasında **Settings → Variables and Secrets → Add**:
   - `WEBHOOK_SECRET` (tür: **Secret**): kendin uydurduğun uzun bir parola. Sadece harf, rakam,
     `_` ve `-` kullan, örn. `hava_bot_9f3k2LmQ71`.
   - `ALLOWED_CHAT_ID` (tür: **Text**): senin chat ID'n (GitHub'a girdiğin sayı). Bunu eklersen
     bot sadece sana cevap verir; eklemezsen botu bulan herkes kullanabilir.
   - (İsteğe bağlı) `CITY` (tür: **Text**): `/hava` için varsayılan şehirler, örn. `Bursa, Pattaya`.

   Kaydet / **Deploy**'a bas.
5. **Worker adresini kopyala:** Worker sayfasının üstünde
   `https://hava-botu.<kullanıcı-adın>.workers.dev` gibi bir adres var. Tarayıcıda açınca
   "Hava durumu botu çalışıyor." yazmalı.
6. **Telegram'ı Worker'a bağla:** Aşağıdaki adresi kendi değerlerinle doldurup tarayıcıda aç:

   ```
   https://api.telegram.org/bot<TOKEN>/setWebhook?url=<WORKER_ADRESİ>&secret_token=<WEBHOOK_SECRET>
   ```

   Yanıt `{"ok":true,"result":true,"description":"Webhook was set"}` olmalı.
7. **(İsteğe bağlı) Komut menüsü:** @BotFather'a `/setcommands` yaz, botunu seç ve şunu gönder:

   ```
   hava - Hava durumu
   ```

   Böylece Telegram'da `/` yazınca `/hava` önerilir.
8. **Dene:** Botuna `/hava` yaz.

## Sorun giderme

- **Cevap gelmiyor:** Tarayıcıda `https://api.telegram.org/bot<TOKEN>/getWebhookInfo` adresini aç.
  `last_error_message` alanı sorunu söyler. `401` görüyorsan `WEBHOOK_SECRET` ile setWebhook'taki
  `secret_token` aynı değildir.
- **Kodu güncelledim:** `worker.js` değişince Cloudflare'de **Edit code**'a girip yeni hâlini
  yapıştırman ve **Deploy**'a basman yeterli; webhook'u tekrar kurman gerekmez.
