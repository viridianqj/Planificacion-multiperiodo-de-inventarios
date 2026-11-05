"""Análisis completo: pasos A (colchones), B (plan con PuLP) y C (comparación)."""

import random
from dataclasses import dataclass

from inventarios.config import COLCHON_MAX, N_SIMULACIONES, PASO_COLCHON, SEMILLA, VARIACION
from inventarios.modelo import calcular_plan
from inventarios.simulacion import promedio_de_costos

@dataclass
class Resultado:
    colchones: list
    costos_guardar: list
    costos_faltantes: list
    costos_totales: list
    mejor_colchon: float
    menor_costo: float
    plan_compras: dict
    plan_guardado: dict
    costo_plan: float
    rigida: tuple          # (guardar, faltantes) de la forma actual
    optimizada: tuple      # (guardar, faltantes) con el mejor colchón
    ahorro: float          # % de reducción de sobrecostos


def analizar(datos, n_sim=N_SIMULACIONES, variacion=VARIACION, colchon_max=COLCHON_MAX,
             paso=PASO_COLCHON, semilla=SEMILLA, progreso=None):
    """
    Hace todo el análisis: Paso A (barrido de colchones), Paso B (plan con PuLP)
    y Paso C (comparación contra la forma actual).
    `progreso` es una función opcional que recibe un número de 0 a 1.
    """
    random.seed(semilla)

    pasos = int(round(colchon_max / paso))
    total_etapas = pasos + 3
    hechas = 0

    def avanzar():
        nonlocal hechas
        hechas += 1
        if progreso:
            progreso(hechas / total_etapas)

    # ---- Paso A: probar colchones de 0% hasta el máximo ----
    colchones, c_guardar, c_faltantes, c_totales = [], [], [], []
    mejor_colchon = None
    menor_costo = None
    for i in range(pasos + 1):
        colchon = round(i * paso, 4)
        guardar, faltantes = promedio_de_costos("optimizada", colchon, datos, n_sim, variacion)
        total = guardar + faltantes
        colchones.append(colchon)
        c_guardar.append(guardar)
        c_faltantes.append(faltantes)
        c_totales.append(total)
        if menor_costo is None or total < menor_costo:
            menor_costo = total
            mejor_colchon = colchon
        avanzar()

    # ---- Paso B: el plan de compras con ese colchón ----
    plan_compras, plan_guardado, costo_plan = calcular_plan(mejor_colchon, datos)

    # ---- Paso C: comparar contra la forma actual (con una simulación nueva) ----
    g_r, f_r = promedio_de_costos("rigida", 0, datos, n_sim, variacion)
    avanzar()
    g_o, f_o = promedio_de_costos("optimizada", mejor_colchon, datos, n_sim, variacion)
    avanzar()
    if g_r + f_r > 0:
        ahorro = (1 - (g_o + f_o) / (g_r + f_r)) * 100
    else:
        ahorro = 0.0

    return Resultado(colchones, c_guardar, c_faltantes, c_totales, mejor_colchon, menor_costo,
                     plan_compras, plan_guardado, costo_plan, (g_r, f_r), (g_o, f_o), ahorro)
