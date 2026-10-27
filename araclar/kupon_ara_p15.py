"""15 bilme esigi kisitli kar aramasi: P(15) >= esik olan kuponlar icinde beklenen kari en yuksek olani arar.
Kullanim: python kupon_ara_p15.py <hafta.json> <cikti.json> <kolon_siniri> <esik1,esik2,...> [onceki_cikti.json ...]
Esikler oran olarak (0.025 = %2,5). Komsuluk ve kazanc modeli kupon_ara.py ile ayni (havuz 110 M, alfa 1.15)."""
import sys, json, time
from concurrent.futures import ProcessPoolExecutor
import kupon_ara as O
toto = O.toto


def skor15(s, T):
    p15 = toto.kupon_ozet(O.G["h"], s)["p15"]
    if p15 < T - 1e-12:
        return -1e9 + p15 * 1e10
    return O.ozet(s)["kar"]


def yerel(args):
    bas, sinir, T = args
    s = ["".join(toto.secim_listesi(x)) for x in bas]
    en = skor15(s, T)
    while True:
        aday = None
        for d in O.komsular(s, sinir):
            v = skor15(d, T)
            if v > en + 1e-6 and (aday is None or v > aday[0]):
                aday = (v, d)
        if aday is None:
            return s, en
        en, s = aday


def main():
    yol, cikti, sinir = sys.argv[1], sys.argv[2], int(sys.argv[3])
    esikler = [float(x) for x in sys.argv[4].split(",")]
    h = toto.oku(yol)
    baslar = [k["secimler"] for k in h["kuponlar"] if O.kolon([toto.secim_listesi(x) for x in k["secimler"]]) <= sinir]
    for k in (sinir, 1944, 1458, 972):
        if k <= sinir:
            baslar.append(toto.en_iyi_sistem(h, k, 15))
    for f in sys.argv[5:]:
        baslar += [a["secimler"] for a in json.load(open(f))]
    baslar += [O.rastgele_baslangic(h, sinir, 900 + i) for i in range(8)]
    isler = [(b, sinir, T) for T in esikler for b in baslar]
    t0 = time.time()
    with ProcessPoolExecutor(8, initializer=O.init, initargs=(yol,)) as ex:
        sonuc = list(ex.map(yerel, isler))
    print(f"{len(isler)} arama, {time.time() - t0:.0f} sn", file=sys.stderr)
    tekil = {}
    for (s, v), (_, _, T) in zip(sonuc, isler):
        if v > -1e8:
            tekil.setdefault(" ".join(s), set()).add(T)
    json.dump([{"secimler": k.split(), "esik": sorted(v)} for k, v in tekil.items()], open(cikti, "w"))
    print(f"{len(tekil)} uygun yerel optimum", file=sys.stderr)


if __name__ == "__main__":
    main()
