"""Günlük hava durumunu Open-Meteo'dan alıp Telegram'a gönderen bot.

Ortam değişkenleri:
  TELEGRAM_BOT_TOKEN  (zorunlu) BotFather'dan alınan token
  TELEGRAM_CHAT_ID    (zorunlu) Mesajın gideceği sohbet ID'si
  CITY                (isteğe bağlı) Şehir adı, varsayılan "Bursa"
  LATITUDE/LONGITUDE  (isteğe bağlı) Verilirse şehir araması yapılmaz
  TIMEZONE            (isteğe bağlı) Varsayılan "Europe/Istanbul"
  DRY_RUN             (isteğe bağlı) "1" ise mesaj gönderilmez, ekrana yazılır
"""

import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
TELEGRAM_URL = "https://api.telegram.org/bot{token}/sendMessage"

# WMO hava durumu kodları: https://open-meteo.com/en/docs
WEATHER_CODES = {
    0: ("☀️", "Açık"),
    1: ("🌤️", "Çoğunlukla açık"),
    2: ("⛅", "Parçalı bulutlu"),
    3: ("☁️", "Kapalı"),
    45: ("🌫️", "Sisli"),
    48: ("🌫️", "Kırağılı sis"),
    51: ("🌦️", "Hafif çisenti"),
    53: ("🌦️", "Çisenti"),
    55: ("🌦️", "Yoğun çisenti"),
    56: ("🌧️", "Hafif dondurucu çisenti"),
    57: ("🌧️", "Dondurucu çisenti"),
    61: ("🌧️", "Hafif yağmur"),
    63: ("🌧️", "Yağmur"),
    65: ("🌧️", "Kuvvetli yağmur"),
    66: ("🌧️", "Hafif dondurucu yağmur"),
    67: ("🌧️", "Dondurucu yağmur"),
    71: ("🌨️", "Hafif kar"),
    73: ("🌨️", "Kar"),
    75: ("❄️", "Yoğun kar"),
    77: ("🌨️", "Kar taneleri"),
    80: ("🌦️", "Hafif sağanak"),
    81: ("🌧️", "Sağanak"),
    82: ("⛈️", "Şiddetli sağanak"),
    85: ("🌨️", "Hafif kar sağanağı"),
    86: ("❄️", "Yoğun kar sağanağı"),
    95: ("⛈️", "Gök gürültülü fırtına"),
    96: ("⛈️", "Hafif dolulu fırtına"),
    99: ("⛈️", "Şiddetli dolulu fırtına"),
}


def http_get_json(url, params, attempts=3):
    full_url = f"{url}?{urllib.parse.urlencode(params)}"
    for attempt in range(1, attempts + 1):
        try:
            with urllib.request.urlopen(full_url, timeout=30) as resp:
                return json.load(resp)
        except (urllib.error.URLError, TimeoutError):
            if attempt == attempts:
                raise
            time.sleep(5 * attempt)


def find_city(name):
    data = http_get_json(GEOCODING_URL, {"name": name, "count": 1, "language": "tr"})
    results = data.get("results")
    if not results:
        raise SystemExit(f"Şehir bulunamadı: {name}")
    city = results[0]
    return city["name"], city["latitude"], city["longitude"]


def get_forecast(lat, lon, timezone):
    return http_get_json(
        FORECAST_URL,
        {
            "latitude": lat,
            "longitude": lon,
            "timezone": timezone,
            "forecast_days": 1,
            "current": "temperature_2m,apparent_temperature,weather_code",
            "daily": ",".join(
                [
                    "weather_code",
                    "temperature_2m_max",
                    "temperature_2m_min",
                    "precipitation_probability_max",
                    "precipitation_sum",
                    "wind_speed_10m_max",
                    "sunrise",
                    "sunset",
                ]
            ),
        },
    )


def describe(code):
    return WEATHER_CODES.get(code, ("🌡️", "Bilinmiyor"))


def advice(daily):
    tips = []
    rain_chance = daily["precipitation_probability_max"][0] or 0
    if rain_chance >= 50:
        tips.append("☂️ Şemsiyeni almayı unutma.")
    if daily["temperature_2m_min"][0] <= 5:
        tips.append("🧥 Sıkı giyin, hava soğuk.")
    elif daily["temperature_2m_max"][0] >= 30:
        tips.append("🧴 Sıcak bir gün, bol su iç.")
    if daily["wind_speed_10m_max"][0] >= 40:
        tips.append("💨 Kuvvetli rüzgar bekleniyor.")
    return tips


def build_message(city, forecast):
    current = forecast["current"]
    daily = forecast["daily"]
    emoji, text = describe(daily["weather_code"][0])
    now_emoji, now_text = describe(current["weather_code"])

    lines = [
        f"🌅 Günaydın! {city} için bugünün hava durumu",
        "",
        f"{emoji} {text}",
        f"🌡️ En düşük {daily['temperature_2m_min'][0]:.0f}°C / "
        f"en yüksek {daily['temperature_2m_max'][0]:.0f}°C",
        f"{now_emoji} Şu an {current['temperature_2m']:.0f}°C, "
        f"hissedilen {current['apparent_temperature']:.0f}°C ({now_text.lower()})",
        f"💧 Yağış ihtimali %{daily['precipitation_probability_max'][0] or 0}"
        f" ({daily['precipitation_sum'][0]:.1f} mm)",
        f"💨 Rüzgar en fazla {daily['wind_speed_10m_max'][0]:.0f} km/s",
        f"🌄 Gün doğumu {daily['sunrise'][0][-5:]}, gün batımı {daily['sunset'][0][-5:]}",
    ]
    tips = advice(daily)
    if tips:
        lines += [""] + tips
    return "\n".join(lines)


def send_telegram(token, chat_id, text):
    body = json.dumps({"chat_id": chat_id, "text": text}).encode()
    req = urllib.request.Request(
        TELEGRAM_URL.format(token=token),
        data=body,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.load(resp)
    except urllib.error.HTTPError as e:
        # Telegram hatanın nedenini yanıt gövdesinde açıklıyor
        detail = e.read().decode(errors="replace")
        raise SystemExit(f"Telegram hatası ({e.code}): {detail}")
    if not result.get("ok"):
        raise SystemExit(f"Telegram hatası: {result}")


def env(name, default=None):
    # Secret'lar yapıştırılırken sona boşluk/satır sonu eklenebiliyor
    return (os.environ.get(name) or "").strip() or default


def main():
    timezone = env("TIMEZONE", "Europe/Istanbul")
    city = env("CITY", "Bursa")
    lat = env("LATITUDE")
    lon = env("LONGITUDE")
    if not (lat and lon):
        city, lat, lon = find_city(city)

    message = build_message(city, get_forecast(lat, lon, timezone))

    if env("DRY_RUN") == "1":
        print(message)
        return

    token = env("TELEGRAM_BOT_TOKEN")
    chat_id = env("TELEGRAM_CHAT_ID")
    if not (token and chat_id):
        sys.exit("TELEGRAM_BOT_TOKEN ve TELEGRAM_CHAT_ID tanımlı olmalı.")
    send_telegram(token, chat_id, message)
    print("Mesaj gönderildi.")


if __name__ == "__main__":
    main()
