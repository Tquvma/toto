"""Birden fazla biletten (ayrik tam sistemler) olusan kuponu degerlendirir: kolon, 15 (tam), 14+/13+/12+ (tam),
kazanc modeli (4 tohum x 20.000 ornek, biletler arasi ortak paylasim; havuz 110 M, alfa 1.15).
Kullanim: python coklu_bilet.py <hafta.json> "<bilet1>" "<bilet2>" ...
Bilet: 15 secim, bosluklu, ornek "1 12 102 102 2 102 102 1 2 2 1 1 102 1 102"."""
import itertools, math, os, sys
from concurrent.futures import ProcessPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import toto

HAVUZ = 110e6
TOHUM = (7, 21, 33, 45)
G = {}


def init(yol):
    G["h"] = toto.oku(yol)
    G["P"] = [toto.olasilik(m) for m in G["h"]["maclar"]]


def kolon(bilet):
    return math.prod(len(s) for s in bilet)


def ayrik_mi(biletler):
    return all(not all(set(x) & set(y) for x, y in zip(a, b)) for a, b in itertools.combinations(biletler, 2))


def p15(P, bilet):
    return math.prod(sum(P[i]["102".index(c)] for c in s) for i, s in enumerate(bilet))


def isabet_ust(P, biletler):
    """P(en iyi kolon >= k), k = 12..15. Tum biletlerde ayni tek olan maclar sabit, digerleri numaralanir."""
    sabit = [i for i in range(15) if len({b[i] for b in biletler}) == 1 and len(biletler[0][i]) == 1]
    deg = [i for i in range(15) if i not in sabit]
    d = toto.isabet_dagilimi([P[i]["102".index(biletler[0][i])] for i in sabit])
    ust = dict.fromkeys((12, 13, 14, 15), 0.0)
    for o in itertools.product(range(3), repeat=len(deg)):
        po = math.prod(P[i][j] for i, j in zip(deg, o))
        hv = max(sum("102"[j] in b[i] for i, j in zip(deg, o)) for b in biletler)
        for k in ust:
            ust[k] += po * sum(d[max(0, k - hv):])
    return ust


def kazanc_is(args):
    yol, tohum, biletler = args
    h = toto.oku(yol)
    orn = toto.sonuc_ornekleri(h, 20000, tohum=tohum, alfa=1.15)
    ks = HAVUZ / 4.9
    pay = {k: toto.HAVUZ_PAYI[k] * HAVUZ for k in toto.HAVUZ_PAYI}
    maliyet = sum(kolon(b) for b in biletler) * toto.KOLON_BEDELI
    top = kar = 0.0
    for o, halk in orn:
        say = dict.fromkeys((15, 14, 13, 12), 0)
        for b in biletler:
            pol = [1]  # pol[m] = bu biletin m mac bilen kolon sayisi
            for i, s in enumerate(b):
                tut = 1 if "102"[o[i]] in s else 0
                yeni = [0] * (len(pol) + 1)
                for m, c in enumerate(pol):
                    yeni[m] += c * (len(s) - tut)
                    yeni[m + 1] += c * tut
                pol = yeni
            for k in say:
                say[k] += pol[k]
        odeme = sum(pay[k] * toto._paylasim(ks * halk[15 - k], say[k]) for k in say if say[k])
        top += odeme
        kar += odeme > maliyet
    return top / len(orn) / maliyet, kar / len(orn)


def degerlendir(yol, biletler, ad=""):
    h = toto.oku(yol)
    P = [toto.olasilik(m) for m in h["maclar"]]
    if not ayrik_mi(biletler):
        sys.exit("Biletler ayrik degil (ayni kolon iki bilette var)")
    ust = isabet_ust(P, biletler)
    with ProcessPoolExecutor(4) as ex:
        R = list(ex.map(kazanc_is, [(yol, t, biletler) for t in TOHUM]))
    g = [r[0] for r in R]
    k = sum(kolon(b) for b in biletler)
    print(f"{ad}{len(biletler)} bilet, {k} kolon = {k * toto.KOLON_BEDELI:,.0f} TL | 15 %{sum(p15(P, b) for b in biletler) * 100:.2f} | "
          f"14+ %{ust[14] * 100:.1f} | 13+ %{ust[13] * 100:.1f} | 12+ %{ust[12] * 100:.1f} | getiri %{sum(g) / 4 * 100:.0f} "
          f"({min(g) * 100:.0f}-{max(g) * 100:.0f}) | kar olasiligi %{sum(r[1] for r in R) / 4 * 100:.1f}")
    for b in biletler:
        print(f"  {kolon(b):>5} kolon: " + " ".join("-".join(toto.secim_listesi(s)) for s in b))
    return ust, sum(g) / 4


if __name__ == "__main__":
    degerlendir(sys.argv[1], [x.split() for x in sys.argv[2:]])
