"""Ucuz surpriz kuponu aramasi: kolon siniri ve 15 olasiligi esigi altinda TAM (orneklemesiz) beklenen getiriyi en yukselten kupon.
Oynanmis kuponlarla (--ayrik) ayni kolonu icermemesi sart: en az bir macta secim kumeleri kesismemeli.
Kullanim: python surpriz_ara.py <hafta.json> <cikti.json> <kolon1,kolon2,...> <p15_esik1,...> [--ayrik "<secimler>" ...]"""
import json, math, os, random, sys, time
from concurrent.futures import ProcessPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import toto
import kesin_kazanc as K
import kupon_ara as O

G = {}


def init(yol, ayrik):
    G["h"] = toto.oku(yol)
    G["P"], G["Q"] = K.hazirla(G["h"])
    G["ayrik"] = [[set(toto.secim_listesi(s)) for s in a] for a in ayrik]
    G["onbellek"] = {}


def ayrik_mi(s):
    return all(any(not (set(x) & y) for x, y in zip(s, a)) for a in G["ayrik"])


def skor(s, esik):
    anahtar = tuple(s)
    if anahtar not in G["onbellek"]:
        G["onbellek"][anahtar] = K.kesin(G["P"], G["Q"], s)
    r = G["onbellek"][anahtar]
    if r["p15"] < esik:
        return -10 + r["p15"] / esik
    if not ayrik_mi(s):
        return -5 + r["getiri"]
    return r["getiri"]


def tekli_komsular(s, sinir):
    """Tek bir macin secim kumesini degistiren hamleler (kolon siniri icinde)."""
    for i in range(15):
        for k in O.KUMELER:
            if k != s[i]:
                d = s[:i] + [k] + s[i + 1:]
                if O.kolon(d) <= sinir:
                    yield d


def yerel(args):
    """Ilk iyilestirmede atlayan yerel arama (rastgele sira); tikaninca boyut takasi hamlelerini de dener."""
    bas, sinir, esik, tohum = args
    rnd = random.Random(tohum)
    s = ["".join(toto.secim_listesi(x)) for x in bas]
    en = skor(s, esik)
    takas = False
    while True:
        komsu = list(O.komsular(s, sinir) if takas else tekli_komsular(s, sinir))
        rnd.shuffle(komsu)
        for d in komsu:
            v = skor(d, esik)
            if v > en + 1e-9:
                en, s = v, d
                takas = False
                break
        else:
            if takas:
                return s, en, sinir, esik
            takas = True


def baslangic(h, sinir, tohum):
    """Olasilik ve deger karisimi tekler; kolon sinirina sigan rastgele ikili/uclu."""
    rnd = random.Random(tohum)
    P, Q = K.hazirla(h)
    s = []
    for i in range(15):
        w = [P[i][k] * (P[i][k] / Q[i][k]) ** rnd.uniform(0, 1.5) * rnd.uniform(0.6, 1.4) for k in range(3)]
        s.append([max(range(3), key=lambda k: w[k])])
    kolon = 1
    for i in rnd.sample(range(15), 15):
        if kolon * 2 <= sinir and rnd.random() < 0.5:
            sira = sorted(range(3), key=lambda k: -P[i][k])
            ek = next(k for k in sira if k not in s[i])
            s[i].append(ek)
            kolon *= 2
    return ["".join("102"[k] for k in sorted(x)) for x in s]


def main():
    yol, cikti = sys.argv[1], sys.argv[2]
    sinirlar = [int(x) for x in sys.argv[3].split(",")]
    esikler = [float(x) for x in sys.argv[4].split(",")]
    ayrik = []
    if "--ayrik" in sys.argv:
        ayrik = [a.split() for a in sys.argv[sys.argv.index("--ayrik") + 1:]]
    h = toto.oku(yol)
    isler = []
    for sinir in sinirlar:
        for esik in esikler:
            for t in range(8):
                isler.append((baslangic(h, sinir, 1000 * sinir + t), sinir, esik, t))
    t0 = time.time()
    with ProcessPoolExecutor(8, initializer=init, initargs=(yol, ayrik)) as ex:
        sonuc = list(ex.map(yerel, isler))
    print(f"{len(isler)} arama, {time.time() - t0:.0f} sn", file=sys.stderr)
    tekil = {}
    for s, v, sinir, esik in sonuc:
        if v > 0:
            tekil.setdefault(" ".join(s), []).append((sinir, esik))
    json.dump([{"secimler": k.split(), "kaynak": v} for k, v in tekil.items()], open(cikti, "w"))
    print(f"{len(tekil)} uygun yerel optimum", file=sys.stderr)


if __name__ == "__main__":
    main()
