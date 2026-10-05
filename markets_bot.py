"""Günlük döviz ve altın kurlarını ayrı bir Telegram botuyla gönderir.

Ortam değişkenleri:
  MARKETS_BOT_TOKEN  (zorunlu) Kur botunun BotFather'dan alınan token'ı
  TELEGRAM_CHAT_ID   (zorunlu) Mesajın gideceği sohbet ID'si
  DRY_RUN            (isteğe bağlı) "1" ise mesaj gönderilmez, ekrana yazılır
"""

import datetime
import json
import sys
import urllib.error
import urllib.request

from weather_bot import env, send_telegram

# Ücretsiz, anahtarsız kur verisi: https://github.com/fawazahmed0/exchange-api
# {date} "latest" ya da "YYYY-MM-DD" olabilir; ikinci adres yedek
RATES_URLS = [
    "https://{date}.currency-api.pages.dev/v1/currencies/try.json",
    "https://cdn.jsdelivr.net/npm/@fawazahmed0/currency-api@{date}/v1/currencies/try.json",
]
GRAMS_PER_OUNCE = 31.1034768
# currency-api.pages.dev, Python'un varsayılan User-Agent'ını 403 ile reddediyor
USER_AGENT = "toto-markets-bot/1.0 (+https://github.com/Tquvma/toto)"

# (kod, etiket, ondalık basamak); "gram" ons altından hesaplanır
MARKETS = [
    ("usd", "💵 Dolar", 2),
    ("eur", "💶 Euro", 2),
    ("thb", "🇹🇭 Baht", 3),
    ("gram", "🥇 Gram altın", 0),
]


def fetch_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)


def get_rates(date="latest"):
    """1 birimin TL karşılığını döndürür: ("2026-10-05", {"usd": 49.1, ..., "gram": 6530})."""
    for url in RATES_URLS:
        try:
            data = fetch_json(url.format(date=date))
            break
        except (urllib.error.URLError, TimeoutError):
            if url == RATES_URLS[-1]:
                raise
    per_try = data["try"]
    rates = {code: 1 / per_try[code] for code in ("usd", "eur", "thb", "xau")}
    rates["gram"] = rates.pop("xau") / GRAMS_PER_OUNCE
    return data["date"], rates


def tr_number(value, decimals):
    # 6530.5 → "6.530,50" (Türkçe biçim)
    return f"{value:,.{decimals}f}".replace(",", "_").replace(".", ",").replace("_", ".")


def build_message(today, yesterday):
    lines = ["💰 Günaydın! Bugünün kurları", ""]
    for code, label, decimals in MARKETS:
        line = f"{label}: {tr_number(today[code], decimals)} ₺"
        if code in yesterday:
            change = (today[code] / yesterday[code] - 1) * 100
            arrow = "▲" if change > 0.005 else "▼" if change < -0.005 else "•"
            line += f" ({arrow} %{tr_number(abs(change), 2)})"
        lines.append(line)
    lines += ["", "Gram altın ons fiyatından hesaplanır; kuyumcu fiyatından farklı olabilir."]
    return "\n".join(lines)


def main():
    date, today = get_rates()
    # Önceki gün alınamazsa değişim yüzdeleri gösterilmez
    try:
        previous = datetime.date.fromisoformat(date) - datetime.timedelta(days=1)
        _, yesterday = get_rates(previous.isoformat())
    except Exception as e:
        print(f"Önceki günün kurları alınamadı: {e}", file=sys.stderr)
        yesterday = {}

    message = build_message(today, yesterday)

    if env("DRY_RUN") == "1":
        print(message)
        return

    token = env("MARKETS_BOT_TOKEN")
    chat_id = env("TELEGRAM_CHAT_ID")
    if not (token and chat_id):
        sys.exit("MARKETS_BOT_TOKEN ve TELEGRAM_CHAT_ID tanımlı olmalı.")
    send_telegram(token, chat_id, message)
    print("Mesaj gönderildi.")


if __name__ == "__main__":
    main()
