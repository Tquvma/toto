"""Adaylarin ana senaryo getirisini 4 bagimsiz tohumla (4x20000 ornek) olcer.
Kullanim: python kupon_dogrula.py <json> <adaylar_deger.json> [p13_alt_sinir]"""
import os, sys, json
from concurrent.futures import ProcessPoolExecutor
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import toto
TOHUM = [7, 21, 33, 45]

def is_(args):
    yol, t, adaylar = args
    h = toto.oku(yol)
    orn = toto.sonuc_ornekleri(h, 20000, tohum=t, alfa=1.15)
    r = []
    for s in adaylar:
        o = toto.kazanc_ozet(s, orn, 110e6, 110e6 / 4.9, 0.0)
        r.append((o["beklenen"] / o["maliyet"], o["kar_olasiligi"], o["kademe"]))
    return r

def main():
    yol = sys.argv[1]
    alt = float(sys.argv[3]) if len(sys.argv) > 3 else 0.08
    d = [x for x in json.load(open(sys.argv[2])) if x["p13"] >= alt]
    adaylar = [x["secimler"] for x in d]
    with ProcessPoolExecutor(4) as ex:
        R = list(ex.map(is_, [(yol, t, adaylar) for t in TOHUM]))
    h = toto.oku(yol)
    sat = []
    for i, x in enumerate(d):
        g = [R[k][i][0] for k in range(4)]
        pk = [R[k][i][1] for k in range(4)]
        kd = {t: sum(R[k][i][2][t] for k in range(4)) / 4 for t in (12, 13, 14, 15)}
        sat.append((x, sum(g) / 4, min(g), max(g), sum(pk) / 4, kd))
    sat.sort(key=lambda z: -z[0]["p13"])
    print(f"{'kolon':>5} {'13+':>6} | getiri ort (min-max) | karO | odeme kademe 15/14/13/12 (TL) | secimler")
    for x, g, gmin, gmax, pk, kd in sat:
        print(f"{x['kolon']:>5} {x['p13']*100:5.1f}% | {g*100:5.0f}% ({gmin*100:.0f}-{gmax*100:.0f}) | {pk*100:4.1f}% | "
              f"{kd[15]:,.0f}/{kd[14]:,.0f}/{kd[13]:,.0f}/{kd[12]:,.0f} | " + " ".join("-".join(toto.secim_listesi(c)) for c in x["secimler"]))

if __name__ == "__main__":
    main()
