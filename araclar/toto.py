#!/usr/bin/env python3
"""Spor Toto haftalik analiz araci (sadece standart kutuphane).

Komutlar:
  program [--sezon 2026/2027 --hafta 8] [--yaz]   Haftanin 15 macini gosterir, --yaz ile haftalar/<sezon>_<hafta>.json iskeletini olusturur
  elo     <hafta.json>                             Milli takim maclari icin Elo modeli olasiliklari (eloratings.net)
  oranlar <hafta.json> [--statsbet]                Nesine (ve istenirse statsbet: Pinnacle/1xBet) oranlari -> marjsiz olasilik
  kupon   <hafta.json>                             JSON'daki kuponlarin kolon sayisi, maliyet ve 12/13/14/15 olasiliklari
  oner    <hafta.json> --kolon 96 [--hedef 13]     Kolon butcesinde "en az hedef kadar bilme" olasiligini maksimize eden sistem
          <hafta.json> --hedef 13 --tara           Ayni hedef icin 12-1152 kolon arasi butce tablosu
  sonuc   <hafta.json>                             Resmi sonuclari ceker, tahmin/kupon isabetini ve ikramiyeleri yazar
  halk    <hafta.json>                             Nesine'deki "% Tercih" (halkin oynama yuzdeleri) -> m["halk"]
  kazanc  <hafta.json> [--kolon 2500 --havuz 75e6 --kolon-sayisi 15e6 --devir 0 --ara]
                                                   Paylasimli ikramiye modeliyle kuponlarin beklenen kazanci ve kar olasiligi;
                                                   --ara ile kolon siniri icinde beklenen kari en yuksek kuponu arar

Olasilik onceligi: "final" (bizim nihai karar) > "piyasa" > "elo".
Sonuc gosterimi Spor Toto'daki gibi: 1 = ev sahibi, 0 = beraberlik, 2 = deplasman.
"""
import argparse
import datetime
import difflib
import gzip
import json
import math
import os
import random
import re
import sys
import unicodedata
import urllib.request

sys.stdout.reconfigure(encoding="utf-8")

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HAFTALAR = os.path.join(KOK, "haftalar")
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0 Safari/537.36"
TOTO_API = "https://webapi.sportoto.gov.tr/"
NESINE = "https://bulten.nesine.com/api/bulten/getprebultenfull"
NESINE_TOTO = "https://st.nesine.com/v2/Program"  # aktif Spor Toto programi + percentage1/0/2 (% Tercih)
HAVUZ_PAYI = {15: 0.35, 14: 0.20, 13: 0.20, 12: 0.25}  # resmi oyun plani
KOLON_BEDELI = 10.0  # TL (Mart 2025'ten beri). Kuponda dogrula, degistiyse burayi guncelle.
MAKS_KOLON = 2500  # resmi oyun plani: bir bilette en fazla 2.500 kolon

# Elo -> 1/0/2 siralı lojistik model. UEFA takimlarinin 2010+ resmi ev sahibi maclarindan (n=2769) fit edildi:
# z = A*(Elo farki/100) + B*ev ; P(1)=s(z-C), P(2)=s(-z-C), P(0)=kalan
ELO_A, ELO_B, ELO_C = 0.5261, 0.3376, 0.6546

TURNUVA = {70: "Süper Lig", 258: "UEFA Uluslar Ligi", 32: "Premier Lig", 36: "Premier Lig", 44: "La Liga",
           56: "Serie A", 6: "Bundesliga", 9: "Bundesliga", 26: "Ligue 1", 28: "Ligue 1"}

# Spor Toto'daki Turkce milli takim adi -> eloratings.net Ingilizce adi
TR2EN = {
    "Türkiye": "Turkey", "Belçika": "Belgium", "İtalya": "Italy", "Fransa": "France", "Bosna Hersek": "Bosnia and Herzegovina",
    "İsveç": "Sweden", "Macaristan": "Hungary", "Gürcistan": "Georgia", "Polonya": "Poland", "Romanya": "Romania",
    "Hırvatistan": "Croatia", "İngiltere": "England", "Kuzey Makedonya Cumhuriyeti": "North Macedonia",
    "Kuzey Makedonya": "North Macedonia", "İskoçya": "Scotland", "İspanya": "Spain", "Çekya": "Czechia",
    "Çek Cumhuriyeti": "Czechia", "İsviçre": "Switzerland", "Slovenya": "Slovenia", "Galler": "Wales",
    "Danimarka": "Denmark", "Hollanda": "Netherlands", "Sırbistan": "Serbia", "Portekiz": "Portugal", "Norveç": "Norway",
    "Yunanistan": "Greece", "Almanya": "Germany", "Avusturya": "Austria", "Kosova": "Kosovo", "İrlanda": "Ireland",
    "İrlanda Cumhuriyeti": "Ireland", "Kuzey İrlanda": "Northern Ireland", "İsrail": "Israel", "Ukrayna": "Ukraine",
    "Slovakya": "Slovakia", "Arnavutluk": "Albania", "Bulgaristan": "Bulgaria", "Lüksemburg": "Luxembourg",
    "Litvanya": "Lithuania", "Azerbaycan": "Azerbaijan", "Letonya": "Latvia", "Estonya": "Estonia", "Finlandiya": "Finland",
    "İzlanda": "Iceland", "Karadağ": "Montenegro", "Kıbrıs": "Cyprus", "Ermenistan": "Armenia", "Kazakistan": "Kazakhstan",
    "Moldova": "Moldova", "Belarus": "Belarus", "Beyaz Rusya": "Belarus", "Faroe Adaları": "Faroe Islands", "Malta": "Malta",
    "Andorra": "Andorra", "Cebelitarık": "Gibraltar", "San Marino": "San Marino", "Lihtenştayn": "Liechtenstein",
    "Rusya": "Russia",
}
# statsbet.org adres parcasi farkli olanlar
EN_SLUG = {"Czechia": "czech-republic", "Ireland": "republic-of-ireland"}


# ---------------------------------------------------------------- yardimcilar
def istek(url, json_mu=True, basliklar=None, deneme=3):
    # gzip: Nesine bulteni sikistirmasiz istekte okuma sirasinda baglantiyi sifirliyor (9 Ekim 2026)
    h = {"User-Agent": UA, "Accept": "application/json" if json_mu else "text/html", "Accept-Encoding": "gzip"}
    h.update(basliklar or {})
    for i in range(deneme):  # Nesine ara sira gecici SSL hatasi veriyor
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=h), timeout=60) as r:
                ham = r.read()
                if r.headers.get("Content-Encoding") == "gzip":
                    ham = gzip.decompress(ham)
                veri = ham.decode("utf-8", "ignore")
            return json.loads(veri) if json_mu else veri
        except urllib.error.HTTPError:
            raise
        except Exception:
            if i == deneme - 1:
                raise


def toto(yol):
    return istek(TOTO_API + yol, basliklar={"Origin": "https://www.sportoto.gov.tr", "Referer": "https://www.sportoto.gov.tr/"})["object"]


def sade(s):
    s = s.replace("İ", "i").replace("ı", "i").lower()
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9 ]", " ", s).split()


def ayni_takim(a, b):
    takma = {"psg": "paris st germain"}  # Nesine kisaltmalari
    a, b = takma.get(a.strip().lower(), a), takma.get(b.strip().lower(), b)
    ek = {"fk", "sk", "jk", "as", "fc", "istanbul"}  # kulup adlarindaki farkli yazilan ekler
    ta, tb = [x for x in sade(a) if x not in ek] or sade(a), [x for x in sade(b) if x not in ek] or sade(b)
    if not ta or not tb:
        return False
    kisa, uzun = (ta, tb) if len(ta) <= len(tb) else (tb, ta)
    if all(any(u.startswith(k) for u in uzun) for k in kisa):  # "k makedonya cum" ~ "kuzey makedonya cumhuriyeti"
        return True
    return difflib.SequenceMatcher(None, " ".join(ta), " ".join(tb)).ratio() >= 0.85


def marjsiz(oranlar):
    ters = [1 / o for o in oranlar]
    t = sum(ters)
    return [round(x / t, 4) for x in ters], round(t - 1, 4)


def yuzde(p):
    return "  -  " if p is None else f"{p * 100:4.0f}%"


def hafta_yolu(sezon, hafta, uzanti="json"):
    return os.path.join(HAFTALAR, f"{sezon.replace('/', '-')}_{int(hafta):02d}.{uzanti}")


def oku(yol):
    with open(yol, encoding="utf-8") as f:
        return json.load(f)


def yaz(yol, veri):
    with open(yol, "w", encoding="utf-8") as f:
        json.dump(veri, f, ensure_ascii=False, indent=1)


def olasilik(m):
    return m.get("final") or m.get("piyasa") or m.get("elo")


def secim_listesi(s):
    """'1', '10', '1-0', '1X', '102' -> ['1','0'] gibi; X -> 0."""
    s = s.upper().replace("X", "0")
    return sorted(set(c for c in s if c in "102"), key="102".index)


# ---------------------------------------------------------------- Spor Toto programi
def tur_bul(sezon=None, hafta=None):
    turlar = [t for t in toto("api/GameRound") if t.get("isPublished")]
    if sezon:
        turlar = [t for t in turlar if t["year"] == sezon]
    if hafta:
        turlar = [t for t in turlar if t["name"] == f"{int(hafta)}. Hafta"]
    if not turlar:
        sys.exit("Hafta bulunamadi.")
    return max(turlar, key=lambda t: t["roundCloseDate"])


def mac_kayitlari(tur_id):
    kayit = []
    for i, x in enumerate(toto(f"api/GameMatch/GetGameMatches/?gameRoundId={tur_id}"), 1):
        m = x["match"]
        kayit.append({
            "no": i,
            "tarih": m["date"][:16].replace("T", " "),
            "ev": m["homeTeam"]["name"],
            "dep": m["awayTeam"]["name"],
            "lig": TURNUVA.get(m["tournamentId"], f"T{m['tournamentId']}")
                   + (f" {m['stage']['name']}" if m.get("stage") else ""),
            "milli": bool(m["homeTeam"].get("isNational")),
            "_skor": m.get("score"),
            "_sonuc": m.get("fullTimeWin"),
        })
    return kayit


def cmd_program(a):
    tur = tur_bul(a.sezon, a.hafta)
    hafta = int(tur["name"].split(".")[0])
    maclar = mac_kayitlari(tur["id"])
    print(f"{tur['year']} {tur['name']}  (id {tur['id']}, kapanis {tur['roundCloseDate'][:16].replace('T', ' ')})\n")
    for m in maclar:
        print(f"{m['no']:2}. {m['tarih']}  {m['ev']} - {m['dep']}  [{m['lig']}]")
    if a.yaz:
        yol = hafta_yolu(tur["year"], hafta)
        if os.path.exists(yol) and not a.zorla:
            sys.exit(f"\n{yol} zaten var (ustune yazmak icin --zorla).")
        os.makedirs(HAFTALAR, exist_ok=True)
        yaz(yol, {"sezon": tur["year"], "hafta": hafta, "tur_id": tur["id"],
                  "kapanis": tur["roundCloseDate"][:16].replace("T", " "),
                  "maclar": [{k: v for k, v in m.items() if not k.startswith("_")} for m in maclar],
                  "kuponlar": []})
        print(f"\nYazildi: {yol}")


# ---------------------------------------------------------------- Elo modeli
def elo_olasilik(fark, ev=1):
    z = ELO_A * fark / 100 + ELO_B * ev
    s = lambda x: 1 / (1 + math.exp(-x))
    p1, p2 = s(z - ELO_C), s(-z - ELO_C)
    return [round(p1, 4), round(1 - p1 - p2, 4), round(p2, 4)]


def elo_puanlari():
    b = {"Referer": "https://www.eloratings.net/"}
    kod_ad = {}
    for satir in istek("https://www.eloratings.net/en.teams.tsv", False, b).splitlines():
        p = satir.split("\t")
        if len(p) >= 2:
            kod_ad[p[0]] = p[1]
    puan = {}
    for satir in istek("https://www.eloratings.net/World.tsv", False, b).splitlines():
        p = satir.split("\t")
        if len(p) > 3:
            puan[kod_ad.get(p[2], p[2])] = int(p[3])
    return puan


def cmd_elo(a):
    h = oku(a.dosya)
    puan = elo_puanlari()
    print(f"{'#':>2}  {'Maç':42} {'Elo':>11}   {'1':>5} {'0':>5} {'2':>5}")
    for m in h["maclar"]:
        e1, e2 = TR2EN.get(m["ev"]), TR2EN.get(m["dep"])
        if not (e1 in puan and e2 in puan):
            print(f"{m['no']:2}  {m['ev']} - {m['dep']}: Elo puani yok (milli takim degil ya da TR2EN eksik)")
            continue
        ev = 0 if m.get("tarafsiz") else 1
        m["elo_puan"] = [puan[e1], puan[e2]]
        m["elo"] = elo_olasilik(puan[e1] - puan[e2], ev)
        p = m["elo"]
        print(f"{m['no']:2}  {m['ev'] + ' - ' + m['dep']:42} {puan[e1]:>5}-{puan[e2]:<5} {yuzde(p[0])} {yuzde(p[1])} {yuzde(p[2])}")
    yaz(a.dosya, h)


# ---------------------------------------------------------------- oranlar
def nesine_oranlari():
    veri = istek(NESINE, basliklar={"Referer": "https://www.nesine.com/", "Origin": "https://www.nesine.com"})
    olaylar = []
    for e in veri["sg"]["EA"]:
        if e.get("GT") != 1 or not e.get("HN"):
            continue
        ms = next((x for x in e.get("MA", []) if x.get("MTID") == 1), None)
        if ms and len(ms["OCA"]) == 3:
            olaylar.append({"ev": e["HN"], "dep": e["AN"], "tarih": e["D"], "oran": [o["O"] for o in sorted(ms["OCA"], key=lambda o: o["N"])]})
    return olaylar


def statsbet_oranlari(ev_en, dep_en, gun):
    slug = lambda ad: EN_SLUG.get(ad, ad.lower().replace(" ", "-"))
    return statsbet_sayfa(f"https://statsbet.org/football/matches/{slug(ev_en)}-vs-{slug(dep_en)}-{gun}")


def statsbet_sayfa(url):
    try:
        html = istek(url, False)
    except Exception:
        return url, {}
    td = r'\],\[\\"\$\\",\\"td\\",null,\{[^}]*children\\":\\"([0-9.]+)\\"\}'
    bulunan = {}
    for bk, o1, o0, o2 in re.findall(r'children\\":\\"(Pinnacle|1xBet|bet365)\\"\}' + td + td + td, html):
        oran = [float(o1), float(o0), float(o2)]
        if oran != [1.5, 3.0, 1.5]:  # bet365 icin sitenin yer tutucu degeri
            bulunan.setdefault(bk, oran)
    return url, bulunan


def cmd_oranlar(a):
    h = oku(a.dosya)
    zaman = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    try:
        nesine = nesine_oranlari()
    except Exception as e:
        print("Nesine alinamadi:", e)
        nesine = []
    for m in h["maclar"]:
        gun = m["tarih"][:10]
        tr_gun = f"{gun[8:10]}.{gun[5:7]}.{gun[:4]}"
        n = next((o for o in nesine if o["tarih"] == tr_gun and ayni_takim(o["ev"], m["ev"]) and ayni_takim(o["dep"], m["dep"])), None)
        if n:
            p, marj = marjsiz(n["oran"])
            m["nesine"] = {"oran": n["oran"], "olasilik": p, "marj": marj, "zaman": zaman}
        sb = {}
        if a.statsbet and m.get("milli") and m["ev"] in TR2EN and m["dep"] in TR2EN:
            url, sb = statsbet_oranlari(TR2EN[m["ev"]], TR2EN[m["dep"]], gun)
        elif a.statsbet and m.get("statsbet", {}).get("url"):  # kulup maci: elle bulunmus adresi tazele
            url, sb = statsbet_sayfa(m["statsbet"]["url"])
        if sb:
            m["statsbet"] = {"url": url, "zaman": zaman, **{k: {"oran": v, "olasilik": marjsiz(v)[0]} for k, v in sb.items()}}
        kaynak = None
        for k in ("Pinnacle", "1xBet"):
            if k in m.get("statsbet", {}):
                kaynak = (k, m["statsbet"][k]["olasilik"])
                break
        if not kaynak and "nesine" in m:
            kaynak = ("Nesine", m["nesine"]["olasilik"])
        if kaynak:
            m["piyasa"], m["piyasa_kaynak"] = kaynak[1], kaynak[0]
        p = m.get("piyasa")
        print(f"{m['no']:2}. {m['ev'] + ' - ' + m['dep']:42} "
              + (f"{m['piyasa_kaynak']:8} {yuzde(p[0])} {yuzde(p[1])} {yuzde(p[2])}" if p else "oran yok"))
    yaz(a.dosya, h)


# ---------------------------------------------------------------- kupon
def isabet_dagilimi(ps):
    d = [1.0]
    for p in ps:
        yeni = [0.0] * (len(d) + 1)
        for k, v in enumerate(d):
            yeni[k] += v * (1 - p)
            yeni[k + 1] += v * p
        d = yeni
    return d


def kupon_ozet(h, secimler):
    ps, kolon = [], 1
    for m, s in zip(h["maclar"], secimler):
        sec = secim_listesi(s)
        p = olasilik(m)
        ps.append(sum(p["102".index(c)] for c in sec))
        kolon *= len(sec)
    d = isabet_dagilimi(ps)
    ust = lambda k: sum(d[k:])
    return {"kolon": kolon, "tutar": kolon * KOLON_BEDELI, "p15": d[15], "p14+": ust(14), "p13+": ust(13),
            "p12+": ust(12), "beklenen": sum(ps), "mac_p": ps, "dagilim": d}


def kupon_yazdir(ad, h, secimler):
    o = kupon_ozet(h, secimler)
    print(f"\n{ad}: {o['kolon']} kolon = {o['tutar']:.0f} TL")
    print("  " + "  ".join(f"{m['no']}:{'-'.join(secim_listesi(s))}" for m, s in zip(h["maclar"], secimler)))
    print(f"  15 bilme {o['p15'] * 100:.2f}% | 14+ {o['p14+'] * 100:.1f}% | 13+ {o['p13+'] * 100:.1f}% | "
          f"12+ {o['p12+'] * 100:.1f}% | beklenen isabet {o['beklenen']:.1f}/15")


def cmd_kupon(a):
    h = oku(a.dosya)
    eksik = [m["no"] for m in h["maclar"] if not olasilik(m)]
    if eksik:
        sys.exit(f"Olasiligi olmayan maclar: {eksik}")
    tek = ["102"[max(range(3), key=lambda i: olasilik(m)[i])] for m in h["maclar"]]
    kupon_yazdir("Tek kolon (her macta en olasi sonuc)", h, tek)
    for k in h.get("kuponlar", []):
        kupon_yazdir(k["ad"], h, k["secimler"])


def en_iyi_sistem(h, kolon_siniri, hedef):
    """Kolon siniri altinda P(en iyi kolonda isabet >= hedef)'i maksimize eden tekli/ikili/uclu dagilimi.
    Dal-sinir ile tam arama. Bir macta n secim yapilacaksa en olasi n sonucu secmek her zaman en iyisidir."""
    secenek = []
    for m in h["maclar"]:
        p = olasilik(m)
        sira = sorted(range(3), key=lambda i: -p[i])
        secenek.append([("".join(sorted(("102"[i] for i in sira[:n]), key="102".index)),
                         min(1.0, sum(p[i] for i in sira[:n]))) for n in (1, 2, 3)])
    tolerans = len(secenek) - hedef  # izin verilen yanlis sayisi
    sira = sorted(range(len(secenek)), key=lambda i: secenek[i][0][1])  # en belirsiz maclar once
    en_iyi = [-1.0, 0, None]
    secim = [1] * len(secenek)

    def ara(j, kolon, dag):
        # dag[k] = simdiye kadarki maclarda tam k yanlis olasiligi; yeni mac eklemek toplami artiramaz -> sinir
        toplam = sum(dag)
        if toplam < en_iyi[0] - 1e-12:
            return
        if j == len(sira):
            if toplam > en_iyi[0] + 1e-12 or kolon < en_iyi[1]:
                en_iyi[:] = [toplam, kolon, secim[:]]
            return
        i = sira[j]
        for n in (3, 2, 1):
            if kolon * n > kolon_siniri:
                continue
            q = secenek[i][n - 1][1]
            secim[i] = n
            ara(j + 1, kolon * n, [dag[0] * q] + [dag[k] * q + dag[k - 1] * (1 - q) for k in range(1, tolerans + 1)])

    ara(0, 1, [1.0] + [0.0] * tolerans)
    return [secenek[i][n - 1][0] for i, n in enumerate(en_iyi[2])]


def cmd_oner(a):
    h = oku(a.dosya)
    if a.tara:
        print(f"Hedef: en az {a.hedef} bilme (her butcede o hedefe gore en iyi sistem)\n")
        print(f"{'kolon':>6} {'tutar':>9}  {str(a.hedef) + '+':>6} {'14+':>6} {'15':>6}  secimler (1-15)")
        for k in (12, 24, 48, 96, 144, 192, 288, 384, 576, 768, 1152, 1728, MAKS_KOLON):
            sec = en_iyi_sistem(h, k, a.hedef)
            o = kupon_ozet(h, sec)
            print(f"{o['kolon']:>6} {o['tutar']:>7.0f}TL  {sum(o['dagilim'][a.hedef:]) * 100:5.1f}% {o['p14+'] * 100:5.1f}% "
                  f"{o['p15'] * 100:5.2f}%  " + " ".join("-".join(secim_listesi(s)) for s in sec))
        return
    if a.kolon > MAKS_KOLON:
        print(f"Uyari: bir bilete en fazla {MAKS_KOLON} kolon yazilabilir, bu sistem birden fazla bilet ister.")
    sec = en_iyi_sistem(h, a.kolon, a.hedef)
    kupon_yazdir(f"Onerilen sistem (en fazla {a.kolon} kolon, hedef {a.hedef}+)", h, sec)


# ---------------------------------------------------------------- halkin tercihleri ve kazanc modeli
def cmd_halk(a):
    h = oku(a.dosya)
    d = istek(NESINE_TOTO, basliklar={"Origin": "https://www.nesine.com", "Referer": "https://www.nesine.com/"})["d"]
    zaman = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    print(f"Nesine program {d['pNo']} (son oynama {d['programLastPlayDate']}), cekildi {zaman}\n")
    print(f"{'#':>2}  {'Maç':38} {'halk 1-0-2':>12}   {'bizim 1-0-2':>12}   deger (bizim/halk)")
    for x in d["matches"]:
        m = next((m for m in h["maclar"] if m["no"] == x["matchNo"]), None)
        if not m or not (ayni_takim(x["homeTeam"], m["ev"]) and ayni_takim(x["awayTeam"], m["dep"])):
            print(f"{x['matchNo']:2}  eslesmedi: {x['name']}")
            continue
        p = [x["percentage1"], x["percentage0"], x["percentage2"]]
        m["halk"] = [round(v / (sum(p) or 1), 4) for v in p]
        m["halk_zaman"] = zaman
        b = olasilik(m)
        deger = "  ".join(f"{c}:{b[i] / m['halk'][i]:.2f}" if m["halk"][i] > 0 else f"{c}:-" for i, c in enumerate("102")) if b else ""
        print(f"{m['no']:2}  {m['ev'] + ' - ' + m['dep']:38} {'-'.join(str(v) for v in p):>12}   "
              + ("-".join(str(round(v * 100)) for v in b) if b else "-").rjust(12) + f"   {deger}")
    yaz(a.dosya, h)


def _katsayilar(n=15):
    """K[d][t][m] = (1+x)^d (2+x)^t carpimindaki x^m katsayisi."""
    K = [[None] * (n + 1) for _ in range(n + 1)]
    for d in range(n + 1):
        for t in range(n + 1 - d):
            pol = [1]
            for carpan in [(1, 1)] * d + [(2, 1)] * t:
                yeni = [0] * (len(pol) + 1)
                for i, c in enumerate(pol):
                    yeni[i] += c * carpan[0]
                    yeni[i + 1] += c * carpan[1]
                pol = yeni
            K[d][t] = pol
    return K


KATSAYI = _katsayilar()


def _paylasim(lam, biz):
    """W ~ Poisson(lam) diger kazananlar varken E[biz / (W + biz)]."""
    if lam > 40:
        return biz / (lam + biz)
    toplam, pmf, w = 0.0, math.exp(-lam), 0
    while w < lam + 12 * math.sqrt(lam) + 15:
        toplam += pmf * biz / (w + biz)
        w += 1
        pmf *= lam / w
    return toplam


def sonuc_ornekleri(h, adet, tohum=7, alfa=1.15):
    """Bizim olasiliklarimizla sonuc ornekler; her ornek icin halkin bir kolonunun 0-3 yanlis yapma olasiliklari.
    alfa: halkin favorilere yigilmasi. Yuzdeler q^alfa ile keskinlestirilir; 8. haftanin gercek kazanan
    sayilariyla kalibre edildi (alfa 1.15-1.2; alfa=1 bagimsizlik varsayimi kazananlari ~%50-80 eksik tahmin etti)."""
    rnd = random.Random(tohum)
    P = [olasilik(m) for m in h["maclar"]]
    Q = []
    for m in h["maclar"]:
        w = [x ** alfa for x in m["halk"]]
        Q.append([x / sum(w) for x in w])
    ornekler = []
    for _ in range(adet):
        o, d0, d1, d2, d3 = [], 1.0, 0.0, 0.0, 0.0
        for p, q in zip(P, Q):
            r = rnd.random()
            i = 0 if r < p[0] else (1 if r < p[0] + p[1] else 2)
            o.append(i)
            qi = q[i]
            d0, d1, d2, d3 = d0 * qi, d1 * qi + d0 * (1 - qi), d2 * qi + d1 * (1 - qi), d3 * qi + d2 * (1 - qi)
        ornekler.append((o, (d0, d1, d2, d3)))
    return ornekler


def kazanc_ozet(secimler, ornekler, havuz, kolon_sayisi, devir=0.0):
    """Paylasimli ikramiye modeli: beklenen odeme, beklenen kar, kar olasiligi."""
    sec = [secim_listesi(s) for s in secimler]
    maske = [sum(1 << "102".index(c) for c in s) for s in sec]
    n = [len(s) for s in sec]
    kolon = math.prod(n)
    maliyet = kolon * KOLON_BEDELI
    uclu = sum(1 for x in n if x == 3)
    pay = {k: HAVUZ_PAYI[k] * havuz + (devir if k == 15 else 0.0) for k in HAVUZ_PAYI}
    toplam = kar_say = 0.0
    kademe = {12: 0.0, 13: 0.0, 14: 0.0, 15: 0.0}
    for o, halk_dag in ornekler:
        a = d = u2 = 0
        for i, oi in enumerate(o):
            if n[i] == 3:
                continue
            tuttu = (maske[i] >> oi) & 1
            if n[i] == 1:
                a += tuttu
            elif tuttu:
                d += 1
            else:
                u2 += 1
        carpan, pol, odeme = 2 ** u2, KATSAYI[d][uclu], 0.0
        for j in range(4):
            mm = 15 - j - a
            if 0 <= mm < len(pol) and pol[mm]:
                biz = carpan * pol[mm]
                kazanan_pay = _paylasim(kolon_sayisi * halk_dag[j], biz)
                odeme += pay[15 - j] * kazanan_pay
                kademe[15 - j] += pay[15 - j] * kazanan_pay
        toplam += odeme
        kar_say += odeme > maliyet
    s = len(ornekler)
    return {"kolon": kolon, "maliyet": maliyet, "beklenen": toplam / s, "kar": toplam / s - maliyet,
            "kar_olasiligi": kar_say / s, "kademe": {k: v / s for k, v in kademe.items()}}


def kazanc_ara(h, ornekler, havuz, kolon_sayisi, devir, kolon_siniri, baslangic):
    """Her macta 7 secim kumesinden birini degistirerek beklenen kari artiran yerel arama (en dik cikis)."""
    kumeler = ["1", "0", "2", "10", "12", "02", "102"]
    mevcut = [("".join(secim_listesi(s))) for s in baslangic]
    en_iyi = kazanc_ozet(mevcut, ornekler, havuz, kolon_sayisi, devir)["kar"]
    while True:
        aday = None
        for i in range(len(mevcut)):
            for k in kumeler:
                if k == mevcut[i]:
                    continue
                dene = mevcut[:i] + [k] + mevcut[i + 1:]
                if math.prod(len(x) for x in dene) > kolon_siniri:
                    continue
                kar = kazanc_ozet(dene, ornekler, havuz, kolon_sayisi, devir)["kar"]
                if kar > en_iyi + 1e-6 and (aday is None or kar > aday[0]):
                    aday = (kar, dene)
        if aday is None:
            return mevcut, en_iyi
        en_iyi, mevcut = aday


def kazanc_yazdir(ad, secimler, o):
    k = o["kademe"]
    print(f"\n{ad}: {o['kolon']} kolon = {o['maliyet']:,.0f} TL")
    print("  " + "  ".join(f"{i + 1}:{'-'.join(secim_listesi(s))}" for i, s in enumerate(secimler)))
    print(f"  beklenen odeme {o['beklenen']:,.0f} TL (15: {k[15]:,.0f} | 14: {k[14]:,.0f} | 13: {k[13]:,.0f} | 12: {k[12]:,.0f})"
          f" -> beklenen kar {o['kar']:+,.0f} TL | kar olasiligi %{o['kar_olasiligi'] * 100:.1f}")


def cmd_kazanc(a):
    h = oku(a.dosya)
    eksik = [m["no"] for m in h["maclar"] if not m.get("halk") or not olasilik(m)]
    if eksik:
        sys.exit(f"Halk yuzdesi ya da olasiligi olmayan maclar: {eksik} (once 'halk' komutunu calistir)")
    if a.kolon_sayisi is None:
        a.kolon_sayisi = a.havuz / 4.9  # yasal tavan: kolon basina ~4,9 TL ikramiye
    print(f"Model: havuz {a.havuz / 1e6:.0f} M TL, halkin kolon sayisi {a.kolon_sayisi / 1e6:.1f} M, devir {a.devir / 1e6:.1f} M TL, "
          f"yigilma alfa {a.alfa}, {a.ornek} ornek.")
    ornekler = sonuc_ornekleri(h, a.ornek, alfa=a.alfa)
    for k in h.get("kuponlar", []):
        kazanc_yazdir(k["ad"], k["secimler"], kazanc_ozet(k["secimler"], ornekler, a.havuz, a.kolon_sayisi, a.devir))
    if a.ara:
        arama = sonuc_ornekleri(h, max(5000, a.ornek // 4), tohum=11, alfa=a.alfa)
        baslangiclar = [k["secimler"] for k in h.get("kuponlar", []) if math.prod(len(secim_listesi(s)) for s in k["secimler"]) <= a.kolon]
        baslangiclar.append(en_iyi_sistem(h, a.kolon, 13))
        sonuclar = [kazanc_ara(h, arama, a.havuz, a.kolon_sayisi, a.devir, a.kolon, b) for b in baslangiclar]
        en_iyi = max(sonuclar, key=lambda x: x[1])[0]
        kazanc_yazdir(f"Beklenen kari en yuksek kupon (en fazla {a.kolon} kolon)", en_iyi,
                      kazanc_ozet(en_iyi, ornekler, a.havuz, a.kolon_sayisi, a.devir))
        o13 = kupon_ozet(h, en_iyi)
        print(f"  (13+ olasiligi %{o13['p13+'] * 100:.1f}, 14+ %{o13['p14+'] * 100:.1f}, 15 %{o13['p15'] * 100:.2f})")


# ---------------------------------------------------------------- sonuc
def cmd_sonuc(a):
    h = oku(a.dosya)
    maclar = mac_kayitlari(h["tur_id"])
    for m, r in zip(h["maclar"], maclar):
        if r["_sonuc"] is not None:
            m["sonuc"] = str(r["_sonuc"])
            s = r["_skor"] or {}
            m["skor"] = f"{s.get('homeRegular')}-{s.get('awayRegular')}" if s else None
    yaz(a.dosya, h)
    sonuclu = [m for m in h["maclar"] if "sonuc" in m]
    print(f"{h['sezon']} {h['hafta']}. hafta: {len(sonuclu)}/15 mac sonuclandi\n")
    for m in h["maclar"]:
        p = olasilik(m)
        tahmin = "102"[max(range(3), key=lambda i: p[i])] if p else "?"
        isaret = "" if "sonuc" not in m else ("✓" if m["sonuc"] == tahmin else "✗")
        print(f"{m['no']:2}. {m['ev'] + ' - ' + m['dep']:42} {m.get('skor') or '':6} sonuc {m.get('sonuc', '-')}  "
              f"en olasi {tahmin} {isaret}" + (f"  (sonuca verdigimiz olasilik {yuzde(p['102'.index(m['sonuc'])])})"
                                               if p and 'sonuc' in m else ""))
    if len(sonuclu) == 15:
        col = "".join(m["sonuc"] for m in h["maclar"])
        print(f"\nKazanan kolon: {col}")
        for k in h.get("kuponlar", []):
            isabet = sum(m["sonuc"] in secim_listesi(s) for m, s in zip(h["maclar"], k["secimler"]))
            print(f"{k['ad']}: en iyi kolonda {isabet}/15")
        try:
            ik = toto(f"api/GameResult/GetGameResultByGameRoundId?Id={h['tur_id']}")
            print(f"Ikramiye: 15 bilen {ik['fifteenWinCount']} kisi x {ik['fifteenWinPrize']:,.2f} TL | "
                  f"14: {ik['fourteenWinCount']} x {ik['fourteenWinPrize']:,.2f} | 13: {ik['thirteenWinCount']} x "
                  f"{ik['thirteenWinPrize']:,.2f} | 12: {ik['twelveWinCount']} x {ik['twelveWinPrize']:,.2f}")
        except Exception:
            print("Ikramiye bilgisi henuz yok.")


def main():
    ap = argparse.ArgumentParser(description="Spor Toto analiz araci")
    alt = ap.add_subparsers(dest="komut", required=True)
    p = alt.add_parser("program")
    p.add_argument("--sezon")
    p.add_argument("--hafta", type=int)
    p.add_argument("--yaz", action="store_true")
    p.add_argument("--zorla", action="store_true")
    for ad in ("elo", "oranlar", "kupon", "oner", "sonuc", "halk", "kazanc"):
        q = alt.add_parser(ad)
        q.add_argument("dosya")
        if ad == "oranlar":
            q.add_argument("--statsbet", action="store_true", help="milli takim maclarinda Pinnacle/1xBet oranlari")
        if ad == "oner":
            q.add_argument("--kolon", type=int, default=96)
            q.add_argument("--hedef", type=int, default=15, help="en az kac bilme olasiligi maksimize edilsin (12-15)")
            q.add_argument("--tara", action="store_true", help="farkli kolon butceleri icin tablo")
        if ad == "kazanc":
            q.add_argument("--kolon", type=int, default=MAKS_KOLON, help="--ara icin kolon siniri")
            q.add_argument("--havuz", type=float, default=75e6, help="tahmini toplam ikramiye havuzu (TL)")
            q.add_argument("--kolon-sayisi", dest="kolon_sayisi", type=float, default=None,
                           help="halkin toplam kolon sayisi (varsayilan: havuz / 4,9 TL)")
            q.add_argument("--alfa", type=float, default=1.15, help="halkin favorilere yigilmasi (8. hafta kalibrasyonu: 1.15)")
            q.add_argument("--devir", type=float, default=0.0, help="15 bilenlere devreden tutar (TL)")
            q.add_argument("--ornek", type=int, default=40000, help="Monte Carlo ornek sayisi")
            q.add_argument("--ara", action="store_true", help="beklenen kari en yuksek kuponu ara")
    a = ap.parse_args()
    {"program": cmd_program, "elo": cmd_elo, "oranlar": cmd_oranlar, "kupon": cmd_kupon,
     "oner": cmd_oner, "sonuc": cmd_sonuc, "halk": cmd_halk, "kazanc": cmd_kazanc}[a.komut](a)


if __name__ == "__main__":
    main()
