#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
pesa_min_y_clase.py

Herramientas para:
  (a) Calcular la masa mínima para calibración de balanza dada una meta de
      incertidumbre relativa (p.ej., 0,1 %).
  (b) Seleccionar la clase de pesa patrón más “floja” que cumple un umbral
      de error permitido (usando tabla OIML R111 de MPE).

USO RÁPIDO
----------
# 1) Masa mínima (m_min = k*s_eff / r_rel), con s=0.005 g, d=0.01 g:
python pesa_min_y_clase.py --calc mmin --s 0.005 --d 0.01 --rrel 0.001 --k 2

# 2) Clase de pesa para 2000 g con TUR=4, usando la incertidumbre de balanza
#    derivada de s y d (u_bal = sqrt(s^2 + (d/√12)^2)):
python pesa_min_y_clase.py --calc clase --mass-g 2000 --tur 4 --s 0.005 --d 0.01

# 3) Ambas cosas a la vez:
python pesa_min_y_clase.py --calc both --s 0.005 --d 0.01 --rrel 0.001 --k 2 \
                           --mass-g 2000 --tur 4

TABLA OIML
----------
Por defecto se usa una tabla DEMO (valores ilustrativos). Para usar tu tabla
oficial OIML R111 (MPE en mg), prepara un CSV como:

mass_g,E1,E2,F1,F2,M1,M2,M3
1, ,1,3,10,50,150,500
2, ,1.2,3.5,12,60,180,600
...
2000, ,50,120,500,2500,7500,25000
...

Y llama con:  --mpe-csv ruta/a/tu_tabla.csv
"""

from __future__ import annotations
from typing import Dict, Sequence, Optional
import argparse
import math
import csv
import sys

MPE_TABLE_EXAMPLE_MG: Dict[float, Dict[str, float]] = {
    1.0:    {"E2": 1.0,  "F1": 3.0,   "F2": 10.0,  "M1": 50.0,   "M2": 150.0,  "M3": 500.0},
    2.0:    {"E2": 1.2,  "F1": 3.5,   "F2": 12.0,  "M1": 60.0,   "M2": 180.0,  "M3": 600.0},
    5.0:    {"E2": 1.5,  "F1": 4.0,   "F2": 15.0,  "M1": 75.0,   "M2": 225.0,  "M3": 750.0},
    10.0:   {"E2": 2.0,  "F1": 5.0,   "F2": 20.0,  "M1": 100.0,  "M2": 300.0,  "M3": 1000.0},
    20.0:   {"E2": 3.0,  "F1": 8.0,   "F2": 30.0,  "M1": 150.0,  "M2": 450.0,  "M3": 1500.0},
    50.0:   {"E2": 5.0,  "F1": 12.0,  "F2": 50.0,  "M1": 250.0,  "M2": 750.0,  "M3": 2500.0},
    100.0:  {"E2": 8.0,  "F1": 20.0,  "F2": 80.0,  "M1": 400.0,  "M2": 1200.0, "M3": 4000.0},
    200.0:  {"E2": 12.0, "F1": 30.0,  "F2": 120.0, "M1": 600.0,  "M2": 1800.0, "M3": 6000.0},
    500.0:  {"E2": 20.0, "F1": 50.0,  "F2": 200.0, "M1": 1000.0, "M2": 3000.0, "M3": 10000.0},
    1000.0: {"E2": 30.0, "F1": 80.0,  "F2": 300.0, "M1": 1500.0, "M2": 4500.0, "M3": 15000.0},
    2000.0: {"E2": 50.0, "F1": 120.0, "F2": 500.0, "M1": 2500.0, "M2": 7500.0, "M3": 25000.0},
    5000.0: {"E2": 80.0, "F1": 200.0, "F2": 800.0, "M1": 4000.0, "M2": 12000.0,"M3": 40000.0},
    10000.0:{"E2": 120.0,"F1": 300.0, "F2": 1200.0,"M1": 6000.0, "M2": 18000.0,"M3": 60000.0},
    20000.0:{"E2": 200.0,"F1": 500.0, "F2": 2000.0,"M1": 10000.0,"M2": 30000.0,"M3": 100000.0},
    50000.0:{"E2": 300.0,"F1": 800.0, "F2": 3000.0,"M1": 15000.0,"M2": 45000.0,"M3": 150000.0},
}
CLASSES_ORDER: Sequence[str] = ("E2", "F1", "F2", "M1", "M2", "M3")

def s_efectiva(s: float, d: Optional[float] = None, incluir_resolucion: bool = True) -> float:
    if incluir_resolucion and d is not None:
        return math.sqrt(s**2 + (d / math.sqrt(12.0))**2)
    return s

def masa_minima(s: float, d: Optional[float], r_rel: float = 0.001, k: float = 2.0,
                incluir_resolucion: bool = True) -> float:
    s_eff = s_efectiva(s, d, incluir_resolucion)
    return (k * s_eff) / r_rel

def cargar_tabla_mpe_csv(path: str) -> Dict[float, Dict[str, float]]:
    table: Dict[float, Dict[str, float]] = {}
    with open(path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            m = float(row["mass_g"])
            table[m] = {}
            for k, v in row.items():
                if k == "mass_g" or v is None or str(v).strip() == "":
                    continue
                table[m][k.strip()] = float(v)
    return table

def mpe_mg_para(mass_g: float, clase: str, tabla: Dict[float, Dict[str, float]]) -> Optional[float]:
    if mass_g in tabla and clase in tabla[mass_g]:
        return tabla[mass_g][clase]
    xs = sorted(tabla.keys())
    if not xs or mass_g < xs[0] or mass_g > xs[-1]:
        return None
    import bisect
    i = bisect.bisect_left(xs, mass_g)
    if i == 0 or i == len(xs):
        return None
    x0, x1 = xs[i - 1], xs[i]
    y0 = tabla[x0].get(clase); y1 = tabla[x1].get(clase)
    if y0 is None or y1 is None:
        return None
    t = (math.log10(mass_g) - math.log10(x0)) / (math.log10(x1) - math.log10(x0))
    return 10 ** (math.log10(y0) + t * (math.log10(y1) - math.log10(y0)))

def seleccionar_clase_pesa(mass_g: float,
                           umbral_std_g: Optional[float] = None,
                           umbral_mpe_mg: Optional[float] = None,
                           tabla_mpe_mg: Optional[Dict[float, Dict[str, float]]] = None,
                           clases_orden: Sequence[str] = CLASSES_ORDER) -> Optional[str]:
    tabla = tabla_mpe_mg or MPE_TABLE_EXAMPLE_MG
    if umbral_mpe_mg is None and umbral_std_g is None:
        raise ValueError("Proporciona umbral_std_g (g) o umbral_mpe_mg (mg).")
    for clase in clases_orden:
        mpe_mg = mpe_mg_para(mass_g, clase, tabla)
        if mpe_mg is None:
            continue
        if umbral_mpe_mg is not None:
            if mpe_mg <= umbral_mpe_mg:
                return clase
        else:
            u_std_g = mpe_mg / 1000.0 / math.sqrt(3.0)
            if u_std_g <= umbral_std_g:
                return clase
    return None

def build_parser():
    p = argparse.ArgumentParser(description="Masa mínima y clase de pesa (OIML R111).")
    p.add_argument("--calc", choices=("mmin", "clase", "both"), default="both")
    p.add_argument("--s", type=float, help="Repetibilidad s (g).")
    p.add_argument("--d", type=float, help="División d (g).")
    p.add_argument("--k", type=float, default=2.0, help="Factor de cobertura k (def=2.0).")
    p.add_argument("--rrel", type=float, default=0.001, help="Incertidumbre relativa objetivo (def=0.001=0.1%).")
    p.add_argument("--mass-g", type=float, help="Denominación del patrón (g) para seleccionar clase.")
    p.add_argument("--tur", type=float, help="TUR objetivo (usa u_patron <= u_balanza/TUR).")
    p.add_argument("--umbral-std-g", type=float, help="Umbral directo para el patrón en incertidumbre estándar (g).")
    p.add_argument("--umbral-mpe-mg", type=float, help="Umbral directo de MPE (mg).")
    p.add_argument("--mpe-csv", type=str, help="Ruta CSV OIML (MPE en mg). Si no, usa tabla DEMO.")
    return p

def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    tabla = cargar_tabla_mpe_csv(args.mpe_csv) if args.mpe_csv else None

    if args.calc in ("mmin", "both"):
        if args.s is None:
            print("[ERROR] Para mmin, especifica --s (g).", file=sys.stderr); return 2
        mmin = masa_minima(args.s, args.d, r_rel=args.rrel, k=args.k, incluir_resolucion=True)
        print(f"m_min (g) = {mmin:.6f}  [k={args.k:g}, r_rel={args.rrel:g}, s={args.s:g}, d={args.d}]")

    if args.calc in ("clase", "both"):
        if args.mass_g is None:
            print("[ERROR] Para clase, especifica --mass-g (g).", file=sys.stderr); return 3
        umbral_std_g = args.umbral_std_g
        umbral_mpe_mg = args.umbral_mpe_mg
        if umbral_std_g is None and args.tur is not None:
            if args.s is None or args.d is None:
                print("[ERROR] Con --tur debes dar --s y --d.", file=sys.stderr); return 4
            u_bal = math.sqrt(args.s**2 + (args.d / math.sqrt(12.0))**2)
            umbral_std_g = u_bal / args.tur
        if umbral_std_g is None and umbral_mpe_mg is None:
            print("[ERROR] Da --umbral-std-g o --umbral-mpe-mg o --tur.", file=sys.stderr); return 5

        clase = seleccionar_clase_pesa(args.mass_g, umbral_std_g, umbral_mpe_mg, tabla)
        if clase is None:
            print("No hay clase que cumpla con la tabla dada.")
        else:
            info = f"umbral_std_g={umbral_std_g:.6f} g" if umbral_std_g is not None else f"umbral_mpe_mg={umbral_mpe_mg:.6f} mg"
            print(f"Clase recomendada para {args.mass_g:g} g: {clase} ({info})")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
