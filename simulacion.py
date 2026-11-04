"""
SIMULACIÓN MONTE CARLO PARA INVENTARIOS
Simula escenarios de demanda con variación ±20% para calibrar el inventario de seguridad.
"""

import random
import config
productos = config.productos
meses = config.meses
costo_guardar = config.costo_guardar
penalizacion = config.penalizacion
demanda = config.DATOS_ENUNCIADO.demanda


def simular_un_escenario(politica, colchon):
    """
    Simula los 3 meses UNA vez, con demanda al azar entre -20% y +20%.

    politica = "rigida" -> compra siempre exactamente lo esperado (la forma actual)
    politica = "optimizada" -> compra lo necesario para tener el colchón

    Devuelve (costo_de_guardar, costo_de_faltantes).
    """
    costo_de_guardar = 0
    costo_de_faltantes = 0

    for p in productos:
        sobrante = 0   # lo que tengo en bodega al empezar el mes
        for m in meses:
            esperado = demanda[p][m - 1]

            # La demanda REAL: cambia al azar hasta 20% hacia arriba o abajo
            variacion = random.uniform(-0.20, 0.20)
            real = esperado * (1 + variacion)

            # ¿Cuánto compro este mes?
            if politica == "rigida":
                compro = esperado   # siempre lo esperado
            else:
                if m < 3:
                    quiero_al_cierre = colchon * demanda[p][m]  # colchón
                else:
                    quiero_al_cierre = 0
                # compro lo que falta para cubrir lo esperado + el colchón,
                # descontando lo que ya tengo
                compro = max(esperado + quiero_al_cierre - sobrante, 0)

            tengo = sobrante + compro

            if tengo >= real:
                sobrante = tengo - real  # me sobró producto
                faltante = 0
            else:
                sobrante = 0
                faltante = real - tengo  # me faltó producto

            costo_de_guardar += costo_guardar[p] * sobrante
            costo_de_faltantes += penalizacion[p] * faltante

    return costo_de_guardar, costo_de_faltantes


def promedio_de_costos(politica, colchon):
    """
    Repite la simulación muchas veces y devuelve el promedio.

    Args:
        politica: "rigida" o "optimizada"
        colchon: nivel de colchón de seguridad (ej. 0.12 para 12%)

    Returns:
        tuple: (promedio_guardar, promedio_faltantes)
    """
    random.seed(2026)   # para que siempre salgan los mismos números
    CANTIDAD_SIMULACIONES = 5000

    suma_guardar = 0
    suma_faltantes = 0
    for i in range(CANTIDAD_SIMULACIONES):
        guardar, faltantes = simular_un_escenario(politica, colchon)
        suma_guardar += guardar
        suma_faltantes += faltantes
    return suma_guardar / CANTIDAD_SIMULACIONES, suma_faltantes / CANTIDAD_SIMULACIONES