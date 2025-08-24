# Pesas
Código para pesa mínima y masa patrón
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Herramientas para:
  (a) Masa mínima para calibración de balanza.
  (b) Selección de clase de pesa patrón que cumple un umbral de error permitido.

Uso típico:
- Cargar o definir la tabla de MPE (Max. Permissible Error) por clase OIML R111.
- Calcular m_min a partir de s (repetibilidad) y d (división).
- Con un TUR objetivo, fijar el umbral para el patrón y seleccionar clase.

NOTA IMPORTANTE:
  Este script está preparado para leer la tabla oficial de MPE desde un CSV
  (columnas: mass_g,E1,E2,F1,F2,M1,M2,M3 con MPE en mg). Incluye valores
  de ejemplo para algunas denominaciones, a modo de demostración. Reemplaza
  esos valores por los de tu laboratorio (OIML R111).
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List, Sequence, Optional
import math
import csv
import os

# ---------------------------------------------------------------------
# (0) Tabla de MPE por clase — EJEMPLO DEMO (Rellena con tu tabla oficial)
#     Formato: MPE mg por denominación (g). Sustituye por OIML R111 real.
# ---------------------------------------------------------------------
MPE_TABLE_EXAMPLE_MG: Dict[float, Dict[str, float]] = {
    # mass_g : { clase : MPE_en_mg }
    1.0:   {"E2": 1.0,  "F1": 3.0,  "F2": 10.0, "M1": 50.0,  "M2": 150.0, "M3": 500.0},
    2.0:   {"E2": 1.2,  "F1": 3.5,  "F2": 12.0, "M1": 60.0,  "M2": 180.0, "M3": 600.0},
    5.0:   {"E2": 1.5,  "F1": 4.0,  "F2": 15.0, "M1": 75.0,  "M2": 225.0, "M3": 750.0},
    10.0:  {"E2": 2.0,  "F1": 5.0,  "F2": 20.0, "M1": 100.0, "M2": 300.0, "M3": 1000.0},
    20.0:  {"E2": 3.0,  "F1": 8.0,  "F2": 30.0, "M1": 150.0, "M2": 450.0, "M3": 1500.0},
    50.0:  {"E2": 5.0,  "F1": 12.0, "F2": 50.0, "M1": 250.0, "M2": 750.0, "M3": 2500.0},
    100.0: {"E2": 8.0,  "F1": 20.0, "F2": 80.0, "M1": 400.0, "M2": 1200.0,"M3": 4000.0},
    200.0: {"E2": 12.0, "F1": 30.0, "F2": 120.0,"M1": 600.0, "M2": 1800.0,"M3": 6000.0},
    500.0: {"E2": 20.0, "F1": 50.0, "F2": 200.0,"M1": 1000.0,"M2": 3000.0,"M3": 10000.0},
    1000.0:{"E2": 30.0, "F1": 80.0, "F2": 300.0,"M1": 1500.0,"M2": 4500.0,"M3": 15000.0},  # 1 kg
    2000.0:{"E2": 50.0, "F1": 120.0,"F2": 500.0,"M1": 2500.0,"M2": 7500.0,"M3": 25000.0},  # 2 kg
    5000.0:{"E2": 80.0, "F1": 200.0,"F2": 800.0,"M1": 4000.0,"M2": 12000.0,"M3": 40000.0}, # 5 kg
    10000.0:{"E2": 120.0,"F1": 300.0,"F2": 1200.0,"M1": 6000.0,"M2": 18000.0,"M3": 60000.0},# 10 kg
    20000.0:{"E2": 200.0,"F1": 500.0,"F2": 2000.0,"M1": 10000.0,"M2": 30000.0,"M3": 100000.0},# 20 kg
    50000.0:{"E2": 300.0,"F1": 800.0,"F2": 3000.0,"M1": 15000.0,"M2": 45000.0,"M3": 150000.0},# 50 kg
}
CLASSES_ORDER = ["E2", "F1", "F2", "M1", "M2", "M3"]  # (puedes agregar "E1" si cargás su MPE)

# ---------------------------------------------------------------------
# (1) Masa mínima para calibración de balanza
# ---------------------------------------------------------------------
def s_efectiva(s: float, d: Optional[float] = None, incluir_resolucion: bool = True) -> float:
    """
    s: desviación estándar (g) de la balanza en el rango de interés.
    d: división (g). Si None o incluir_resolucion=False, no se suma.
    Return: s_eff en g.
    """
    if incluir_resolucion and d is not None:
        return math.sqrt(s**2 + (d / math.sqrt(12.0))**2)
    return s

def masa_minima(s: float, d: Optional[float], r_rel: float = 0.001, k: float = 2.0,
                incluir_resolucion: bool = True) -> float:
    """
    Calcula la masa mínima (g) para alcanzar una incertidumbre relativa objetivo r_rel (p.ej. 0.001 = 0.1 %)
    usando U = k * s_eff  y  U / m <= r_rel  =>  m_min = k * s_eff / r_rel.
    """
    s_eff = s_efectiva(s, d, incluir_resolucion)
    return (k * s_eff) / r_rel

# ---------------------------------------------------------------------
# (2) Selección de clase de pesa patrón
# ---------------------------------------------------------------------
def cargar_tabla_mpe_csv(path: str) -> Dict[float, Dict[str, float]]:
    """
    CSV con encabezados: mass_g,E1,E2,F1,F2,M1,M2,M3 (MPE en mg).
    Devuelve dict: { mass_g : {clase: mpe_mg, ...}, ... }
    """
    table: Dict[float, Dict[str, float]] = {}
    with open(path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            m = float(row["mass_g"])
            table[m] = {}
            for k, v in row.items():
                if k == "mass_g" or v.strip() == "":
                    continue
                table[m][k.strip()] = float(v)
    return table

def mpe_mg_para(mass_g: float, clase: str, tabla: Dict[float, Dict[str, float]]) -> Optional[float]:
    """
    Busca MPE (mg) para la denominación exacta mass_g. Si no está, intenta interpolación log-lineal.
    """
    if mass_g in tabla and clase in tabla[mass_g]:
        return tabla[mass_g][clase]
    # Interpolación simple en log10(masa) si hay puntos alrededor
    xs = sorted(tabla.keys())
    if mass_g < xs[0] or mass_g > xs[-1]:
        return None
    import bisect
    i = bisect.bisect_left(xs, mass_g)
    if i == 0 or i == len(xs):
        return None
    x0, x1 = xs[i-1], xs[i]
    y0 = tabla[x0].get(clase); y1 = tabla[x1].get(clase)
    if y0 is None or y1 is None:
        return None
    # Interpolación log-log (mg vs g)
    import math
    t = (math.log10(mass_g) - math.log10(x0)) / (math.log10(x1) - math.log10(x0))
    y = 10**(math.log10(y0) + t * (math.log10(y1) - math.log10(y0)))
    return y

def seleccionar_clase_pesa(mass_g: float, umbral_std_g: Optional[float] = None,
                           umbral_mpe_mg: Optional[float] = None,
                           tabla_mpe_mg: Optional[Dict[float, Dict[str, float]]] = None,
                           clases_orden: Sequence[str] = CLASSES_ORDER) -> Optional[str]:
    """
    Devuelve la clase "más floja" cuya MPE (en mg) cumple el umbral.
    - Si das umbral_std_g (incertidumbre estándar permitida para el patrón), se compara con MPE/√3.
    - Si das umbral_mpe_mg, se compara directamente con MPE (mg).
    - Si no pasas tabla, usa la de ejemplo (debes reemplazarla por la oficial).
    """
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
            u_std_g = mpe_mg / 1000.0 / math.sqrt(3.0)  # MPE rectangular -> u
            if u_std_g <= umbral_std_g:
                return clase
    return None

# ---------------------------------------------------------------------
# (3) Ejemplos rápidos
# ---------------------------------------------------------------------
if __name__ == "__main__":
    # --- Parámetros de las tres balanzas (del informe)
    # T-Scale (punto 100 kg)
    s_t = 6.0       # g (repetibilidad)
    d_t = 20.0      # g
    # Mettler (punto 2000 g)
    s_m = 0.005     # g
    d_m = 0.01      # g
    # Sartorius (punto 500 g)
    s_s = 0.0005    # g
    d_s = 0.001     # g

    r_obj = 0.001   # 0.1 % objetivo
    k = 2.0

    for nombre, s, d in [
        ("T-Scale 100 kg", s_t, d_t),
        ("Mettler 2000 g", s_m, d_m),
        ("Sartorius 500 g", s_s, d_s),
    ]:
        mmin = masa_minima(s, d, r_rel=r_obj, k=k, incluir_resolucion=True)
        print(f"[{nombre}] m_min para r={r_obj*100:.2f}% -> {mmin:.3f} g")

    # Selección de clase para un patrón de 2000 g, fijando TUR=4:
    # umbral para el patrón: u_std_patron <= u_bal / TUR.
    u_bal_m = math.sqrt(s_m**2 + (d_m/math.sqrt(12))**2)  # g
    TUR = 4.0
    umbral_std_patron = u_bal_m / TUR
    clase = seleccionar_clase_pesa(
        mass_g=2000.0,
        umbral_std_g=umbral_std_patron,
        tabla_mpe_mg=MPE_TABLE_EXAMPLE_MG
    )
    print(f"Clase recomendada para 2000 g con TUR={TUR}: {clase} (usando tabla DEMO)")
