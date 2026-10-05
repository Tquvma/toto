"""Türkiye ve yakın çevresindeki büyük depremleri Discord kanalına bildirir.

Veri EMSC'den (Avrupa-Akdeniz Sismoloji Merkezi) gelir; API anahtarı gerekmez.
Gönderilen depremler quake_state.json'a yazılır, aynı deprem iki kez bildirilmez.

Ortam değişkenleri:
  DISCORD_WEBHOOK_URL  (zorunlu) Discord kanalının webhook adresi
  MIN_MAGNITUDE        (isteğe bağlı) Varsayılan 5.0
  TEST                 (isteğe bağlı) "true" ise son deprem eşiğe bakılmadan "TEST" olarak
                       gönderilir ve kaydedilmez (Discord bağlantısını denemek için)
  DRY_RUN              (isteğe bağlı) "1" ise gönderilmez, ekrana yazılır ve durum kaydedilmez
"""

import datetime
import json
import math
import os
import sys
import urllib.parse
import urllib.request
from zoneinfo import ZoneInfo

from weather_bot import env

EMSC_URL = "https://www.seismicportal.eu/fdsnws/event/1/query"
# Türkiye ve yakın çevresi (Ege, Kıbrıs, sınır bölgeleri)
REGION = {"minlat": 35.5, "maxlat": 42.5, "minlon": 25.5, "maxlon": 45.0}
# GitHub zamanlanmış görevleri gecikebildiği için geriye doğru geniş bakılır
LOOKBACK = datetime.timedelta(hours=6)
STATE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "quake_state.json")
USER_AGENT = "toto-quake-bot/1.0 (+https://github.com/Tquvma/toto)"
TURKEY_TZ = ZoneInfo("Europe/Istanbul")
BURSA = (40.1885, 29.0610)

# En yakın büyük şehri bulmak için (enlem, boylam)
CITIES = {
    "Adana": (37.0000, 35.3213), "Adıyaman": (37.7648, 38.2786), "Afyonkarahisar": (38.7507, 30.5567),
    "Ağrı": (39.7191, 43.0503), "Ankara": (39.9334, 32.8597), "Antalya": (36.8969, 30.7133),
    "Aydın": (37.8560, 27.8416), "Balıkesir": (39.6484, 27.8826), "Bingöl": (38.8847, 40.4939),
    "Bitlis": (38.4006, 42.1095), "Bolu": (40.7350, 31.6061), "Bursa": BURSA,
    "Çanakkale": (40.1553, 26.4142), "Çorum": (40.5506, 34.9556), "Denizli": (37.7765, 29.0864),
    "Diyarbakır": (37.9144, 40.2306), "Düzce": (40.8438, 31.1565), "Edirne": (41.6771, 26.5557),
    "Elazığ": (38.6810, 39.2264), "Erzincan": (39.7500, 39.5000), "Erzurum": (39.9043, 41.2679),
    "Eskişehir": (39.7767, 30.5206), "Gaziantep": (37.0662, 37.3833), "Hakkari": (37.5744, 43.7408),
    "Hatay": (36.2025, 36.1606), "Isparta": (37.7648, 30.5566), "İstanbul": (41.0082, 28.9784),
    "İzmir": (38.4237, 27.1428), "Kahramanmaraş": (37.5858, 36.9371), "Kars": (40.6013, 43.0975),
    "Kastamonu": (41.3887, 33.7827), "Kayseri": (38.7312, 35.4787), "Kocaeli": (40.7654, 29.9408),
    "Konya": (37.8746, 32.4932), "Kütahya": (39.4167, 29.9833), "Malatya": (38.3552, 38.3095),
    "Manisa": (38.6191, 27.4289), "Mardin": (37.3212, 40.7245), "Mersin": (36.8121, 34.6415),
    "Muğla": (37.2153, 28.3636), "Muş": (38.7432, 41.5065), "Osmaniye": (37.0742, 36.2478),
    "Sakarya": (40.7569, 30.3781), "Samsun": (41.2928, 36.3313), "Siirt": (37.9333, 41.9500),
    "Sivas": (39.7477, 37.0179), "Şanlıurfa": (37.1591, 38.7969), "Tekirdağ": (40.9781, 27.5115),
    "Tokat": (40.3167, 36.5500), "Trabzon": (41.0015, 39.7178), "Tunceli": (39.1079, 39.5401),
    "Uşak": (38.6823, 29.4082), "Van": (38.4891, 43.4089), "Yalova": (40.6500, 29.2667),
    "Zonguldak": (41.4564, 31.7987), "Lefkoşa": (35.1856, 33.3823),
}
DIRECTIONS = ["kuzeyi", "kuzeydoğusu", "doğusu", "güneydoğusu", "güneyi", "güneybatısı", "batısı", "kuzeybatısı"]


def distance_km(a, b):
    lat1, lon1, lat2, lon2 = map(math.radians, (*a, *b))
    h = math.sin((lat2 - lat1) / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2
    return 6371 * 2 * math.asin(math.sqrt(h))


def direction(origin, point):
    # origin'den point'e pusula yönü
    lat1, lon1, lat2, lon2 = map(math.radians, (*origin, *point))
    y = math.sin(lon2 - lon1) * math.cos(lat2)
    x = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(lon2 - lon1)
    bearing = (math.degrees(math.atan2(y, x)) + 360) % 360
    return DIRECTIONS[round(bearing / 45) % 8]


def genitive(name):
    # Tamlayan eki: Tekirdağ'ın, İzmir'in, Muş'un, Bingöl'ün, Lefkoşa'nın
    last_vowel = next(ch for ch in reversed(name.lower()) if ch in "aıoueiöü")
    suffix = {"a": "ın", "ı": "ın", "e": "in", "i": "in", "o": "un", "u": "un", "ö": "ün", "ü": "ün"}[last_vowel]
    if name[-1].lower() in "aıoueiöü":
        suffix = "n" + suffix
    return f"{name}'{suffix}"


def describe_location(point):
    city, center = min(CITIES.items(), key=lambda c: distance_km(c[1], point))
    km = distance_km(center, point)
    if km < 10:
        return f"{city} yakınları"
    return f"{genitive(city)} yaklaşık {km:.0f} km {direction(center, point)}"


def fetch_quakes(min_mag, now, lookback=LOOKBACK):
    params = {
        "format": "json",
        "start": (now - lookback).strftime("%Y-%m-%dT%H:%M:%S"),
        "minmag": min_mag,
        "orderby": "time-asc",
        **REGION,
    }
    req = urllib.request.Request(f"{EMSC_URL}?{urllib.parse.urlencode(params)}", headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=30) as resp:
        if resp.status == 204:  # sonuç yok
            return []
        return json.load(resp)["features"]


def build_embed(quake):
    p = quake["properties"]
    point = (p["lat"], p["lon"])
    when = datetime.datetime.fromisoformat(p["time"].replace("Z", "+00:00")).astimezone(TURKEY_TZ)
    mag = p["mag"]
    color = 0xD32F2F if mag >= 6 else 0xF57C00
    return {
        "title": f"🔴 M{mag:.1f} deprem – {describe_location(point)}",
        "url": f"https://www.seismicportal.eu/eventdetails.html?unid={p['unid']}",
        "color": color,
        "fields": [
            {"name": "Büyüklük", "value": f"{mag:.1f} ({p.get('magtype', '')})", "inline": True},
            {"name": "Derinlik", "value": f"{p['depth']:.0f} km", "inline": True},
            {"name": "Saat (TR)", "value": when.strftime("%d.%m.%Y %H:%M:%S"), "inline": True},
            {"name": "Bursa'ya uzaklık", "value": f"{distance_km(BURSA, point):.0f} km", "inline": True},
            {"name": "Bölge (EMSC)", "value": p.get("flynn_region", "-").title(), "inline": True},
            {"name": "Harita", "value": f"[Google Haritalar](https://www.google.com/maps?q={p['lat']},{p['lon']})", "inline": True},
        ],
        "footer": {"text": "Kaynak: EMSC · İlk ölçümdür, değerler güncellenebilir"},
    }


def send_discord(webhook_url, embeds):
    body = json.dumps({"username": "Deprem Bildirimi", "embeds": embeds}).encode()
    req = urllib.request.Request(
        webhook_url,
        data=body,
        # Discord, Python'un varsayılan User-Agent'ını reddedebiliyor
        headers={"Content-Type": "application/json", "User-Agent": USER_AGENT},
    )
    try:
        urllib.request.urlopen(req, timeout=30).close()
    except urllib.error.HTTPError as e:
        raise SystemExit(f"Discord hatası ({e.code}): {e.read().decode(errors='replace')}")


def load_state():
    try:
        with open(STATE_FILE) as f:
            return json.load(f)
    except FileNotFoundError:
        return {"sent": {}}


def save_state(state, now):
    # LOOKBACK'ten eski kayıtlar bir daha sorgulanmayacağı için silinir
    cutoff = (now - 2 * LOOKBACK).isoformat()
    state["sent"] = {k: v for k, v in state["sent"].items() if v >= cutoff}
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2, sort_keys=True)
        f.write("\n")


def send_test(webhook_url, now):
    # Son 7 gündeki en yeni depremi (büyüklüğüne bakmadan) TEST etiketiyle gönderir
    quakes = fetch_quakes(0, now, lookback=datetime.timedelta(days=7))
    if not quakes:
        sys.exit("Son 7 günde bölgede deprem bulunamadı.")
    embed = build_embed(quakes[-1])
    embed["title"] = "🧪 TEST – " + embed["title"]
    embed["footer"]["text"] = "Bu bir test mesajıdır · " + embed["footer"]["text"]
    if env("DRY_RUN") == "1":
        print(json.dumps(embed, indent=2, ensure_ascii=False))
        return
    send_discord(webhook_url, [embed])
    print("Test mesajı gönderildi.")


def main():
    now = datetime.datetime.now(datetime.timezone.utc)
    if env("TEST") == "true":
        send_test(env("DISCORD_WEBHOOK_URL"), now)
        return

    min_mag = float(env("MIN_MAGNITUDE", "5.0"))
    state = load_state()
    new = [q for q in fetch_quakes(min_mag, now) if q["id"] not in state["sent"]]
    if not new:
        print("Yeni deprem yok.")
        return

    embeds = [build_embed(q) for q in new]
    if env("DRY_RUN") == "1":
        print(json.dumps(embeds, indent=2, ensure_ascii=False))
        return

    webhook_url = env("DISCORD_WEBHOOK_URL")
    if not webhook_url:
        sys.exit("DISCORD_WEBHOOK_URL tanımlı olmalı.")
    # Discord tek mesajda en fazla 10 embed kabul ediyor
    for i in range(0, len(embeds), 10):
        send_discord(webhook_url, embeds[i : i + 10])

    for q in new:
        state["sent"][q["id"]] = q["properties"]["time"]
    save_state(state, now)
    print(f"{len(new)} deprem bildirildi.")


if __name__ == "__main__":
    main()
