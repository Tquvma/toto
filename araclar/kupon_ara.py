"""9. hafta: <=144 kolon (1.440 TL) icin cok baslangicli kupon aramasi.
Hedefler: beklenen kar (kar), kar olasiligi (pk), 13+ olasiligi. Sonuc: Pareto listesi.
Kullanim: python kupon_ara.py <json> <cikti.json> [kolon_siniri]"""
import sys, os, json, math, random, time
from concurrent.futures import ProcessPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import toto

KUMELER = ["1", "0", "2", "10", "12", "02", "102"]
HAVUZ = 110e6
KS = HAVUZ / 4.9
ALFA = 1.15
G = {}


def init(yol):
    G["h"] = toto.oku(yol)
    G["orn"] = toto.sonuc_ornekleri(G["h"], 3000, tohum=11, alfa=ALFA)


def kolon(s):
    return math.prod(len(x) for x in s)


def ozet(s):
    return toto.kazanc_ozet(s, G["orn"], HAVUZ, KS, 0.0)


def skor(o, hedef):
    if hedef == "kar":
        return o["kar"]
    # kar olasiligi; esitlikte beklenen kar
    return o["kar_olasiligi"] * 1e7 + o["kar"]


def komsular(s, sinir):
    n = len(s)
    for i in range(n):
        for k in KUMELER:
            if k != s[i]:
                d = s[:i] + [k] + s[i + 1:]
                if kolon(d) <= sinir:
                    yield d
    # boyut takasi: i kuculur, j buyur (butce dar oldugu icin tekli hamle yetmez)
    for i in range(n):
        for ki in KUMELER:
            if len(ki) >= len(s[i]):
                continue
            for j in range(n):
                if j == i:
                    continue
                for kj in KUMELER:
                    if len(kj) <= len(s[j]):
                        continue
                    d = s[:]
                    d[i], d[j] = ki, kj
                    if kolon(d) <= sinir:
                        yield d


def yerel(args):
    bas, sinir, hedef = args
    s = ["".join(toto.secim_listesi(x)) for x in bas]
    en = skor(ozet(s), hedef)
    while True:
        aday = None
        for d in komsular(s, sinir):
            v = skor(ozet(d), hedef)
            if v > en + 1e-6 and (aday is None or v > aday[0]):
                aday = (v, d)
        if aday is None:
            return s, en
        en, s = aday


def rastgele_baslangic(h, sinir, tohum):
    rnd = random.Random(tohum)
    yapilar = [(t, d) for t in range(5) for d in range(8) if 3 ** t * 2 ** d <= sinir]
    yapilar = [y for y in yapilar if not any(3 ** y[0] * 2 ** (y[1] + 1) <= sinir for _ in [0])]  # maksimal yapilar
    t, d = rnd.choice(yapilar)
    idx = list(range(15))
    rnd.shuffle(idx)
    s = []
    for i, m in enumerate(h["maclar"]):
        p = toto.olasilik(m)
        q = m["halk"]
        w = [p[k] * (p[k] / q[k]) ** rnd.uniform(0, 1) for k in range(3)]  # olasilik + deger karisimi
        sira = sorted(range(3), key=lambda k: -w[k] * rnd.uniform(0.7, 1.3))
        n = 3 if i in idx[:t] else (2 if i in idx[t:t + d] else 1)
        s.append("".join(sorted(("102"[k] for k in sira[:n]), key="102".index)))
    return s


def main():
    yol, cikti = sys.argv[1], sys.argv[2]
    sinir = int(sys.argv[3]) if len(sys.argv) > 3 else 144
    h = toto.oku(yol)
    baslar = [k["secimler"] for k in h["kuponlar"] if kolon([toto.secim_listesi(x) for x in k["secimler"]]) <= sinir]
    for hd in (12, 13, 14):
        baslar.append(toto.en_iyi_sistem(h, sinir, hd))
    baslar += [rastgele_baslangic(h, sinir, 100 + i) for i in range(24)]
    isler = [(b, sinir, hd) for hd in ("kar", "pk") for b in baslar]
    t0 = time.time()
    with ProcessPoolExecutor(8, initializer=init, initargs=(yol,)) as ex:
        sonuc = list(ex.map(yerel, isler))
    print(f"{len(isler)} arama, {time.time() - t0:.0f} sn", file=sys.stderr)
    tekil = {}
    for (s, v), (b, _, hd) in zip(sonuc, isler):
        tekil.setdefault(" ".join(s), set()).add(hd)
    json.dump([{"secimler": k.split(), "hedef": sorted(v)} for k, v in tekil.items()], open(cikti, "w"))
    print(f"{len(tekil)} farkli yerel optimum", file=sys.stderr)


if __name__ == "__main__":
    main()
