"""Aday kuponlari bagimsiz buyuk orneklemle ve duyarlilik senaryolariyla degerlendirir.
Kullanim: python kupon_degerlendir.py <hafta.json> <adaylar.json> [ek_adaylar.json ...]"""
import os, sys, json, math
from concurrent.futures import ProcessPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import toto

SENARYO = [(110e6, 1.15), (90e6, 1.15), (140e6, 1.15), (110e6, 1.0), (110e6, 1.3)]
G = {}


def init(yol):
    G["h"] = toto.oku(yol)
    G["orn"] = {a: toto.sonuc_ornekleri(G["h"], 20000, tohum=7, alfa=a) for a in {s[1] for s in SENARYO}}


def degerlendir(s):
    h = G["h"]
    o13 = toto.kupon_ozet(h, s)
    sen = []
    for havuz, alfa in SENARYO:
        o = toto.kazanc_ozet(s, G["orn"][alfa], havuz, havuz / 4.9, 0.0)
        sen.append({"havuz": havuz, "alfa": alfa, "getiri": o["beklenen"] / o["maliyet"], "pk": o["kar_olasiligi"],
                    "kar": o["kar"], "kademe": o["kademe"]})
    return {"secimler": s, "kolon": o13["kolon"], "p13": o13["p13+"], "p14": o13["p14+"], "p15": o13["p15"],
            "p12": o13["p12+"], "sen": sen}


def main():
    yol = sys.argv[1]
    adaylar = []
    for f in sys.argv[2:]:
        for a in json.load(open(f)):
            s = a["secimler"] if isinstance(a, dict) else a
            if s not in adaylar:
                adaylar.append(s)
    with ProcessPoolExecutor(8, initializer=init, initargs=(yol,)) as ex:
        r = list(ex.map(degerlendir, adaylar))
    json.dump(r, open(sys.argv[2].replace(".json", "_deger.json"), "w"))
    # Pareto: 13+, getiri (ana senaryo), kar olasiligi (ana senaryo)
    ana = lambda x: x["sen"][0]
    par = [x for x in r if not any(
        y is not x and y["p13"] >= x["p13"] and ana(y)["getiri"] >= ana(x)["getiri"] and ana(y)["pk"] >= ana(x)["pk"]
        and (y["p13"] > x["p13"] or ana(y)["getiri"] > ana(x)["getiri"] or ana(y)["pk"] > ana(x)["pk"]) for y in r)]
    par.sort(key=lambda x: -x["p13"])
    print(f"{len(r)} aday, Pareto {len(par)}\n")
    print(f"{'kolon':>5} {'13+':>6} {'14+':>5} {'15':>5} | {'getiri':>6} {'karO':>5} | getiri aralik (havuz90/140, alfa1.0/1.3) | secimler")
    for x in par:
        a = ana(x)
        g = [f"{s['getiri'] * 100:.0f}" for s in x["sen"][1:]]
        print(f"{x['kolon']:>5} {x['p13'] * 100:5.1f}% {x['p14'] * 100:4.1f}% {x['p15'] * 100:4.2f}% | {a['getiri'] * 100:5.0f}% "
              f"{a['pk'] * 100:4.1f}% | {'/'.join(g):>22} | " + " ".join("-".join(toto.secim_listesi(c)) for c in x["secimler"]))


if __name__ == "__main__":
    main()
