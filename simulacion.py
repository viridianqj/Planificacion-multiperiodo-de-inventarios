"""
SIMULACIÓN MONTE CARLO PARA INVENTARIOS
Simula escenarios de demanda con variación ±20% para calibrar el inventario de seguridad.
"""

import random
import config
from dataclasses import dataclass


def simular_un_escenario(politica, colchon, datos, variacion=config.VARIACION):
    """
    Simula los 3 meses UNA vez, con demanda al azar entre -variación y +variación.
    politica = "rigida" -> compra siempre exactamente lo esperado (la forma actual)
    politica = "optimizada" -> compra lo necesario para tener el colchón
    Devuelve (costo_de_guardar, costo_de_faltantes).
    """
    costo_de_guardar = 0
    costo_de_faltantes = 0
    ultimo_mes = datos.meses[-1]

    for p in datos.productos:
        sobrante = 0   # lo que tengo en bodega al empezar el mes
        for m in datos.meses:
            esperado = datos.demanda[p][m - 1]

            # La demanda REAL: cambia al azar hacia arriba o hacia abajo
            cambio = random.uniform(-variacion, variacion)
            real = esperado * (1 + cambio)

            # ¿Cuánto compro este mes?
            if politica == "rigida":
                compro = esperado   # siempre lo esperado
            else:
                if m < ultimo_mes:
                    quiero_al_cierre = colchon * datos.demanda[p][m]  # colchón
                else:
                    quiero_al_cierre = 0
                # comprlo lo que falta para cubrir lo esperado + el colchón,
                # descontando lo que ya tengo
                compro = max(esperado + quiero_al_cierre - sobrante, 0)

            tengo = sobrante + compro

            if tengo >= real:
                sobrante = tengo - real   # me sobró producto
                faltante = 0
            else:
                sobrante = 0
                faltante = real - tengo   # me faltó producto

            costo_de_guardar += datos.costo_guardar[p] * sobrante
            costo_de_faltantes += datos.penalizacion[p] * faltante

    return costo_de_guardar, costo_de_faltantes


def promedio_de_costos(politica, colchon, datos, n_sim=config.N_SIMULACIONES, variacion=config.VARIACION):
    """Repite la simulación muchas veces y devuelve el promedio."""
    suma_guardar = 0
    suma_faltantes = 0
    for _ in range(n_sim):
        guardar, faltantes = simular_un_escenario(politica, colchon, datos, variacion)
        suma_guardar += guardar
        suma_faltantes += faltantes
    return suma_guardar / n_sim, suma_faltantes / n_sim


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


def analizar(datos, n_sim=config.N_SIMULACIONES, variacion=config.VARIACION, colchon_max=config.COLCHON_MAX,
             paso=config.PASO_COLCHON, semilla=config.SEMILLA, progreso=None):
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
    from modelo import calcular_plan
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