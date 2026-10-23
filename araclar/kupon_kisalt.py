"""Tek biletlik bir kuponu (taban) istenen kolon sayisina indirir, 15/14+/13+ olasiligini dusurmeden.
Bir bilete yazilamayan tutarlar (or. 2.133 kolon) icin kuponu birkac bilete boler:
  S = (taban - R) + A
  R: tabanin icinden cikarilan en olasiliksiz blok (en fazla 3 kisitli mac -> en fazla 3 bilet),
  A: tabanin bir tekini diger sonuc(lar)ina saptiran en olasi blok (1 bilet).
|R| - |A| = kolon(taban) - hedef. Getiri dogrusal yaklasimla (blok bazinda) siralanir, 14+/13+ tam hesaplanir.
En iyi adaylari coklu_bilet.py ile dogrula (tam paylasim, 4 tohum).
Kullanim: python kupon_kisalt.py <hafta.json> "<taban secimler>" <hedef_kolon> [cikti.json]"""
import itertools, json, math, os, sys
from concurrent.futures import ProcessPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import toto
import coklu_bilet

HAVUZ = 110e6
G = {}
sira = lambda s: "".join(sorted(s, key="102".index))


def init(yol, taban):
    h = toto.oku(yol)
    ks = HAVUZ / 4.9
    G["taban"] = taban
    G["orn"] = [(o, [toto._paylasim(ks * d[j], 1) for j in range(4)]) for o, d in toto.sonuc_ornekleri(h, 3000, tohum=11, alfa=1.15)]


def blok_deger(args):
    """Blok kolonlarinin dogrusal beklenen odemesi. args = (sapma (mac, kume) ya da None, {mac: kume})."""
    sap, kisit = args
    taban = G["taban"]
    pay = {k: toto.HAVUZ_PAYI[k] * HAVUZ for k in toto.HAVUZ_PAYI}
    top = 0.0
    for o, g in G["orn"]:
        pol = [1]
        for i, s in enumerate(taban):
            s = sap[1] if sap and i == sap[0] else kisit.get(i, s)
            tut = 1 if "102"[o[i]] in s else 0
            yeni = [0] * (len(pol) + 1)
            for m, c in enumerate(pol):
                yeni[m] += c * (len(s) - tut)
                yeni[m + 1] += c * tut
            pol = yeni
        for j in range(4):
            if pol[15 - j]:
                top += pay[15 - j] * pol[15 - j] * g[j]
    return top / len(G["orn"])


def main():
    yol, taban, hedef = sys.argv[1], ["".join(toto.secim_listesi(s)) for s in sys.argv[2].split()], int(sys.argv[3])
    h = toto.oku(yol)
    P = [toto.olasilik(m) for m in h["maclar"]]
    pi = lambda i, s: sum(P[i]["102".index(c)] for c in s)
    U = [i for i in range(15) if len(taban[i]) > 1]
    T = [i for i in range(15) if len(taban[i]) == 1]
    fark = coklu_bilet.kolon(taban) - hedef
    if fark <= 0:
        sys.exit("hedef kolon tabandan kucuk olmali")
    ptek = math.prod(pi(i, taban[i]) for i in T)
    secenek = [[None] + [sira(x) for n in range(1, len(taban[i])) for x in itertools.combinations(taban[i], n)] for i in U]
    bloklar = []
    for b in itertools.product(*secenek):
        r = math.prod(len(taban[i]) if s is None else len(s) for i, s in zip(U, b))
        p = math.prod(1.0 if s is None else pi(i, s) / pi(i, taban[i]) for i, s in zip(U, b))
        bloklar.append((b, r, p, sum(s is not None for s in b)))
    Rler = [x for x in bloklar if 1 <= x[3] <= 3]
    boy = {}
    for x in bloklar:
        boy.setdefault(x[1], []).append(x)
    enbuyuk = {r: sorted(v, key=lambda x: -x[2])[:40] for r, v in boy.items()}
    sapmalar = [(i, sira(s), pi(i, s) / pi(i, taban[i])) for i in T for n in (1, 2)
                for s in itertools.combinations([c for c in "102" if c != taban[i]], n)]
    sapmalar = [x for x in sapmalar if x[2] >= 0.3]
    ciftler = []
    for b, r, p, t in Rler:
        if r == fark:
            ciftler.append((ptek * (1 - p), t, b, None, None))
        for i, s, oran in sapmalar:
            a = r - fark
            if a > 0 and a % len(s) == 0 and a // len(s) in enbuyuk:
                for bA, _, pA, _ in enbuyuk[a // len(s)]:
                    if 1 - p + oran * pA >= 1 - 1e-12:
                        ciftler.append((ptek * (1 - p + oran * pA), t + 1, b, (i, s), bA))
    print(f"15 olasiligi tabandan dusuk olmayan {len(ciftler)} aday", file=sys.stderr)
    kisit = lambda b: {i: s for i, s in zip(U, b) if s is not None}
    gerekli = {(None, tuple(sorted(kisit(x[2]).items()))) for x in ciftler}
    gerekli |= {(x[3], tuple(sorted(kisit(x[4]).items()))) for x in ciftler if x[3]}
    gerekli.add((None, ()))
    gerekli = list(gerekli)
    with ProcessPoolExecutor(8, initializer=init, initargs=(yol, taban)) as ex:
        deger = dict(zip(gerekli, ex.map(blok_deger, [(s, dict(k)) for s, k in gerekli], chunksize=20)))
    E0 = deger[(None, ())]
    maliyet = hedef * toto.KOLON_BEDELI

    def biletler(bR, sap, bA):
        out, onceki = [], {}
        for i, s in kisit(bR).items():
            b = taban[:]
            for j, ss in onceki.items():
                b[j] = ss
            b[i] = "".join(c for c in taban[i] if c not in s)
            out.append(b)
            onceki[i] = s
        if sap:
            a = taban[:]
            a[sap[0]] = sap[1]
            for i, s in kisit(bA).items():
                a[i] = s
            out.append(a)
        return out

    adaylar = []
    for p15, nb, bR, sap, bA in ciftler:
        e = E0 - deger[(None, tuple(sorted(kisit(bR).items())))]
        if sap:
            e += deger[(sap, tuple(sorted(kisit(bA).items())))]
        adaylar.append({"getiri_dogrusal": e / maliyet, "p15": p15, "biletler": biletler(bR, sap, bA)})
    adaylar.sort(key=lambda x: -x["getiri_dogrusal"])
    ust0 = coklu_bilet.isabet_ust(P, [taban])
    # tam 14+/13+ hesabi pahali: getiriye gore ilk 400, 15'e gore ilk 400 ve 15'i tabandan %3+ yuksek olanlarin getiriye gore ilk 400'u
    secim = {}
    for liste in (adaylar, sorted(adaylar, key=lambda x: -x["p15"]), [x for x in adaylar if x["p15"] >= ptek * 1.03]):
        for x in liste[:400]:
            secim[id(x)] = x
    iyi = []
    for x in sorted(secim.values(), key=lambda x: -x["getiri_dogrusal"]):
        u = coklu_bilet.isabet_ust(P, x["biletler"])
        if u[13] >= ust0[13] - 1e-9 and u[14] >= ust0[14] - 1e-9:
            x["ust"] = {str(k): v for k, v in u.items()}
            iyi.append(x)
    print(f"Taban: {coklu_bilet.kolon(taban)} kolon, 15 %{ptek * 100:.2f}, 14+ %{ust0[14] * 100:.1f}, 13+ %{ust0[13] * 100:.1f}, "
          f"dogrusal getiri %{E0 / (coklu_bilet.kolon(taban) * toto.KOLON_BEDELI) * 100:.1f}")
    print(f"Hedef {hedef} kolon: 15/14+/13+ tabandan dusuk olmayan {len(iyi)} aday (getiriye gore ilk 8):")
    for x in iyi[:8]:
        print(f"  getiri ~%{x['getiri_dogrusal'] * 100:.1f} | 15 %{x['p15'] * 100:.2f} | 14+ %{x['ust']['14'] * 100:.1f} | "
              f"13+ %{x['ust']['13'] * 100:.1f} | " + " / ".join(" ".join(b) for b in x["biletler"]))
    if iyi:
        x = max(iyi, key=lambda x: x["p15"])
        print(f"  15'i en yuksek: getiri ~%{x['getiri_dogrusal'] * 100:.1f} | 15 %{x['p15'] * 100:.2f} | 14+ %{x['ust']['14'] * 100:.1f} | "
              f"13+ %{x['ust']['13'] * 100:.1f} | " + " / ".join(" ".join(b) for b in x["biletler"]))
    if len(sys.argv) > 4:
        json.dump(iyi[:20], open(sys.argv[4], "w"))


if __name__ == "__main__":
    main()
