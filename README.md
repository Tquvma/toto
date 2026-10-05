# toto

Her sabah 06:10'da (Türkiye saati) günlük hava durumunu Telegram'a gönderen bot.
Hava durumu verisi [Open-Meteo](https://open-meteo.com)'dan gelir; API anahtarı gerekmez.
Zamanlamayı GitHub Actions yapar, sunucu gerekmez.

## Kurulum

1. **Bot oluştur:** Telegram'da [@BotFather](https://t.me/BotFather)'a `/newbot` yaz, adımları izle
   ve verilen **token**'ı kaydet.
2. **Chat ID'ni bul:** Yeni botuna herhangi bir mesaj at, sonra tarayıcıda şu adresi aç:
   `https://api.telegram.org/bot<TOKEN>/getUpdates`
   Çıkan yanıttaki `"chat":{"id": ...}` değeri senin chat ID'ndir.
3. **GitHub'a ekle:** Repo → **Settings → Secrets and variables → Actions**
   - *Secrets* sekmesine `TELEGRAM_BOT_TOKEN` ve `TELEGRAM_CHAT_ID` ekle.
   - (İsteğe bağlı) *Variables* sekmesine `CITY` ekle, örn. `Ankara`. Varsayılan `İstanbul`.
4. **Dene:** **Actions → Günlük hava durumu → Run workflow** ile hemen bir mesaj gönder.

Workflow'un çalışması için bu dosyaların varsayılan dalda (`main`) olması gerekir.

## Notlar

- GitHub zamanlanmış görevleri yoğunluğa göre birkaç dakika (bazen daha fazla) geç çalıştırabilir.
- Herkese açık repolarda 60 gün boyunca hiç commit olmazsa GitHub zamanlanmış görevleri durdurur;
  Actions sekmesinden tekrar etkinleştirebilirsin.
- Saati değiştirmek için `.github/workflows/daily-weather.yml` içindeki `cron` satırını düzenle
  (saat UTC'dir, Türkiye saatinden 3 çıkar).

## Yerelde çalıştırma

```bash
DRY_RUN=1 CITY=İzmir python3 weather_bot.py   # mesajı göndermeden ekrana yazar
```
