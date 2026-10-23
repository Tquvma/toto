"""Kucuk kuponlar icin ORNEKLEMESIZ (tam) beklenen odeme: kuponun en fazla 3 yanlis yaptigi tum sonuclar numaralanir.
Paylasim modeli toto.kazanc_ozet ile ayni (havuz, halkin kolon sayisi = havuz / 4,9, alfa ile keskinlestirilmis halk yuzdeleri).
Monte Carlo'dan farki: nadir ama buyuk odemeli sonuclar (surpriz kuponlarin degeri) gurultusuz hesaplanir.
Kullanim: python kesin_kazanc.py <hafta.json> "<secimler>" ["<secimler>" ...]   (secimler: "1 2 102 ...")"""
import math, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import toto


def hazirla(h, alfa=1.15):
    P = [toto.olasilik(m) for m in h["maclar"]]
    Q = []
    for m in h["maclar"]:
        w = [x ** alfa for x in m["halk"]]
        Q.append([x / sum(w) for x in w])
    return P, Q


def kesin(P, Q, secimler, havuz=110e6, kolon_sayisi=None, devir=0.0):
    """Donus: {beklenen, kademe{15,14,13,12}, p15, kolon, maliyet, getiri}."""
    ks = kolon_sayisi or havuz / 4.9
    pay = {k: toto.HAVUZ_PAYI[k] * havuz + (devir if k == 15 else 0.0) for k in toto.HAVUZ_PAYI}
    sec = [["102".index(c) for c in toto.secim_listesi(s)] for s in secimler]
    n = [len(s) for s in sec]
    kademe = {15: 0.0, 14: 0.0, 13: 0.0, 12: 0.0}
    yigin = [(0, 1.0, 0, (1, 0, 0, 0), 1, (1.0, 0.0, 0.0, 0.0))]
    while yigin:
        i, po, m, e, carp, d = yigin.pop()
        if i == 15:
            for k in range(4 - m):
                adet = e[k] * carp
                if adet:
                    t = 15 - m - k
                    kademe[t] += po * pay[t] * toto._paylasim(ks * d[m + k], adet)
            continue
        Pi, Qi, si, a = P[i], Q[i], sec[i], n[i] - 1
        d0, d1, d2, d3 = d
        for j in range(3):
            q = Qi[j]
            nd = (d0 * q, d1 * q + d0 * (1 - q), d2 * q + d1 * (1 - q), d3 * q + d2 * (1 - q))
            if j in si:
                yigin.append((i + 1, po * Pi[j], m, (e[0], e[1] + a * e[0], e[2] + a * e[1], e[3] + a * e[2]), carp, nd))
            elif m < 3:
                yigin.append((i + 1, po * Pi[j], m + 1, e, carp * n[i], nd))
    kolon = math.prod(n)
    p15 = math.prod(sum(P[i][j] for j in sec[i]) for i in range(15))
    top = sum(kademe.values())
    return {"beklenen": top, "kademe": kademe, "p15": p15, "kolon": kolon, "maliyet": kolon * toto.KOLON_BEDELI,
            "getiri": top / (kolon * toto.KOLON_BEDELI)}


def tutunca_dagilim(P, Q, secimler, havuz=110e6):
    """15 tuttugunda (sonuc kuponun bir kolonuna esit) kuponun toplam odemesinin dagilimi.
    Donus: [(olasilik, odeme, diger 15 bilen beklentisi)], olasiliklar P(15)'e normalize."""
    import itertools
    ks = havuz / 4.9
    pay = {k: toto.HAVUZ_PAYI[k] * havuz for k in toto.HAVUZ_PAYI}
    sec = [["102".index(c) for c in toto.secim_listesi(s)] for s in secimler]
    out, top = [], 0.0
    for o in itertools.product(*sec):
        po = math.prod(P[i][j] for i, j in enumerate(o))
        d = [1.0, 0.0, 0.0, 0.0]
        for i, j in enumerate(o):
            q = Q[i][j]
            d = [d[0] * q, d[1] * q + d[0] * (1 - q), d[2] * q + d[1] * (1 - q), d[3] * q + d[2] * (1 - q)]
        pol = [1]  # kuponun bu sonucta k yanlis yapan kolon sayilari
        for i, j in enumerate(o):
            a = len(sec[i]) - 1
            pol = [(pol[k] if k < len(pol) else 0) + (a * pol[k - 1] if 0 < k <= len(pol) else 0) for k in range(min(4, len(pol) + 1))]
        odeme = sum(pay[15 - k] * toto._paylasim(ks * d[k], pol[k]) for k in range(len(pol)) if pol[k])
        out.append([po, odeme, ks * d[0]])
        top += po
    for x in out:
        x[0] /= top
    return sorted(out, key=lambda x: x[1])


def yuzdelik(dag, p):
    birikim = 0.0
    for w, v, _ in dag:
        birikim += w
        if birikim >= p:
            return v
    return dag[-1][1]


if __name__ == "__main__":
    h = toto.oku(sys.argv[1])
    P, Q = hazirla(h)
    for s in sys.argv[2:]:
        sec = s.split()
        r = kesin(P, Q, sec)
        o = toto.kupon_ozet(h, sec)
        k = r["kademe"]
        print(f"{r['kolon']} kolon = {r['maliyet']:,.0f} TL | 15 %{r['p15'] * 100:.4f} (1/{1 / r['p15']:,.0f}) | 13+ %{o['p13+'] * 100:.2f} | "
              f"getiri %{r['getiri'] * 100:.0f} (15: {k[15]:,.1f} 14: {k[14]:,.1f} 13: {k[13]:,.1f} 12: {k[12]:,.1f} TL) | {s}")
        if r["kolon"] <= 2500:
            dag = tutunca_dagilim(P, Q, sec)
            ort = sum(w * v for w, v, _ in dag)
            kisi = sum(w * x for w, _, x in dag)
            print(f"    15 tutarsa toplam odeme: medyan {yuzdelik(dag, .5):,.0f} | %25 {yuzdelik(dag, .25):,.0f} | %75 {yuzdelik(dag, .75):,.0f} | "
                  f"ortalama {ort:,.0f} TL | diger 15 bilen ort. {kisi:,.1f}")
