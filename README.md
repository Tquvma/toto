# toto

Her sabah 06:10'da (Türkiye saati) Bursa ve Pattaya'nın günlük hava durumunu Telegram'a gönderen bot.
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
   - (İsteğe bağlı) *Variables* sekmesine `CITY` ekle; birden fazla şehir için virgülle ayır,
     örn. `Bursa, Pattaya, Ankara`. Varsayılan `Bursa, Pattaya`. Saatler her şehrin yerel saatidir.
4. **Dene:** **Actions → Günlük hava durumu → Run workflow** ile hemen bir mesaj gönder.

Workflow'un çalışması için bu dosyaların varsayılan dalda (`main`) olması gerekir.

## Kur botu

Döviz ve altın kurları, hava durumu botundan bağımsız **ikinci bir bottan** her sabah 10:00'da gelir:
dolar, euro, Tayland bahtı ve gram altın (TL), bir önceki güne göre değişimiyle.
Veri [fawazahmed0/exchange-api](https://github.com/fawazahmed0/exchange-api)'den gelir; API anahtarı gerekmez.
Gram altın ons fiyatından hesaplanır, kuyumcu fiyatından biraz farklı olabilir.

1. @BotFather'a `/newbot` yazıp ikinci bir bot oluştur (örn. "Kur Botu") ve token'ı al.
2. Yeni botu Telegram'da açıp **Başlat**'a bas.
3. Repo → **Settings → Secrets and variables → Actions** → `MARKETS_BOT_TOKEN` adıyla token'ı ekle.
   Chat ID olarak mevcut `TELEGRAM_CHAT_ID` kullanılır.
4. **Actions → Günlük kurlar → Run workflow** ile dene.

## Notlar

- GitHub zamanlanmış görevleri yoğunluğa göre birkaç dakika (bazen daha fazla) geç çalıştırabilir.
- Herkese açık repolarda 60 gün boyunca hiç commit olmazsa GitHub zamanlanmış görevleri durdurur;
  Actions sekmesinden tekrar etkinleştirebilirsin.
- Saati değiştirmek için `.github/workflows/daily-weather.yml` içindeki `cron` satırını düzenle
  (saat UTC'dir, Türkiye saatinden 3 çıkar).

## Yerelde çalıştırma

```bash
DRY_RUN=1 CITY=İzmir python3 weather_bot.py   # mesajı göndermeden ekrana yazar
DRY_RUN=1 python3 markets_bot.py
```
